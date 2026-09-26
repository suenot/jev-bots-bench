#!/usr/bin/env python3
"""Build the static dashboard from the checked-in aggregate benchmark data."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "site"
OUTPUT = SOURCE / "dist"
SUMMARY = ROOT / "results" / "summary.json"


def main() -> None:
    data = json.loads(SUMMARY.read_text())
    if data.get("schema_version") != 1 or not isinstance(data.get("models"), list) or not isinstance(data.get("runs"), list):
        raise ValueError("results/summary.json is missing required benchmark fields")
    if len(data["models"]) != 16:
        raise ValueError("benchmark inventory must contain all 16 engines")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "styles.css", "app.js", ".vercelignore"):
        shutil.copy2(SOURCE / name, OUTPUT / name)
    (OUTPUT / "data").mkdir(exist_ok=True)
    shutil.copy2(SUMMARY, OUTPUT / "data" / "summary.json")
    shutil.copy2(ROOT / "VERSION", OUTPUT / "version.txt")
    print(f"Built {OUTPUT} with {len(data['runs'])} measured rows and {len(data['models'])} engines")


if __name__ == "__main__":
    main()
