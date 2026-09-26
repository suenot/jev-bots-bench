#!/usr/bin/env python3
"""CPU GLiNER2.5-Decide adapter for the weekly market JSONL protocol."""

from __future__ import annotations

import contextlib
import json
import os
import sys
import time

MODEL = "fastino/GLiNER2.5-Decide"
REVISION = "7ee5da4c2415e32259bcdc0b1a7367c32ce8d6f6"
TASK = "next_7_day_price_direction"
LABELS = ("up", "down")


def main() -> None:
    # Keep stdout reserved for one JSON response per request. Some model loaders
    # print progress during initialization or inference.
    with contextlib.redirect_stdout(sys.stderr):
        from gliner2 import AutoExtractor

        local_path = os.environ.get("GLINER_MODEL_PATH")
        if local_path:
            model = AutoExtractor.from_pretrained(local_path, map_location="cpu")
        else:
            model = AutoExtractor.from_pretrained(MODEL, revision=REVISION, map_location="cpu")

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
            result = model.classify_text(state, {TASK: list(LABELS)})
        prediction = result[TASK]
        if prediction not in LABELS:
            raise ValueError(f"line {line_number}: unexpected class {prediction!r}")
        response = {
            "id": request["id"],
            "prediction": prediction,
            "target_weight": float(prediction == "up"),
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "source": "gliner2-autoextractor",
            "model": MODEL,
            "model_revision": REVISION,
        }
        sys.stdout.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"gliner_decide: {error}", file=sys.stderr)
        raise SystemExit(1) from error
