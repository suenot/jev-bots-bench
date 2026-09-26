#!/usr/bin/env python3
"""Pinned minojev general-checkpoint CPU adapter for weekly market JSONL."""

from __future__ import annotations

import contextlib
import json
import math
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

MODEL = "zeredy879/minojev/general"
MODEL_REVISION = "e1e4bbec238c36af6db1af3b1890634440228cb7"
SOURCE_REVISION = "622dd952c3db2769a7a32d1a13cc89db04bba95e"
TASK = "next_7_day_price_direction"
OPTIONS = {
    "up": "The next seven-day return is strictly positive.",
    "down": "The next seven-day return is zero or negative.",
}


def main() -> None:
    checkpoint = os.environ.get("MINOJEV_MODEL_PATH")
    if not checkpoint:
        raise ValueError("MINOJEV_MODEL_PATH must point to the pinned general/ checkpoint")

    # Upstream emits logs during model load; stdout is the JSONL protocol.
    with contextlib.redirect_stdout(sys.stderr):
        from minojev import DecisionModel, ScoreOptions, request_from_object
        from transformers import AutoTokenizer

        # The published tokenizer config has a list here, while Transformers
        # 4.56 expects a mapping. Supply equivalent named tokens in memory.
        tokenizer_dir = Path(checkpoint).resolve() / "backbone"
        tokenizer_config = json.loads((tokenizer_dir / "tokenizer_config.json").read_text())
        extra_tokens = tokenizer_config.get("extra_special_tokens", {})
        if isinstance(extra_tokens, list):
            extra_tokens = {f"special_token_{index}": token for index, token in enumerate(extra_tokens)}
        original_loader = AutoTokenizer.from_pretrained

        def load_tokenizer(cls, path, *args, **kwargs):
            if Path(path).resolve() == tokenizer_dir:
                kwargs.setdefault("extra_special_tokens", extra_tokens)
            return original_loader(path, *args, **kwargs)

        with patch.object(AutoTokenizer, "from_pretrained", classmethod(load_tokenizer)):
            model = DecisionModel.load(checkpoint, device="cpu")
    settings = ScoreOptions(mode="fresh", batch_requests=1, device="cpu")

    for line_number, line in enumerate(sys.stdin, 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            raise ValueError(f"line {line_number}: id must be a nonempty string")
        state = item.get("state")
        if not isinstance(state, str) or not state.strip():
            raise ValueError(f"line {line_number}: state must be a nonempty string")

        request = request_from_object({
            "id": item["id"],
            "state": state,
            "questions": {
                TASK: {
                    "type": "choice",
                    "instructions": TASK,
                    "options": OPTIONS,
                }
            },
        })
        started = time.perf_counter()
        with contextlib.redirect_stdout(sys.stderr):
            answer = model.score([request], settings)[0]
        scores = dict(zip(answer["candidate_ids"], answer["probabilities"], strict=True))
        if set(scores) != set(OPTIONS):
            raise ValueError(f"line {line_number}: incomplete choice distribution")
        up, down = (float(scores[label]) for label in OPTIONS)
        if not all(math.isfinite(value) and value >= 0 for value in (up, down)):
            raise ValueError(f"line {line_number}: invalid choice probability")
        total = up + down
        if total <= 0:
            raise ValueError(f"line {line_number}: zero probability mass")
        up, down = up / total, down / total
        prediction = "up" if up > down else "down"
        response = {
            "id": item["id"],
            "prediction": prediction,
            "probabilities": {"up": up, "down": down},
            "prob_up": up,
            "target_weight": float(prediction == "up"),
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "source": "minojev-trained-general-head",
            "source_revision": SOURCE_REVISION,
            "model": MODEL,
            "model_revision": MODEL_REVISION,
            "score_mode": "fresh",
            "choice_temperature": 0.2706,
        }
        sys.stdout.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"minojev_decide: {error}", file=sys.stderr)
        raise SystemExit(1) from error
