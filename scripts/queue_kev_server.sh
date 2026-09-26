#!/usr/bin/env bash
# Run pinned Kev after the existing CPU queues, without moving market history.
set -euo pipefail

bench_root="${1:-/mnt/third/jev-bots-bench}"
cd "$bench_root"
mkdir -p weekly
exec 9>weekly/kev-queue.lock
if ! flock -n 9; then
  printf 'Kev queue already holds the lock\n' >&2
  exit 1
fi

log() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$*"; }
expected=1382
event_sha=d17d4fb3bfcacd898e0a81a07ed704d598f931fc4db9ff683ba649646fdbbecc
paths=(
  weekly/responses-gliner25.jsonl
  weekly/responses-nico_open_jev.jsonl
  weekly/responses-gliformer.jsonl
  weekly/simple-shards/responses-00.jsonl
  weekly/simple-shards/responses-01.jsonl
  weekly/simple-shards/responses-02.jsonl
  weekly/simple-shards/responses-03.jsonl
)
counts=(1382 1382 1382 346 346 345 345)
patterns=(
  '^python3 benchmark/run.py invoke --events weekly/events.jsonl --output weekly/responses-gliner25.jsonl'
  '^python3 benchmark/run.py invoke --events weekly/events.jsonl --output weekly/responses-nico_open_jev.jsonl'
  '^python3 benchmark/run.py invoke --events weekly/events.jsonl --output weekly/responses-gliformer.jsonl'
  '^python3 benchmark/run.py invoke --events weekly/simple-shards/events-00.jsonl --output weekly/simple-shards/responses-00.jsonl'
  '^python3 benchmark/run.py invoke --events weekly/simple-shards/events-01.jsonl --output weekly/simple-shards/responses-01.jsonl'
  '^python3 benchmark/run.py invoke --events weekly/simple-shards/events-02.jsonl --output weekly/simple-shards/responses-02.jsonl'
  '^python3 benchmark/run.py invoke --events weekly/simple-shards/events-03.jsonl --output weekly/simple-shards/responses-03.jsonl'
)

check_events() {
  [[ $(wc -l < weekly/events.jsonl) -eq $expected ]] || {
    log "wrong event count (expected $expected)" >&2
    exit 1
  }
  printf '%s  weekly/events.jsonl\n' "$event_sha" | sha256sum --check --status || {
    log "event SHA-256 mismatch" >&2
    exit 1
  }
}

check_events
log "Kev queue started pid=$$ nice=$(ps -o ni= -p $$ | tr -d ' ') event_sha=$event_sha"
while :; do
  ready=1
  progress=()
  for i in "${!paths[@]}"; do
    count=0
    [[ ! -f "${paths[$i]}" ]] || count=$(wc -l < "${paths[$i]}")
    progress+=("$count/${counts[$i]}")
    if (( count > counts[i] )); then
      log "too many responses in ${paths[$i]}: $count" >&2
      exit 1
    fi
    if (( count < counts[i] )); then
      ready=0
      if ! pgrep -f "${patterns[$i]}" >/dev/null; then
        log "predecessor stopped incomplete: ${paths[$i]} $count/${counts[$i]}" >&2
        exit 1
      fi
    elif pgrep -f "${patterns[$i]}" >/dev/null; then
      ready=0
    fi
  done
  (( ready == 0 )) || break
  log "waiting initial streams: ${progress[*]}"
  sleep 120 9>&-
done

check_events
python3 - <<'PY'
import json
from pathlib import Path

events = [json.loads(line)['id'] for line in Path('weekly/events.jsonl').open()]
if events != [f'e{i:06d}' for i in range(1, 1383)]:
    raise SystemExit('Kev queue: event IDs are not e000001..e001382 in order')
for name in ('gliner25', 'nico_open_jev', 'gliformer'):
    got = [json.loads(line)['id'] for line in Path(f'weekly/responses-{name}.jsonl').open()]
    if got != events:
        raise SystemExit(f'Kev queue: predecessor IDs differ for {name}')
for i in range(4):
    shard = [json.loads(line)['id'] for line in Path(f'weekly/simple-shards/events-{i:02d}.jsonl').open()]
    got = [json.loads(line)['id'] for line in Path(f'weekly/simple-shards/responses-{i:02d}.jsonl').open()]
    if got != shard:
        raise SystemExit(f'Kev queue: simple shard IDs differ for {i:02d}')
print('Kev queue: all 1,382 event IDs and seven predecessor streams match', flush=True)
PY

# Existing queued model runs are allowed to finish first. Waiting for their
# wrapper processes also covers the short gap between chained models.
other_queues=(
  '^bash weekly/run-anyjev-after-gliner-nico.sh'
  '^bash weekly/run-jevk5-after-current.sh'
  '^bash weekly/run-semif-after-jevk5.sh'
  '^bash weekly/run-zefan-after-semif.sh'
  '^bash scripts/queue_nano_mino_server.sh'
  '^bash scripts/run_mini_jev_after_mino.sh'
  '^python3 benchmark/run.py invoke '
  'llama-jevk5/build/bin/llama-server'
  'jev.server.*zefan-open-jev'
)
while :; do
  busy=()
  for pattern in "${other_queues[@]}"; do
    if pgrep -f "$pattern" >/dev/null; then busy+=("$pattern"); fi
  done
  (( ${#busy[@]} > 0 )) || break
  log "waiting for existing model jobs: ${busy[*]}"
  sleep 120 9>&-
done

check_events
if pgrep -f '^python3 benchmark/run.py invoke .*weekly/responses-kev.jsonl' >/dev/null; then
  log 'another Kev invoke is running' >&2
  exit 1
fi
printf '%s  %s\n' \
  'f91272dd2ceb3d595de788aa1d24defc2b08e60588856dd83947536833a9c181' 'kev-runtime.tar.gz' \
  '9b908623acb162118575f4e7a94524f9c139c335be4bfb74d6cfceca01e1885a' 'models/kev-0.8b/adapter_model.safetensors' \
  'f400bd12802b2b105ae45d6b03774a158a3db4fccff42413734ddca2e5c920b6' 'models/kev-0.8b/head.pt' \
  'c2b1e5a17d9c1e27685d92ed9b382911ebb99955ecd89052d1721241adfbab6c' 'models/kev-qwen35-base/model.safetensors-00001-of-00001.safetensors' | sha256sum --check
test -x .venv-kev/bin/python

export KEV_CHECKPOINT_DIR="$bench_root/models/kev-0.8b"
export KEV_BASE_DIR="$bench_root/models/kev-qwen35-base"
export KEV_THREADS=2 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export TOKENIZERS_PARALLELISM=false HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
log 'pinned events/models verified; starting Kev with --resume'
nice -n 19 python3 benchmark/run.py invoke \
  --events weekly/events.jsonl \
  --output weekly/responses-kev.jsonl \
  --resume --timeout-seconds 900 \
  -- .venv-kev/bin/python adapters/kev_decide.py \
  >> weekly/kev-invoke.log 2>&1
[[ $(wc -l < weekly/responses-kev.jsonl) -eq $expected ]] || {
  log 'Kev invoke exited without 1,382 responses' >&2
  exit 1
}
log 'Kev 1,382-event invoke completed'
