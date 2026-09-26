#!/usr/bin/env python3
"""Adapt pinned JevK5 4B v0.3 GGUF decisions to the weekly JSONL contract."""

from __future__ import annotations

import json
import math
import os
import sys
import time

SOURCE_REVISION = "1e5ae1b533b9eb80c0cbe3fbd010607d0b4e26ae"
MODEL = "alibiserikbay/JevK5-GGUF/jevk5-4b-v0.3-Q4_K_M.gguf"
MODEL_REVISION = "ec67b0bfce5119a8b11a2cdb430bb43e3fa3e82a"
MODEL_SHA256 = "94ca0d7745c47f79091b0892ca657c81d9dc9e4ed0238ba0a7ea261d8938c882"
LLAMA_REVISION = "9575389609d6f8437de0b205561a4824d217c409"
TASK = "next_7_day_price_direction"
QUESTION = {
    "type": "choice",
    "instructions": TASK,
    "criteria": {"up": "Up", "down": "Down"},
}


def main() -> None:
    from jevk5 import JevK5GGUF

    model = JevK5GGUF(
        url=os.environ.get("JEVK5_SERVER_URL", "http://127.0.0.1:8080"),
        temperature=1.22,
        knockout_temperature=0.93,
        top_k=128,
    )
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
        missing_before = model.missing
        result = model.decide(state, QUESTION)
        if model.missing != missing_before:
            raise ValueError(f"line {line_number}: answer-letter log probability missing from llama-server response")
        probabilities = result["probabilities"]
        up, down = (float(probabilities[label]) for label in ("up", "down"))
        if not all(math.isfinite(value) and value >= 0 for value in (up, down)):
            raise ValueError(f"line {line_number}: invalid model probabilities")
        total = up + down
        if total <= 0:
            raise ValueError(f"line {line_number}: zero probability mass")
        up, down = up / total, down / total
        prediction = "up" if up > down else "down"
        response = {
            "id": request["id"],
            "prediction": prediction,
            "probabilities": {"up": up, "down": down},
            "prob_up": up,
            "target_weight": float(prediction == "up"),
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "source": "jevk5-gguf",
            "source_revision": SOURCE_REVISION,
            "model": MODEL,
            "model_revision": MODEL_REVISION,
            "model_sha256": MODEL_SHA256,
            "llama_revision": LLAMA_REVISION,
            "temperature": 1.22,
        }
        sys.stdout.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"jevk5_decide: {error}", file=sys.stderr)
        raise SystemExit(1) from error
