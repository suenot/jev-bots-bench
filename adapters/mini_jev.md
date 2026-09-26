# mini-jev: frozen Qwen letter scorer on CPU

[mini-jev](https://github.com/r-ms/mini-jev/tree/ca612198bfb69f538f029a4615f6d0a18b4f814c)
is a decision *method*, not a separately trained Jev model. Its published B1
path reads next-token logits for lettered options from the frozen
[Qwen3-4B-Instruct-2507 checkpoint](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/tree/cdbee75f17c01a7cc42f958dc650907174af0554).
The source is pinned to `ca612198bfb69f538f029a4615f6d0a18b4f814c` and
the weights to `cdbee75f17c01a7cc42f958dc650907174af0554`. No benchmark
outcomes or market labels are used for training.

The source README documents MPS/CUDA experiments, but its `Engine` accepts
`device="cpu"`. This adapter uses that published engine, its prompt renderer,
single-token letter table, fp32 candidate-logit calculation, and B1 scorer.
It loads the **same unmodified Qwen weights** in CPU `float32`, because this
older Xeon has no native bfloat16 acceleration. This numerical run mode is
different from the author's bfloat16 GPU study and must be reported as such.
The CPU runtime uses Python 3.12 and PyTorch 2.8; the source package is
imported from the pinned archive because its original experiment pins Python
3.11 and PyTorch 2.5.1. No source code or checkpoint weights are patched.
The benchmark task is fixed before scoring: `A = down` means next seven-day
return is zero or negative, `B = up` means strictly positive. Ties go to A.
The adapter reads only each event's supplied historical `state`; it never
reads outcome labels or future candles.

The output shares are the unrounded softmax of the two *bare-letter logits*;
the source's six-decimal display values can hide a narrow winning margin.
They are
conditional candidate scores, **not calibrated probabilities** of future
returns. `candidate_mass` and `argmax_class` expose whether the model's own
next-token distribution actually concentrated on these letters.

## Reproduce

Create the source archive from the exact revision:

```sh
git clone https://github.com/r-ms/mini-jev.git mini-jev
git -C mini-jev archive --format=tar ca612198bfb69f538f029a4615f6d0a18b4f814c \
  minijev pyproject.toml README.md LICENSE > mini-jev-source.tar
sha256sum mini-jev-source.tar
```

Expected archive SHA-256: `bb34dfbbabc3f4cbb48a2eb2be0d50b1fee9c5149a666ff899d56202e85df611`.
Download only the **model** files, directly to the compute host if possible:

```sh
hf download Qwen/Qwen3-4B-Instruct-2507 \
  --revision cdbee75f17c01a7cc42f958dc650907174af0554 \
  --local-dir models/mini-jev-qwen3-4b \
  --include '*.safetensors' '*.json' 'vocab.json' 'merges.txt'
```

The setup script checks every required file before installing dependencies.
The three weight shards have SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `model-00001-of-00003.safetensors` | `75311d91bb08cf0b882913da464a1e722a31fb44db35208663487efb7a3d8ed6` |
| `model-00002-of-00003.safetensors` | `0b48adbb1f60e901153d91907ba11ce63bd4b8b584482e730f48808d055dfba1` |
| `model-00003-of-00003.safetensors` | `7dd39ccca5e4de123c74c14af44c9bf2eb75df33b4614382af0134528e060d5d` |

Install the separate Python 3.12 CPU runtime and score JSONL events:

```sh
MINI_JEV_SOURCE_ARCHIVE="$PWD/mini-jev-source.tar" \
MINI_JEV_MODEL_PATH="$PWD/models/mini-jev-qwen3-4b" \
  bash scripts/setup_mini_jev_server.sh

MINI_JEV_SOURCE_DIR="$PWD/.runtime-mini-jev/source" \
MINI_JEV_MODEL_PATH="$PWD/models/mini-jev-qwen3-4b" \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  .venv-mini-jev/bin/python adapters/mini_jev_decide.py \
  < data/weekly-v1/events.jsonl > decisions-mini-jev.jsonl
```

The adapter emits one decision per `{id,state}` input line. The common
benchmark runner then applies its execution lag, long/cash policy, fees,
and realized returns.

## Verified CPU smoke and queued run

One fully offline event on server1, using `nice -n 19 taskset -c 18,19`,
returned `e000001 -> down`, `prob_up=0.007041`, `candidate_mass=1.0`, and
`argmax_class=bare_candidate`. `benchmark.run.valid_decision` accepted it.
The model call took 172.090 seconds; process wall time was 217.39 seconds
including load, and peak RSS was 19,798,860 KB. At this CPU affinity,
1,382 events would take roughly 66 hours of inference after model load.
That estimate is not a completed backtest.

`scripts/run_mini_jev_after_mino.sh` waits for the 1,382 minojev response IDs
to match the ordered event IDs, then invokes mini-jev with `--resume`, two
CPU threads, low priority, and an offline checkpoint. It writes
`weekly/responses-mini-jev.jsonl`; the log and PID are under
`.runtime-mini-jev/`. The queue does not score returns or publish results.

```sh
nohup nice -n 19 bash scripts/run_mini_jev_after_mino.sh \
  > .runtime-mini-jev/full-run.log 2>&1 < /dev/null &
echo $! > .runtime-mini-jev/full-run.pid
```
