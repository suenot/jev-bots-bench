#!/usr/bin/env python3
"""Verify published hashes and replay aggregate scores without raw minute candles."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def verify(path: str, expected: str) -> None:
    actual = digest(ROOT / path)
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch for {path}: {actual}")


def equivalent(left: object, right: object) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(equivalent(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(equivalent(a, b) for a, b in zip(left, right))
    return left == right


def main() -> None:
    record = json.loads((ROOT / "results/model-provenance.json").read_text())
    inventory = {
        model["id"]: model
        for model in json.loads((ROOT / "benchmark/models.json").read_text())["models"]
    }
    verify("benchmark/run.py", record["runner_sha256"])
    verify("data/weekly-v1/events.jsonl", record["benchmark_event_sha256"])
    verify("data/weekly-v1/settlements.jsonl", record["settlement_sha256"])
    with (ROOT / "data/weekly-v1/events.jsonl").open() as source:
        event_ids = [json.loads(line)["id"] for line in source if line.strip()]
    specs = []
    for model in record["models"]:
        pinned = inventory[model["id"]]
        if model["source_revision"] != pinned["source_sha"] or model.get("weights_revision") != pinned.get("weights_sha"):
            raise ValueError(f"source or weight revision differs from inventory: {model['id']}")
        verify(model["adapter_path"], model["adapter_sha256"])
        verify(model["environment_path"], model["environment_sha256"])
        verify(model["responses_path"], model["responses_sha256"])
        with (ROOT / model["responses_path"]).open() as source:
            response_ids = [json.loads(line)["id"] for line in source if line.strip()]
        if len(response_ids) != model["response_count"] or response_ids != event_ids:
            raise ValueError(f"response count or event order mismatch for {model['id']}")
        specs.append(f"{model['id']}={ROOT / model['responses_path']}")
    with TemporaryDirectory() as directory:
        output = Path(directory) / "summary.json"
        subprocess.run([sys.executable, str(ROOT / "benchmark/run.py"), "evaluate",
                        "--events", str(ROOT / "data/weekly-v1/events.jsonl"),
                        "--settlements", str(ROOT / "data/weekly-v1/settlements.jsonl"),
                        "--models", str(ROOT / "benchmark/models.json"),
                        "--responses", *specs,
                        "--output", str(output)], check=True)
        replayed = json.loads(output.read_text())
    published = json.loads((ROOT / "results/summary.json").read_text())
    for key in ("schema_version", "status", "methodology", "models", "runs", "baselines", "provenance"):
        if not equivalent(replayed[key], published[key]):
            raise ValueError(f"published aggregate differs from replay: {key}")
    print(f"verified {len(specs)} model response files and {len(published['runs'])} published model rows")


if __name__ == "__main__":
    main()
