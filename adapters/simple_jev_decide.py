#!/usr/bin/env python3
"""Run pinned Simple Jev on one causal market state per JSONL line."""

from __future__ import annotations

import asyncio
import contextlib
import json
import math
import os
import sys
import time

MODEL = "Qwen/Qwen3.5-0.8B"
MODEL_REVISION = "2fc06364715b967f1860aea9cf38778875588b17"
SOURCE_REVISION = "c077d5dfdb5c2c7dd24b17d5f556f07e0162dc1c"
TASK = "next_7_day_price_direction"


async def serve() -> None:
    # The source package is installed from the pinned Simple Jev checkout.
    with contextlib.redirect_stdout(sys.stderr):
        from hf_server import load_service

        model_path = os.environ.get("SIMPLE_JEV_MODEL_PATH", MODEL)
        service = load_service(
            model_path,
            revision=None if model_path != MODEL else MODEL_REVISION,
            served_model_name=MODEL,
            device="cpu",
            dtype="float32",
            prompt_policy="baseline",
            max_model_len=2048,
            max_choice_options=2,
            max_batch_size=1,
            max_batch_tokens=2048,
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
        with contextlib.redirect_stdout(sys.stderr):
            result = await service.classify({
                "model": MODEL,
                "state": state,
                "questions": {
                    TASK: {
                        "type": "choice",
                        "instructions": TASK,
                        "criteria": {"up": "Up", "down": "Down"},
                    }
                },
            })
        probabilities = result["answers"][TASK]["probabilities"]
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
            "source": "simple-jev-hf",
            "source_revision": SOURCE_REVISION,
            "model": MODEL,
            "model_revision": MODEL_REVISION,
            "prompt_policy": "baseline",
        }
        sys.stdout.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        asyncio.run(serve())
    except Exception as error:
        print(f"simple_jev_decide: {error}", file=sys.stderr)
        raise SystemExit(1) from error
