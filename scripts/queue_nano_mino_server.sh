#!/usr/bin/env bash
# Continue the pinned NanoJev and minojev CPU runs after the short model runs.
set -euo pipefail

bench_root="${1:-/mnt/third/jev-bots-bench}"
cd "$bench_root"
weekly="$bench_root/weekly"
expected=1382
event_sha="d17d4fb3bfcacd898e0a81a07ed704d598f931fc4db9ff683ba649646fdbbecc"

check_events() {
  printf '%s  %s\n' "$event_sha" "$weekly/events.jsonl" | sha256sum --check --status
}

check_response_ids() {
  python3 - "$weekly/events.jsonl" "$1" <<'PY'
import json
import sys

def ids(path):
    with open(path, encoding="utf-8") as stream:
        return [json.loads(line)["id"] for line in stream if line.strip()]

if ids(sys.argv[1]) != ids(sys.argv[2]):
    raise SystemExit(f"Response IDs differ from events: {sys.argv[2]}")
PY
}

exec 9>"$weekly/nano-mino-queue.lock"
flock -n 9 || { printf 'Nano/mino queue is already running\n'; exit 0; }
test "$(wc -l < "$weekly/events.jsonl")" -eq "$expected"
check_events

while [[ ! -f "$weekly/responses-gliner25.jsonl" || ! -f "$weekly/responses-nico_open_jev.jsonl" ]] ||
      [[ "$(wc -l < "$weekly/responses-gliner25.jsonl")" -ne "$expected" ]] ||
      [[ "$(wc -l < "$weekly/responses-nico_open_jev.jsonl")" -ne "$expected" ]]; do
  for predecessor in "$weekly/responses-gliner25.jsonl" "$weekly/responses-nico_open_jev.jsonl"; do
    if [[ -f "$predecessor" && "$(wc -l < "$predecessor")" -gt "$expected" ]]; then
      printf 'Response count exceeds %s: %s\n' "$expected" "$predecessor" >&2
      exit 1
    fi
  done
  sleep 120
done
python3 - "$weekly/events.jsonl" "$weekly/responses-gliner25.jsonl" \
  "$weekly/responses-nico_open_jev.jsonl" <<'PY'
import json
import sys

expected = [json.loads(line)["id"] for line in open(sys.argv[1])]
for path in sys.argv[2:]:
    actual = [json.loads(line)["id"] for line in open(path)]
    if actual != expected:
        raise SystemExit(f"Response IDs differ from events: {path}")
PY
# Let the completed short-run adapters release their resident model weights.
sleep 120

export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2

run_model() {
  local model_id="$1" adapter="$2" python_bin="$3" output="$4" log="$5"
  check_events
  if [[ -f "$output" && "$(wc -l < "$output")" -eq "$expected" ]]; then
    check_response_ids "$output"
    printf '%s already has %s responses\n' "$model_id" "$expected"
    return
  fi
  printf 'Starting %s at %s\n' "$model_id" "$(date -u +%FT%TZ)"
  nice -n 19 python3 benchmark/run.py invoke --resume \
    --events "$weekly/events.jsonl" --output "$output" \
    -- "$python_bin" "$adapter" >> "$log" 2>&1
  test "$(wc -l < "$output")" -eq "$expected"
  check_response_ids "$output"
  printf 'Completed %s at %s\n' "$model_id" "$(date -u +%FT%TZ)"
}

export NANOJEV_CHECKPOINT_DIR="$bench_root/models/nanojev-unified"
export NANOJEV_SOURCE_DIR="$bench_root/nanojev-source"
export NANOJEV_THREADS=2
run_model nanojev adapters/nanojev_decide.py .venv-nanojev/bin/python \
  "$weekly/responses-nanojev.jsonl" "$weekly/nanojev-invoke.log"

export MINOJEV_MODEL_PATH="$bench_root/models/minojev-general"
run_model minojev adapters/minojev_decide.py .venv-minojev/bin/python \
  "$weekly/responses-minojev.jsonl" "$weekly/minojev-invoke.log"
