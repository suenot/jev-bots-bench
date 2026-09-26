#!/usr/bin/env python3
"""Exercise the Laya JSONL contract without installing Laya or loading weights."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import types
from pathlib import Path


class FakeModel:
    def predict(self, state, questions):
        assert state == "Weekly momentum is positive."
        assert list(questions) == ["next_7_day_price_direction"]
        return {"answers": {"next_7_day_price_direction": {
            "probabilities": {"up": 0.7001, "down": 0.2999}
        }}}


def main() -> None:
    fake_laya = types.ModuleType("laya")

    def load(model, *, device, revision):
        assert model == "convaiinnovations/laya"
        assert device == "cpu"
        assert revision == "55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851"
        return FakeModel()

    fake_laya.load = load
    sys.modules["laya"] = fake_laya
    spec = importlib.util.spec_from_file_location("laya_decide", Path(__file__).with_name("laya_decide.py"))
    adapter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(adapter)

    original_stdin = sys.stdin
    sys.stdin = io.StringIO('{"id":"event-1","state":"Weekly momentum is positive."}\n')
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output):
            adapter.main()
    finally:
        sys.stdin = original_stdin
    response = json.loads(output.getvalue())
    assert response["id"] == "event-1"
    assert response["prediction"] == "up"
    assert response["probabilities"] == {"up": 0.7001, "down": 0.2999}
    assert response["target_weight"] == 1.0
    assert response["model_revision"] == adapter.REVISION
    print("Laya mock JSONL smoke: ok")


if __name__ == "__main__":
    main()
