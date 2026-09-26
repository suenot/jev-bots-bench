#!/usr/bin/env python3
"""Split public model inputs for parallel inference and merge responses in original order."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def rows(path: Path) -> list[dict]:
    with path.open() as source:
        return [json.loads(line) for line in source if line.strip()]


def split(events: Path, directory: Path, count: int) -> None:
    if count < 1:
        raise ValueError("shards must be positive")
    requests = rows(events)
    directory.mkdir(parents=True, exist_ok=True)
    outputs = [directory / f"events-{index:02d}.jsonl" for index in range(count)]
    if any(path.exists() for path in outputs):
        raise FileExistsError("shard output exists")
    files = [path.open("x") for path in outputs]
    try:
        for index, request in enumerate(requests):
            files[index % count].write(json.dumps(request, sort_keys=True, allow_nan=False) + "\n")
    finally:
        for file in files:
            file.close()
    print(f"split {len(requests)} events into {count} shards")


def merge(events: Path, response_files: list[Path], output: Path) -> None:
    event_ids = [row["id"] for row in rows(events)]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("event ids are not unique")
    responses = {}
    for path in response_files:
        for response in rows(path):
            event_id = response["id"]
            if event_id in responses:
                raise ValueError(f"duplicate response id: {event_id}")
            responses[event_id] = response
    if set(responses) != set(event_ids):
        raise ValueError("merged responses do not cover exactly the input events")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as target:
        for event_id in event_ids:
            target.write(json.dumps(responses[event_id], sort_keys=True, allow_nan=False) + "\n")
    print(f"merged {len(event_ids)} responses: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    partition = commands.add_parser("split")
    partition.add_argument("--events", type=Path, required=True)
    partition.add_argument("--dir", type=Path, required=True)
    partition.add_argument("--shards", type=int, required=True)
    combine = commands.add_parser("merge")
    combine.add_argument("--events", type=Path, required=True)
    combine.add_argument("--responses", type=Path, nargs="+", required=True)
    combine.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "split":
        split(args.events, args.dir, args.shards)
    else:
        merge(args.events, args.responses, args.output)


if __name__ == "__main__":
    main()
