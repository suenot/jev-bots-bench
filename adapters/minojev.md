# minojev general checkpoint on CPU

The adapter uses the trained **general** minojev decision head with its
Qwen3-1.7B backbone. The [source](https://github.com/zeredy879/minojev/tree/622dd952c3db2769a7a32d1a13cc89db04bba95e)
is pinned to `622dd952c3db2769a7a32d1a13cc89db04bba95e`; the
[public checkpoint](https://huggingface.co/zeredy879/minojev/tree/e1e4bbec238c36af6db1af3b1890634440228cb7/general)
is pinned to `e1e4bbec238c36af6db1af3b1890634440228cb7`.
The 3,441,185,608-byte backbone `model.safetensors` has SHA-256
`169ad53ec313c3a34b06c0809216e4fc072cce444a5d4ff2b59690d064130ed5`;
the 3,178,488-byte `head.safetensors` has SHA-256
`35209573555f0442254c257e8ff57f04652ecb24c2db8d05b3240c9e16777bb2`.
The setup script verifies these files, both model configs, the tokenizer, and
the source archive before installing anything.

This is a valid zero-shot *market-domain* use of a trained general decision
head: one fixed binary choice about the next seven-day return, with no model
training on the benchmark outcomes. The checkpoint's choice temperature
`0.2706` was calibrated on its published nonmarket tasks, so its outputs
should not be interpreted as calibrated probabilities of crypto returns.
Minojev's HF backbone does not support its `reuse` mode; this adapter uses
the published `fresh` scoring path.
The published tokenizer has a list-valued `extra_special_tokens` field;
Transformers 4.56.2 expects a mapping. The adapter supplies the same named
tokens as an in-memory mapping while loading, without editing the checkpoint.

## Reproduce setup

Create the pinned source archive:

```sh
git clone https://github.com/zeredy879/minojev.git minojev
git -C minojev archive --format=tar 622dd952c3db2769a7a32d1a13cc89db04bba95e src pyproject.toml README.md LICENSE > minojev-runtime.tar
sha256sum minojev-runtime.tar
```

Expected source archive SHA-256:
`9df15ceda2c36de782f82d8c79cc6fb43b43e839e55c3cdca4908f5f95d3e028`.
Copy the `general/` directory from the pinned checkpoint revision, retaining
its `backbone/` subdirectory. Required files are `config.json`,
`head.safetensors`, and, under `backbone/`, `model.safetensors`, `config.json`,
`tokenizer.json`, `tokenizer_config.json`, and `minojev_tokenizer.json`.
The source installation uses Python 3.12, the official CPU PyTorch wheel,
and the checked-in Linux x86_64 dependency lock file (including `protobuf`,
needed by this tokenizer). Only source and
checkpoint artifacts need to reach the compute host; historical candles
remain in place.

```sh
MINOJEV_SOURCE_ARCHIVE=/path/to/minojev-runtime.tar \
MINOJEV_MODEL_PATH=/path/to/checkpoint/general \
  bash scripts/setup_minojev_server.sh

MINOJEV_MODEL_PATH=/path/to/checkpoint/general \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  .venv-minojev/bin/python adapters/minojev_decide.py \
  < data/weekly-v1/events.jsonl > decisions-minojev.jsonl
```

The adapter emits one decision for each `{id,state}` JSONL line. It loads
the model once, requests the native complete choice distribution, then
renormalizes the eight-decimal output to exactly sum to one. The benchmark
runner separately applies its common execution lag, long/cash policy, fees,
and realized future returns.

## Verified CPU smoke

On server1, one event from `weekly/events.jsonl` ran fully offline with
`nice -n 19 taskset -c 18,19` and two PyTorch/BLAS threads. It returned
`e000001 -> up`, `prob_up=0.6997820280130783`; the benchmark's
`valid_decision` accepted the response. The model call took 120.625 seconds,
and the process took 159.23 seconds including load, with a peak RSS of
10,389,344 KB. A 1,382-event run at this CPU affinity would take roughly
46 hours of inference, so this model is technically runnable but expensive.
That extrapolation is only a planning estimate; a complete backtest has not
been run here.
