#!/usr/bin/env python3
"""CPU Laya adapter for the weekly market JSONL protocol."""

from __future__ import annotations

import contextlib
import json
import math
import sys
import time

MODEL = "convaiinnovations/laya"
REVISION = "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851"
TASK = "next_7_day_price_direction"
LABELS = ("up", "down")
QUESTIONS = {
    TASK: {
        "type": "choice",
        "instructions": TASK,
        "criteria": {label: label for label in LABELS},
    }
}


def main() -> None:
    # The direct SDK keeps one English checkpoint resident across all rows.
    # Its model loader and dependencies must not write to protocol stdout.
    with contextlib.redirect_stdout(sys.stderr):
        import laya

        model = laya.load(MODEL, device="cpu", revision=REVISION)

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
            result = model.predict(state, QUESTIONS)
        probabilities = result["answers"][TASK]["probabilities"]
        up, down = (float(probabilities[label]) for label in LABELS)
        if not all(math.isfinite(value) and value >= 0 for value in (up, down)):
            raise ValueError(f"line {line_number}: invalid model probabilities")
        total = up + down
        if total <= 0:
            raise ValueError(f"line {line_number}: zero probability mass")
        # Laya rounds each returned choice probability to four decimals.
        up, down = up / total, down / total
        prediction = "up" if up > down else "down"
        response = {
            "id": request["id"],
            "prediction": prediction,
            "probabilities": {"up": up, "down": down},
            "prob_up": up,
            "target_weight": float(prediction == "up"),
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "source": "laya-direct-sdk",
            "model": MODEL,
            "model_revision": REVISION,
        }
        sys.stdout.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"laya_decide: {error}", file=sys.stderr)
        raise SystemExit(1) from error
