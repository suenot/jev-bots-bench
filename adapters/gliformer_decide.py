#!/usr/bin/env python3
"""CPU GLiFormer adapter for the weekly market JSONL protocol."""

from __future__ import annotations

import contextlib
import json
import math
import sys
import time

MODEL = "knowledgator/gliformer-large-v1"
REVISION = "d0a4e53d09cebe6bc963dd9be319d4279084bb2d"
TASK = "next_7_day_price_direction"
LABELS = ("up", "down")


def main() -> None:
    with contextlib.redirect_stdout(sys.stderr):
        from gliformer import GLiFormer

        model = GLiFormer.from_pretrained(MODEL, revision=REVISION, load_tokenizer=True)
        model = model.to("cpu").eval()

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
            # The upstream decoder applies a separate sigmoid to each class
            # and normally filters at 0.5. A negative threshold returns both.
            scores = model.classify(
                state, {TASK: list(LABELS)}, threshold=-1.0, multi_label=True
            )
        by_label = {item["class_name"]: float(item["score"]) for item in scores}
        if set(by_label) != set(LABELS):
            raise ValueError(f"line {line_number}: model omitted a direction score")
        up, down = (by_label[label] for label in LABELS)
        if not all(math.isfinite(value) and value >= 0 for value in (up, down)):
            raise ValueError(f"line {line_number}: invalid model scores")
        total = up + down
        if total <= 0:
            raise ValueError(f"line {line_number}: zero score mass")
        up, down = up / total, down / total
        prediction = "up" if up > down else "down"
        response = {
            "id": request["id"],
            "prediction": prediction,
            "probabilities": {"up": up, "down": down},
            "prob_up": up,
            "target_weight": float(prediction == "up"),
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "source": "gliformer-classifier",
            "model": MODEL,
            "model_revision": REVISION,
            "probability_semantics": "normalized_independent_sigmoid_scores",
        }
        sys.stdout.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"gliformer_decide: {error}", file=sys.stderr)
        raise SystemExit(1) from error
