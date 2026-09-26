#!/usr/bin/env python3
"""Pinned AnyJev L0, zero-label CPU decisions over causal market JSONL."""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

SOURCE_REVISION = "795a4970b47218b7c0686cd579d691fc2cf8df2f"
MODEL = "Qwen/Qwen3.5-0.8B"
MODEL_REVISION = "2fc06364715b967f1860aea9cf38778875588b17"
WEIGHT_FILE = "model.safetensors-00001-of-00001.safetensors"
WEIGHT_SHA256 = "04b1c301231dd422b8860db31311ab2721511346a32cb1e079c4c4e5f1fe4696"
MODEL_FILE_SHA256 = {
    WEIGHT_FILE: WEIGHT_SHA256,
    "config.json": "b90b86f35c8e6925ef74ee04d0e758f0a845c83a42089ad82bbaa948de9b4204",
    "merges.txt": "a9d356d7bdf1ef4949e3e748e95b8e10ad9d4e2e838eddc38a0a7b6b94d1db8d",
    "model.safetensors.index.json": "d8a08838a613b025eb7952ed9db11696213e57e76a375661ef5c12f9dd5dcf4e",
    "preprocessor_config.json": "27225450ac9c6529872ee1924fcb0962ff5634834f817040f444118116f4e516",
    "tokenizer_config.json": "49e2b6e395f959f077f1e992b338919c0d4a9732fc6e613995e06557f843500c",
    "tokenizer.json": "5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42",
    "video_preprocessor_config.json": "7768af27c1fafa9cc9011c1dc20067e03f8915e03b63504550e11d5066986d13",
    "vocab.json": "ce99b4cb2983d118806ce0a8b777a35b093e2000a503ebde25853284c9dfa003",
}
TASK = "next_7_day_price_direction"


def verify_model_files(root: Path) -> None:
    for name, expected in MODEL_FILE_SHA256.items():
        path = root / name
        if not path.is_file():
            raise ValueError(f"Missing pinned Qwen file: {path}")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != expected:
            raise ValueError(f"Pinned Qwen file SHA-256 mismatch: {path}")


def main() -> None:
    model_path = Path(os.environ["ANYJEV_MODEL_PATH"])
    threads = int(os.environ.get("ANYJEV_THREADS", "2"))
    if threads < 1:
        raise ValueError("ANYJEV_THREADS must be positive")
    verify_model_files(model_path)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    with contextlib.redirect_stdout(sys.stderr):
        import torch
        from anyjev import Decider, Question
        from anyjev.backends.hf import HFBackend

        torch.set_num_threads(threads)
        torch.set_num_interop_threads(1)
        backend = HFBackend(str(model_path), device="cpu", dtype="float32", batch_size=1)
        # No fitted prior or task labels. Permutation marginalization is the
        # source's L0 path; prior="none" makes every line independent of order.
        decider = Decider(backend, level="L0", prior="none", max_permutations=2)
        question = Question.choice(TASK, ["Up", "Down"], name=TASK)

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
            decision = decider.decide(state, [question], require="L0")[TASK]
        up, down = (float(decision.distribution[label]) for label in ("Up", "Down"))
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
            "source": "anyjev-l0-hf-cpu",
            "source_revision": SOURCE_REVISION,
            "model": MODEL,
            "model_revision": MODEL_REVISION,
            "weight_sha256": WEIGHT_SHA256,
            "decision_level": decision.level,
            "permutations": decision.diagnostics["permutations"],
            "prior": decision.diagnostics["prior_method"],
            "training_labels_used": 0,
            "probability_semantics": "l0_permutation_marginal_uncalibrated_for_market",
        }
        sys.stdout.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"anyjev_decide: {error}", file=sys.stderr)
        raise SystemExit(1) from error
