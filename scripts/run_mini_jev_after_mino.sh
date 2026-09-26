#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVENTS="$ROOT/weekly/events.jsonl"
DEPENDENCY="$ROOT/weekly/responses-minojev.jsonl"
OUTPUT="$ROOT/weekly/responses-mini-jev.jsonl"
RUNTIME="$ROOT/.runtime-mini-jev"
EVENTS_SHA256=d17d4fb3bfcacd898e0a81a07ed704d598f931fc4db9ff683ba649646fdbbecc

verify_events() {
  printf '%s  %s\n' "$EVENTS_SHA256" "$EVENTS" | sha256sum --check
}

mkdir -p "$RUNTIME"
exec 9>"$RUNTIME/full-run.lock"
flock -n 9 || { echo "mini-jev full-run queue already active"; exit 1; }

expected=$(wc -l < "$EVENTS")
printf 'waiting_for_minojev expected_ids=%s dependency=%s\n' "$expected" "$DEPENDENCY"
while :; do
  if [[ -f "$DEPENDENCY" ]]; then
    count=$(wc -l < "$DEPENDENCY")
    if (( count > expected )); then
      echo "minojev response count exceeds event count" >&2
      exit 1
    fi
    if (( count == expected )); then
      break
    fi
  fi
  sleep 60
done

verify_events
python3 - "$EVENTS" "$DEPENDENCY" <<'PY'
import json
import sys

def ids(path):
    with open(path, encoding="utf-8") as stream:
        return [json.loads(line)["id"] for line in stream if line.strip()]

events, responses = (ids(path) for path in sys.argv[1:])
if not events or events != responses:
    raise SystemExit("minojev response IDs are not the exact event sequence")
print(f"minojev_complete verified_ids={len(events)}", flush=True)
PY

cd "$ROOT"
export MINI_JEV_SOURCE_DIR="$ROOT/.runtime-mini-jev/source"
export MINI_JEV_MODEL_PATH="$ROOT/models/mini-jev-qwen3-4b"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
verify_events
printf 'starting_mini_jev events=%s output=%s\n' "$EVENTS" "$OUTPUT"
exec nice -n 19 taskset -c 18,19 python3 benchmark/run.py invoke \
  --events "$EVENTS" --output "$OUTPUT" --resume -- \
  "$ROOT/.venv-mini-jev/bin/python" adapters/mini_jev_decide.py
