#!/usr/bin/env python3
"""Exercise the GLiFormer JSONL contract without installing it or loading weights."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import types
from pathlib import Path


class FakeModel:
    @classmethod
    def from_pretrained(cls, model, *, revision, load_tokenizer):
        assert model == "knowledgator/gliformer-large-v1"
        assert revision == "d0a4e53d09cebe6bc963dd9be319d4279084bb2d"
        assert load_tokenizer is True
        return cls()

    def to(self, device):
        assert device == "cpu"
        return self

    def eval(self):
        return self

    def classify(self, state, classes, *, threshold, multi_label):
        assert state == "Weekly momentum is positive."
        assert classes == {"next_7_day_price_direction": ["up", "down"]}
        assert threshold == -1.0 and multi_label is True
        return [{"class_name": "up", "score": 0.8},
                {"class_name": "down", "score": 0.2}]


def main() -> None:
    fake_gliformer = types.ModuleType("gliformer")
    fake_gliformer.GLiFormer = FakeModel
    sys.modules["gliformer"] = fake_gliformer
    spec = importlib.util.spec_from_file_location("gliformer_decide", Path(__file__).with_name("gliformer_decide.py"))
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
    assert response["probabilities"] == {"up": 0.8, "down": 0.2}
    assert response["probability_semantics"] == "normalized_independent_sigmoid_scores"
    print("GLiFormer mock JSONL smoke: ok")


if __name__ == "__main__":
    main()
