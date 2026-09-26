# NanoJev trained checkpoint on CPU

This adapter uses [NanoJev source commit
`76fdfc9ecdca45a9bcef17991a07d3041a87685a`](https://github.com/TianyuCodings/NanoJev/tree/76fdfc9ecdca45a9bcef17991a07d3041a87685a)
and the released [`unified-games-v1` checkpoint](https://huggingface.co/C-Tianyu/NanoJev/tree/047b927b30882a1138fc504821b82ac145a4b81a)
at immutable model revision `047b927b30882a1138fc504821b82ac145a4b81a`.
The selected `best.safetensors` is 2,385,039,280 bytes with SHA-256
`f68c47d66998231b86b7e91b4ed5e82ae23acf104c8b7cd6d165c3ac7b7ffe1b`.
The checkpoint combines a [Qwen3-0.6B base model](https://huggingface.co/Qwen/Qwen3-0.6B/tree/c1899de289a04d12100db370d81485cdf75e47ca)
with NanoJev's trained attention decision head. Its training mixed Maze,
Snake, and two ViZDoom tasks; it was not trained on market direction.

## Compatibility boundary

The pinned inference schema [accepts a nonempty text `state` and a two-option
`choice` question](https://github.com/TianyuCodings/NanoJev/blob/76fdfc9ecdca45a9bcef17991a07d3041a87685a/scripts/predict_toy_decisions.py).
It constructs candidate paths using `State:`, `Question type: choice`, and
`Candidate:` segments. The benchmark's text state can therefore enter without
inventing another representation or retraining. The adapter supplies the
same `next_7_day_price_direction` question and `Up`/`Down` options as the
other decision engines. The model receives only `{id,state}` from the causal
event stream. No settlement, future return, market label, or training target
is read by this adapter. The base model's pretraining corpus cannot be audited
from this checkpoint, so input causality alone does not prove that every
historical market fact was absent from pretraining.

NanoJev's published `DecisionPredictor` [explicitly refuses non-CUDA
devices](https://github.com/TianyuCodings/NanoJev/blob/76fdfc9ecdca45a9bcef17991a07d3041a87685a/scripts/predict_toy_decisions.py).
The underlying `DecisionModel.forward()` takes its device from the model's
weights, and the checkpoint loader reads `best.safetensors` on CPU. This
adapter reproduces that loader and the public `prepare_examples()` and
`answer_from_probabilities()` functions on CPU in float32. It loads all
weights with `strict=True` and keeps the model resident for subsequent JSONL
lines. This CPU path is our adaptation, not an upstream-supported runtime.
It uses `torch==2.8.0+cpu` for the server's Python 3.12 environment; the
upstream CUDA training environment records `torch==2.14.0` on Python 3.14.
Different precision/runtime can change borderline decisions. The returned
choice softmax is uncalibrated for crypto markets.

## Reproduce

Create the pinned source archive on a machine with GitHub access:

```sh
git clone https://github.com/TianyuCodings/NanoJev.git nanojev-source
git -C nanojev-source archive --format=tar 76fdfc9ecdca45a9bcef17991a07d3041a87685a \
  scripts/predict_toy_decisions.py scripts/train_toy_decisions.py | gzip -n > nanojev-runtime.tar.gz
sha256sum nanojev-runtime.tar.gz
```

Expected archive SHA-256:
`3370f5dec53956138a42342b4d1bd180ea697796317570294de58d3395bb018f`.
Download only `best.safetensors`, `config.json`, `backbone_config/config.json`,
and the three files under `tokenizer/` from the pinned model revision above.
The adapter checks SHA-256 for all six checkpoint files and both pinned source
scripts before loading. No game dataset
or market history download is needed. Transfer the source archive and model
files to the compute host, then run:

```sh
NANOJEV_SOURCE_ARCHIVE=/absolute/path/to/nanojev-runtime.tar.gz \
  bash scripts/setup_nanojev_server.sh
NANOJEV_CHECKPOINT_DIR=/absolute/path/to/nanojev-unified \
NANOJEV_SOURCE_DIR=/mnt/third/jev-bots-bench/nanojev-source \
NANOJEV_THREADS=2 \
  .venv-nanojev/bin/python adapters/nanojev_decide.py < events.jsonl > decisions-nanojev.jsonl
```

`NANOJEV_MAX_TOKENS` defaults to 2048. Longer candidate paths fail rather
than being truncated. The adapter emits the same binary long/cash contract as
the other models, with checkpoint and base-model revisions in each row.

## Verified one-event smoke

The pinned checkpoint and all five metadata/tokenizer files matched their
published SHA-256 values. On the CPU compute host, the first published event
`e000001` produced `up` with `p(up)=0.6739526987075806` and
`p(down)=0.3260473310947418`. The candidate paths were 380 tokens each.
`benchmark.run.valid_decision()` accepted the response. With
`NANOJEV_THREADS=2` and `nice -n 10` under concurrent load, the model call
took 39.0 seconds; the full cold-start process took 101.89 seconds, including
checkpoint hashing and load. Repeating that one call's duration across 1,382
events suggests roughly 15 hours for a resident-process pass, but varied
event lengths and server contention make this only a planning estimate.

Recommended benchmark status: **compatible; full run pending**. The smoke
proves that the released trained head can read the causal market input on CPU.
It does not establish trading skill, and no full NanoJev backtest has run yet.
