# GLiFormer large-v1 CPU setup

The adapter runs the released GLiFormer classification head. The
[source](https://github.com/Knowledgator/GLiFormer/tree/b5c0a0fd2aacff64736fbfa0bac0bdcc032d5eff)
is pinned to `b5c0a0fd2aacff64736fbfa0bac0bdcc032d5eff`; the
[checkpoint](https://huggingface.co/knowledgator/gliformer-large-v1/tree/d0a4e53d09cebe6bc963dd9be319d4279084bb2d)
is pinned to `d0a4e53d09cebe6bc963dd9be319d4279084bb2d`.
The checkpoint's `pytorch_model.bin` is 2,302,735,855 bytes with SHA-256
`f80b29199d66f878669f283703e4dba9fd726755dcc20aba1ed0d24fce4a23f1`.
The adapter uses the checkpoint's CPU Python classifier and normalizes its
two independent sigmoid scores to a binary distribution. Those normalized
scores are **not calibrated probabilities of future market returns**.

## Reproduce

Create the source archive from the pinned commit:

```sh
git clone https://github.com/Knowledgator/GLiFormer.git GLiFormer
git -C GLiFormer archive --format=tar b5c0a0fd2aacff64736fbfa0bac0bdcc032d5eff gliformer pyproject.toml README.md LICENSE > gliformer-runtime.tar
sha256sum gliformer-runtime.tar
```

Expected archive SHA-256:
`ba0e024ed2d45b75c6fa8943c1af8edc1c0121ce716d41f972cad27796f9f0ee`.
Download these files from the pinned checkpoint revision into one directory:
`pytorch_model.bin`, `gliner_config.json`, `tokenizer.json`, and
`tokenizer_config.json`. Their SHA-256 values are checked by the setup script.
The compute host needs Python 3.12 and access to PyPI and the official CPU
PyTorch wheel index. It can receive source and model artifacts without any
market-history transfer.
The checked-in `requirements-gliformer-cpu-lock.txt` records the exact
Linux x86_64 package versions used for the smoke; setup installs the CPU
PyTorch wheel first, then this dependency set and the pinned source archive.

```sh
GLIFORMER_SOURCE_ARCHIVE=/path/to/gliformer-runtime.tar \
GLIFORMER_MODEL_PATH=/path/to/gliformer-large-v1 \
  bash scripts/setup_gliformer_server.sh

GLIFORMER_MODEL_PATH=/path/to/gliformer-large-v1 \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  .venv-gliformer/bin/python adapters/gliformer_decide.py \
  < data/weekly-v1/events.jsonl > decisions-gliformer.jsonl
```

The adapter emits one decision for each `{id,state}` JSONL request. It uses
the same `next_7_day_price_direction` task as the other models and loads the
checkpoint once per stream. The benchmark supplies only closed historical
observations to `state` and measures future P&L separately.

One-event Linux x64 CPU smoke with two assigned cores and `HF_HUB_OFFLINE=1`
returned `down` for `e000001`, with normalized `p(up)=0.11593522761326566`.
Inference took 16.193 seconds after model load; resident memory was about
3.8 GB during the smoke. The optional `flashdeberta` kernel was absent, so
the source used its documented eager-attention fallback. The output passed
the benchmark runner's `valid_decision` check. This verifies the adapter
protocol and CPU feasibility; it is not a trading result.
