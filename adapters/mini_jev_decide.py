#!/usr/bin/env python3
"""mini-jev B1 letter scorer on its pinned, frozen Qwen3-4B checkpoint."""

from __future__ import annotations

import contextlib
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

SOURCE_REVISION = "ca612198bfb69f538f029a4615f6d0a18b4f814c"
MODEL = "Qwen/Qwen3-4B-Instruct-2507"
MODEL_REVISION = "cdbee75f17c01a7cc42f958dc650907174af0554"
OPTIONS = ("down", "up")


def main() -> None:
    source = os.environ.get("MINI_JEV_SOURCE_DIR")
    checkpoint = os.environ.get("MINI_JEV_MODEL_PATH")
    if not source or not checkpoint:
        raise ValueError("Set MINI_JEV_SOURCE_DIR and MINI_JEV_MODEL_PATH")
    sys.path.insert(0, str(Path(source).resolve()))

    import torch
    from minijev.engine import Engine
    from minijev.letters import build_tables, candidate_logits_fp32, classify_argmax, score
    from minijev.prompts import SYSTEM_B, render

    with contextlib.redirect_stdout(sys.stderr):
        engine = Engine(model_id=checkpoint, device="cpu", attn="eager", dtype="float32")
    bare, space = build_tables(engine.tok)

    for line_number, line in enumerate(sys.stdin, 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            raise ValueError(f"line {line_number}: id must be a nonempty string")
        state = item.get("state")
        if not isinstance(state, str) or not state.strip():
            raise ValueError(f"line {line_number}: state must be a nonempty string")

        user = (
            f"TEXT:\n{state}\n\nQUESTION: What is the direction of the next seven-day return?\n"
            "A = down (zero or negative return)\n"
            "B = up (strictly positive return)\n\nANSWER:"
        )
        prompt = render(engine.tok, SYSTEM_B, user)
        started = time.perf_counter()
        hidden, _, _, _ = engine.last_hidden([prompt])
        bare_logits = candidate_logits_fp32(hidden, engine.embed_weight, bare[:2])[0]
        space_logits = candidate_logits_fp32(hidden, engine.embed_weight, space[:2])[0]
        result = score(bare_logits, space_logits)
        # Upstream rounds p_cand to six decimals for reporting. Preserve its
        # unrounded logit decision in the benchmark's probability contract.
        probabilities = [float(value) for value in torch.softmax(bare_logits.double(), dim=-1)]
        total = sum(probabilities)
        if not all(math.isfinite(value) and value >= 0 for value in probabilities) or total <= 0:
            raise ValueError(f"line {line_number}: invalid candidate scores")
        p_down, p_up = (value / total for value in probabilities)
        prediction = OPTIONS[result["pred_pos"]]
        full = engine.full_logits_from_hidden(hidden)[0].float()
        candidate_mass = float(torch.exp(torch.logsumexp(full[bare[:2]], dim=0) - torch.logsumexp(full, dim=0)))
        argmax_id = int(torch.argmax(full).item())
        response = {
            "id": item["id"],
            "prediction": prediction,
            "probabilities": {"up": p_up, "down": p_down},
            "prob_up": p_up,
            "target_weight": float(prediction == "up"),
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "source": "mini-jev-B1-frozen-Qwen3-4B",
            "source_revision": SOURCE_REVISION,
            "model": MODEL,
            "model_revision": MODEL_REVISION,
            "device": "cpu",
            "dtype": "float32",
            "score_mode": "bare-letter-logits",
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "candidate_mass": round(candidate_mass, 8),
            "argmax_class": classify_argmax(argmax_id, bare, space, 2),
        }
        sys.stdout.write(json.dumps(response, ensure_ascii=False, allow_nan=False) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"mini_jev_decide: {error}", file=sys.stderr)
        raise SystemExit(1) from error
