#!/usr/bin/env python3
"""Adapt the pinned Zefan-Cai/Open-Jev 2B HTTP server to benchmark JSONL."""

from __future__ import annotations

import json
import math
import os
import sys
import time
import urllib.request

SOURCE_REVISION = "3308a15ccd7eea1df7a37d6ddc39b023b801ba16"
PACKAGE = "ZefanCai/Open-Jev-2B"
PACKAGE_REVISION = "0c7aa498b1627be8da4acf34c863ff0ee0a92785"
BASE = "Qwen/Qwen3.5-2B"
BASE_REVISION = "15852e8c16360a2fea060d615a32b45270f8a8fc"
CHECKPOINT_SHA256 = "3076462e6356412082e79af909227b39b2863b90def79155ca0821aa506b7ded"
TASK = "next_7_day_price_direction"
QUESTION = {"type": "choice", "instructions": TASK, "criteria": {"up": "Up", "down": "Down"}}


def main() -> None:
    url = os.environ.get("ZEFAN_OPEN_JEV_SERVER_URL", "http://127.0.0.1:18086").rstrip("/")
    for line_number, line in enumerate(sys.stdin, 1):
        if not line.strip():
            continue
        request = json.loads(line)
        if not isinstance(request, dict) or not isinstance(request.get("id"), str):
            raise ValueError(f"line {line_number}: id must be a string")
        state = request.get("state")
        if not isinstance(state, str) or not state.strip():
            raise ValueError(f"line {line_number}: state must be a nonempty string")

        payload = json.dumps({"state": state, "questions": {TASK: QUESTION}}, ensure_ascii=False).encode()
        http_request = urllib.request.Request(
            url + "/v1/systemone", data=payload, headers={"Content-Type": "application/json"}
        )
        started = time.perf_counter()
        with urllib.request.urlopen(http_request, timeout=900) as response:
            result = json.load(response)
        metadata = result.get("metadata", {})
        if metadata.get("method") != "lora_decision_head":
            raise ValueError(f"line {line_number}: wrong Open-Jev inference method")
        if metadata.get("base_revision") != BASE_REVISION:
            raise ValueError(f"line {line_number}: wrong base model revision")
        if metadata.get("checkpoint_sha256") != CHECKPOINT_SHA256:
            raise ValueError(f"line {line_number}: wrong trained checkpoint hash")
        if result.get("model") != BASE:
            raise ValueError(f"line {line_number}: wrong base model")
        probabilities = result["answers"][TASK]["probabilities"]
        up, down = (float(probabilities[label]) for label in ("up", "down"))
        if not all(math.isfinite(value) and value >= 0 for value in (up, down)):
            raise ValueError(f"line {line_number}: invalid probabilities")
        total = up + down
        if total <= 0:
            raise ValueError(f"line {line_number}: zero probability mass")
        up, down = up / total, down / total
        prediction = "up" if up > down else "down"
        row = {
            "id": request["id"],
            "prediction": prediction,
            "probabilities": {"up": up, "down": down},
            "prob_up": up,
            "target_weight": float(prediction == "up"),
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "source": "zefan-open-jev-2b",
            "source_revision": SOURCE_REVISION,
            "model": PACKAGE,
            "model_revision": PACKAGE_REVISION,
            "base_model": BASE,
            "base_revision": BASE_REVISION,
            "checkpoint_sha256": CHECKPOINT_SHA256,
        }
        sys.stdout.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"zefan_open_jev_decide: {error}", file=sys.stderr)
        raise SystemExit(1) from error
