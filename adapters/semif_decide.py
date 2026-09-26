#!/usr/bin/env python3
"""SemIf's pinned llama.cpp option-logit scorer over weekly market JSONL."""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

SOURCE_REVISION = "23cf1f39fc9534fe81437200959b6dfc7106e45a"
MODEL = "Qwen/Qwen3.5-4B"
MODEL_REVISION = "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"
GGUF_REPO = "bartowski/Qwen_Qwen3.5-4B-GGUF"
GGUF_REVISION = "4168f45a16a1290d65a4ec0fa312ae917a4c15d6"
GGUF_SHA256 = "13c16f426047e2de38cd075bdade4a7bcbc8c774384876f677740cda65f8a983"
GGUF_BYTES = 3_013_027_808
TASK = "next_7_day_price_direction"
TOKENIZER_SHA256 = {
    "chat_template.jinja": "a4aee8afcf2e0711942cf848899be66016f8d14a889ff9ede07bca099c28f715",
    "config.json": "ddc63e1c717afa86c865bb5e01313d89d72bb53b97ad4a8a03ba8510c0621670",
    "merges.txt": "a9d356d7bdf1ef4949e3e748e95b8e10ad9d4e2e838eddc38a0a7b6b94d1db8d",
    "tokenizer.json": "5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42",
    "tokenizer_config.json": "316230d6a809701f4db5ea8f8fc862bc3a6f3229c937c174e674ff3ca0a64ac8",
    "vocab.json": "ce99b4cb2983d118806ce0a8b777a35b093e2000a503ebde25853284c9dfa003",
}


def verify_gguf(path: Path) -> None:
    if not path.is_file() or path.stat().st_size != GGUF_BYTES:
        raise ValueError(f"Expected the pinned {GGUF_BYTES}-byte GGUF at {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != GGUF_SHA256:
        raise ValueError("GGUF SHA-256 does not match the pinned checkpoint")


def verify_tokenizer(path: Path) -> None:
    if not path.is_dir():
        raise ValueError(f"Reference tokenizer directory is missing: {path}")
    for name, expected in TOKENIZER_SHA256.items():
        file_path = path / name
        if not file_path.is_file():
            raise ValueError(f"Reference tokenizer file is missing: {file_path}")
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if digest != expected:
            raise ValueError(f"Reference tokenizer checksum mismatch: {name}")


def main() -> None:
    gguf_path = Path(os.environ["SEMIF_GGUF_PATH"])
    tokenizer_path = Path(os.environ["SEMIF_TOKENIZER_PATH"])
    verify_tokenizer(tokenizer_path)
    verify_gguf(gguf_path)
    threads = int(os.environ.get("SEMIF_THREADS", "2"))
    max_tokens = int(os.environ.get("SEMIF_MAX_TOKENS", "2048"))

    with contextlib.redirect_stdout(sys.stderr):
        from semif_phase1 import llamacpp_backend

        model, tokenizer, metadata = llamacpp_backend.load_model(
            str(tokenizer_path), MODEL_REVISION, gguf_path,
            threads=threads, context_tokens=max_tokens,
        )
    try:
        for line_number, line in enumerate(sys.stdin, 1):
            if not line.strip():
                continue
            request = json.loads(line)
            if not isinstance(request, dict) or not isinstance(request.get("id"), str):
                raise ValueError(f"line {line_number}: id must be a string")
            state = request.get("state")
            if not isinstance(state, str) or not state.strip():
                raise ValueError(f"line {line_number}: state must be a nonempty string")
            row = {
                "id": request["id"],
                "state": state,
                "question": TASK,
                "options": [
                    {"id": "up", "description": "Up"},
                    {"id": "down", "description": "Down"},
                ],
            }
            started = time.perf_counter()
            with contextlib.redirect_stdout(sys.stderr):
                scored = llamacpp_backend.score(model, tokenizer, row, metadata, max_tokens)
            up, down = (float(value) for value in scored["probabilities"])
            if not all(math.isfinite(value) and 0 <= value <= 1 for value in (up, down)):
                raise ValueError(f"line {line_number}: invalid option probabilities")
            if not math.isclose(up + down, 1.0, abs_tol=1e-6):
                raise ValueError(f"line {line_number}: option probabilities do not sum to one")
            prediction = "up" if up > down else "down"
            response = {
                "id": request["id"],
                "prediction": prediction,
                "probabilities": {"up": up, "down": down},
                "prob_up": up,
                "target_weight": float(prediction == "up"),
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                "source": "semif-llamacpp-direct",
                "source_revision": SOURCE_REVISION,
                "model": MODEL,
                "model_revision": MODEL_REVISION,
                "gguf_repo": GGUF_REPO,
                "gguf_revision": GGUF_REVISION,
                "gguf_sha256": GGUF_SHA256,
                "prompt_sha256": scored["prompt_sha256"],
                "prompt_version": scored["prompt_version"],
                "input_tokens": scored["input_tokens"],
                "probability_semantics": "conditional_option_logit_softmax_uncalibrated",
            }
            sys.stdout.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + "\n")
            sys.stdout.flush()
    finally:
        model.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"semif_decide: {error}", file=sys.stderr)
        raise SystemExit(1) from error
