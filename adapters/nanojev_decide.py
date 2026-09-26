#!/usr/bin/env python3
"""CPU replay of NanoJev's pinned trained decision head over market JSONL."""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

SOURCE_REVISION = "76fdfc9ecdca45a9bcef17991a07d3041a87685a"
CHECKPOINT_REPO = "C-Tianyu/NanoJev"
CHECKPOINT_REVISION = "047b927b30882a1138fc504821b82ac145a4b81a"
BASE_MODEL = "Qwen/Qwen3-0.6B"
BASE_REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"
TASK = "next_7_day_price_direction"
FILE_SHA256 = {
    "best.safetensors": "f68c47d66998231b86b7e91b4ed5e82ae23acf104c8b7cd6d165c3ac7b7ffe1b",
    "config.json": "901038b5f1785c748c3fb4d35131e910951f2178f9a8bf024ff57aca556a30e9",
    "backbone_config/config.json": "30c011854471509747858ac07ffb8a4dab2bc6c04035b184729b69500c557c54",
    "tokenizer/chat_template.jinja": "a55ee1b1660128b7098723e0abcd92caa0788061051c62d51cbe87d9cf1974d8",
    "tokenizer/tokenizer.json": "be75606093db2094d7cd20f3c2f385c212750648bd6ea4fb2bf507a6a4c55506",
    "tokenizer/tokenizer_config.json": "1cc816812993bff176eb4f7495433b736f06fba9b6e7b05cac7b4a1780650c95",
}
SOURCE_FILE_SHA256 = {
    "scripts/predict_toy_decisions.py": "6eedc49aaf9a81763677e3cff4e87fc4e499bfc5decf0bb4678f452f578dd92b",
    "scripts/train_toy_decisions.py": "4f39babd5575e43d7acf3eca357329a93c60041f334bc2bd7424929bf9c0da86",
}


def verify_files(root: Path, expected_files: dict[str, str], label: str) -> None:
    for name, expected in expected_files.items():
        path = root / name
        if not path.is_file():
            raise ValueError(f"Missing pinned NanoJev {label} file: {path}")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != expected:
            raise ValueError(f"NanoJev {label} SHA-256 mismatch: {name}")


def load_cpu_model(checkpoint_root: Path, source_root: Path, threads: int):
    sys.path.insert(0, str(source_root / "scripts"))
    import torch
    from safetensors.torch import load_file
    from transformers import AutoConfig, AutoModel, AutoTokenizer
    from predict_toy_decisions import load_decision_model_class, read_json

    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    config = read_json(checkpoint_root / "config.json")
    if (config.get("model"), config.get("resolved_model_revision"), config.get("set_head")) != (
        BASE_MODEL, BASE_REVISION, "attention"
    ):
        raise ValueError("NanoJev checkpoint configuration differs from the pinned trained model")
    tokenizer = AutoTokenizer.from_pretrained(
        str(checkpoint_root / "tokenizer"), local_files_only=True, trust_remote_code=False
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    body_config = AutoConfig.from_pretrained(
        str(checkpoint_root / "backbone_config"), local_files_only=True, trust_remote_code=False
    )
    body_config.use_cache = False
    body = AutoModel.from_config(
        body_config, attn_implementation="sdpa", trust_remote_code=False
    ).float()
    model = load_decision_model_class()(body, config["set_head"])
    model.load_state_dict(load_file(str(checkpoint_root / "best.safetensors"), device="cpu"), strict=True)
    model.eval()
    return model, tokenizer, config, torch


def main() -> None:
    checkpoint_root = Path(os.environ["NANOJEV_CHECKPOINT_DIR"])
    source_root = Path(os.environ["NANOJEV_SOURCE_DIR"])
    verify_files(source_root, SOURCE_FILE_SHA256, "source")
    verify_files(checkpoint_root, FILE_SHA256, "checkpoint")
    threads = int(os.environ.get("NANOJEV_THREADS", "2"))
    max_tokens = int(os.environ.get("NANOJEV_MAX_TOKENS", "2048"))
    if threads < 1 or max_tokens < 1:
        raise ValueError("NANOJEV_THREADS and NANOJEV_MAX_TOKENS must be positive")
    with contextlib.redirect_stdout(sys.stderr):
        model, tokenizer, config, torch = load_cpu_model(checkpoint_root, source_root, threads)
        from predict_toy_decisions import answer_from_probabilities, prepare_examples

    for line_number, line in enumerate(sys.stdin, 1):
        if not line.strip():
            continue
        request = json.loads(line)
        if not isinstance(request, dict) or not isinstance(request.get("id"), str):
            raise ValueError(f"line {line_number}: id must be a string")
        state = request.get("state")
        if not isinstance(state, str) or not state.strip():
            raise ValueError(f"line {line_number}: state must be a nonempty string")
        payload = {"states": [{"id": request["id"], "state": state, "questions": {
            TASK: {"type": "choice", "instructions": TASK,
                   "criteria": {"up": "Up", "down": "Down"}}
        }}]}
        started = time.perf_counter()
        with contextlib.redirect_stdout(sys.stderr):
            examples = prepare_examples(payload, tokenizer, max_tokens)
            with torch.inference_mode():
                logits, _ = model(examples, tokenizer.pad_token_id)
                probabilities = logits[0, :2].float().softmax(-1).tolist()
            answer = answer_from_probabilities(examples[0], probabilities)
        up, down = (float(answer["probabilities"][key]) for key in ("up", "down"))
        if not all(math.isfinite(value) and 0 <= value <= 1 for value in (up, down)):
            raise ValueError(f"line {line_number}: invalid model probabilities")
        prediction = "up" if up > down else "down"
        response = {
            "id": request["id"],
            "prediction": prediction,
            "probabilities": {"up": up, "down": down},
            "prob_up": up,
            "target_weight": float(prediction == "up"),
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "source": "nanojev-trained-head-cpu",
            "source_revision": SOURCE_REVISION,
            "model": CHECKPOINT_REPO,
            "model_revision": CHECKPOINT_REVISION,
            "checkpoint_sha256": FILE_SHA256["best.safetensors"],
            "base_model": BASE_MODEL,
            "base_revision": BASE_REVISION,
            "training_domain": "maze_snake_vizdoom_games",
            "input_token_count": max(len(ids) for ids in examples[0]["leaf_tokens"]),
            "probability_semantics": "checkpoint_choice_softmax_uncalibrated_for_market",
        }
        sys.stdout.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"nanojev_decide: {error}", file=sys.stderr)
        raise SystemExit(1) from error
