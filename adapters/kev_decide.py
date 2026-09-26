#!/usr/bin/env python3
"""Pinned Kev-0.8B trained decision head on causal market JSONL, CPU only."""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

SOURCE_REVISION = "f1535963cea021439370c23127bc970b6788e730"
CHECKPOINT_REPO = "jaredpalmer/kev-0.8b"
CHECKPOINT_REVISION = "9a45d25eb2ab761841196625383fa1dff0e56c1e"
BASE_REPO = "Qwen/Qwen3.5-0.8B-Base"
BASE_REVISION = "dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68"
TASK = "next_7_day_price_direction"
CHECKPOINT_SHA256 = {
    "adapter_config.json": "748acb2cda88454cb1ba69d745ba336f3fcb5486eac349e90960c8b8d8d3e854",
    "adapter_model.safetensors": "9b908623acb162118575f4e7a94524f9c139c335be4bfb74d6cfceca01e1885a",
    "head.pt": "f400bd12802b2b105ae45d6b03774a158a3db4fccff42413734ddca2e5c920b6",
}
BASE_SHA256 = {
    "config.json": "b90b86f35c8e6925ef74ee04d0e758f0a845c83a42089ad82bbaa948de9b4204",
    "merges.txt": "a9d356d7bdf1ef4949e3e748e95b8e10ad9d4e2e838eddc38a0a7b6b94d1db8d",
    "model.safetensors-00001-of-00001.safetensors": "c2b1e5a17d9c1e27685d92ed9b382911ebb99955ecd89052d1721241adfbab6c",
    "model.safetensors.index.json": "ce9a885efdf27d3664fdef5d512ad365216f1074051ef840c7cd8e5431495d0a",
    "tokenizer.json": "fe000e3ed39ed12b8d2481d527d44f93c65d37e87645d2dcc80d1bf9d50d2927",
    "tokenizer_config.json": "e611fbccc7c29ef3b1cafb1cb7ea548d189968632901d678fd62be68c47885de",
    "vocab.json": "ce99b4cb2983d118806ce0a8b777a35b093e2000a503ebde25853284c9dfa003",
}


def verify_files(root: Path, expected: dict[str, str], label: str) -> None:
    for name, sha256 in expected.items():
        path = root / name
        if not path.is_file():
            raise ValueError(f"Missing pinned Kev {label} file: {path}")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != sha256:
            raise ValueError(f"Kev {label} SHA-256 mismatch: {name}")


def main() -> None:
    checkpoint_dir = Path(os.environ["KEV_CHECKPOINT_DIR"])
    base_dir = Path(os.environ["KEV_BASE_DIR"])
    threads = int(os.environ.get("KEV_THREADS", "2"))
    if threads < 1 or threads > 2:
        raise ValueError("KEV_THREADS must be 1 or 2")
    verify_files(checkpoint_dir, CHECKPOINT_SHA256, "checkpoint")
    verify_files(base_dir, BASE_SHA256, "base")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    with contextlib.redirect_stdout(sys.stderr):
        import torch
        from kev.api import SystemOneRequest, to_record
        from kev.checkpoint import Checkpoint, LoadOptions
        from kev.model import SERVE_MAX_BRANCH, SERVE_MAX_STATE

        torch.set_num_threads(threads)
        torch.set_num_interop_threads(1)
        checkpoint = Checkpoint(str(checkpoint_dir))
        if (checkpoint.meta.base, checkpoint.meta.base_revision) != (BASE_REPO, BASE_REVISION):
            raise ValueError("Kev checkpoint declares a different base model or revision")
        if checkpoint.full:
            raise ValueError("Expected the pinned LoRA adapter plus pointer head")
        # The published head points to a Hub base. Substitute the verified local
        # mirror in memory; no checkpoint weight or calibration value is changed.
        checkpoint.meta.base = str(base_dir)
        checkpoint.meta.base_revision = None
        tokenizer, model = checkpoint.load("cpu", LoadOptions(dtype=torch.float32, backend="torch"))

    for line_number, line in enumerate(sys.stdin, 1):
        if not line.strip():
            continue
        request = json.loads(line)
        if not isinstance(request, dict) or not isinstance(request.get("id"), str):
            raise ValueError(f"line {line_number}: id must be a string")
        state = request.get("state")
        if not isinstance(state, str) or not state.strip():
            raise ValueError(f"line {line_number}: state must be a nonempty string")
        started = time.perf_counter()
        with contextlib.redirect_stdout(sys.stderr):
            public_request = SystemOneRequest.model_validate({
                "state": state,
                "questions": {TASK: {
                    "type": "choice", "instructions": TASK,
                    "criteria": {"up": "Up", "down": "Down"},
                }},
            })
            record, metadata = to_record(public_request)
            if metadata[0]["keys"] != ["up", "down"] or record["questions"][0]["options"] != ["up: Up", "down: Down"]:
                raise ValueError("Kev changed the requested up/down option order")
            # to_record inserts label=0 as an unused schema placeholder. Neither
            # encode nor probs reads it to score the two option texts.
            encoded = model.encode(tokenizer, record, max_state=SERVE_MAX_STATE,
                                   max_branch=SERVE_MAX_BRANCH, strict=True)
            if len(encoded["opt_idx"]) != 1 or len(encoded["opt_idx"][0]) != 2 or encoded["opt_idx"][0][0] >= encoded["opt_idx"][0][1]:
                raise ValueError("Kev encoded options out of order")
            probabilities = model.probs(encoded)[0].tolist()
        up, down = (float(value) for value in probabilities)
        if not all(math.isfinite(value) and 0 <= value <= 1 for value in (up, down)):
            raise ValueError(f"line {line_number}: invalid model probabilities")
        if not math.isclose(up + down, 1.0, abs_tol=1e-6):
            raise ValueError(f"line {line_number}: probabilities do not sum to one")
        prediction = "up" if up > down else "down"
        response = {
            "id": request["id"],
            "prediction": prediction,
            "probabilities": {"up": up, "down": down},
            "prob_up": up,
            "target_weight": float(prediction == "up"),
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "source": "kev-trained-head-cpu",
            "source_revision": SOURCE_REVISION,
            "model": CHECKPOINT_REPO,
            "model_revision": CHECKPOINT_REVISION,
            "adapter_sha256": CHECKPOINT_SHA256["adapter_model.safetensors"],
            "head_sha256": CHECKPOINT_SHA256["head.pt"],
            "base_model": BASE_REPO,
            "base_revision": BASE_REVISION,
            "base_sha256": BASE_SHA256["model.safetensors-00001-of-00001.safetensors"],
            "checkpoint_temperature": float(model.head.temperature),
            "input_tokens": len(encoded["ids"]),
            "benchmark_labels_used": 0,
            "probability_semantics": "checkpoint_temperature_nonmarket_calibration",
        }
        sys.stdout.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"kev_decide: {error}", file=sys.stderr)
        raise SystemExit(1) from error
