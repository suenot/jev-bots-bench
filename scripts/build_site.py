#!/usr/bin/env python3
"""Build the static dashboard from the checked-in aggregate benchmark data."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site"
OUTPUT = SOURCE / "dist"
SUMMARY = ROOT / "results" / "summary.json"
INVENTORY = ROOT / "benchmark" / "models.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT, help="output directory for static assets")
    output = parser.parse_args().output.resolve()
    data = json.loads(SUMMARY.read_text())
    if data.get("schema_version") != 1 or not isinstance(data.get("models"), list) or not isinstance(data.get("runs"), list):
        raise ValueError("results/summary.json is missing required benchmark fields")
    inventory = json.loads(INVENTORY.read_text())["models"]
    expected_ids = {model["id"] for model in inventory}
    published_ids = {model["id"] for model in data["models"]}
    if len(data["models"]) != len(inventory) or published_ids != expected_ids:
        raise ValueError("published model catalog differs from benchmark inventory")
    output.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "styles.css", "app.js"):
        shutil.copy2(SOURCE / name, output / name)
    ignore_file = ".vercelignore" if output == OUTPUT else ".assetsignore"
    shutil.copy2(SOURCE / ignore_file, output / ignore_file)
    (output / "data").mkdir(exist_ok=True)
    shutil.copy2(SUMMARY, output / "data" / "summary.json")
    shutil.copy2(ROOT / "VERSION", output / "version.txt")
    print(f"Built {output} with {len(data['runs'])} measured rows and {len(data['models'])} catalog entries")


if __name__ == "__main__":
    main()
