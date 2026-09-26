# Kev-0.8B trained decision head on CPU

This adapter uses pinned [Kev source commit
`f1535963cea021439370c23127bc970b6788e730`](https://github.com/jaredpalmer/kev/tree/f1535963cea021439370c23127bc970b6788e730)
and the released, ungated Apache-2.0
[`jaredpalmer/kev-0.8b` checkpoint](https://huggingface.co/jaredpalmer/kev-0.8b/tree/9a45d25eb2ab761841196625383fa1dff0e56c1e)
at immutable revision `9a45d25eb2ab761841196625383fa1dff0e56c1e`.
Its LoRA adapter and fitted pointer head are applied to
[`Qwen/Qwen3.5-0.8B-Base`](https://huggingface.co/Qwen/Qwen3.5-0.8B-Base/tree/dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68),
revision `dc7cdfe2ee4154fa7e30f5b51ca41bfa40174e68`, also Apache-2.0.
This **Base** checkpoint is different from the Qwen3.5-0.8B checkpoint used
by the Simple Jev and AnyJev adapters. Its weights cannot be substituted.

Kev's [`Checkpoint.load()`](https://github.com/jaredpalmer/kev/blob/f1535963cea021439370c23127bc970b6788e730/kev/checkpoint.py)
supports a CPU PyTorch path and loads the trained LoRA weights, pointer head,
and the checkpoint's fitted temperature. The adapter loads a local verified
mirror of each pinned model to avoid inference-time network access. The only
request data are `{ "id": "...", "state": "..." }`; the fixed choice question
is `next_7_day_price_direction`, with `up: Up` and `down: Down`. Kev's public
API converter inserts a dummy label index into its internal record, but the
inference encoder and scorer do not use that field. No benchmark outcome,
future event, or trading label is read or fitted. The checkpoint was trained
on other decision tasks; its temperature has **not** been fitted to market
returns. As with every retrospective model test, the base's pretraining
corpus cannot prove that all market history was absent from the weights.
The adapter asserts that the converter returns `up`, then `down`; the pinned
encoder iterates options in that order, and the scorer reads option indices
without sorting. Its first probability therefore belongs to `up`.

The adapter verifies these SHA-256 values before loading:

| Pinned artifact | File | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| Kev-0.8B | `adapter_model.safetensors` | 43,338,624 | `9b908623acb162118575f4e7a94524f9c139c335be4bfb74d6cfceca01e1885a` |
| Kev-0.8B | `head.pt` | 2,103,999 | `f400bd12802b2b105ae45d6b03774a158a3db4fccff42413734ddca2e5c920b6` |
| Qwen3.5-0.8B-Base | `model.safetensors-00001-of-00001.safetensors` | 1,746,942,600 | `c2b1e5a17d9c1e27685d92ed9b382911ebb99955ecd89052d1721241adfbab6c` |

The small config, tokenizer, and index files are also SHA-checked in
[`kev_decide.py`](kev_decide.py). The upstream [Kev license](https://github.com/jaredpalmer/kev/blob/f1535963cea021439370c23127bc970b6788e730/LICENSE)
is Apache-2.0; the checkpoint and base model cards declare the same license.

## Reproduce

On a host with GitHub access, prepare a source archive from the exact commit:

```sh
git clone https://github.com/jaredpalmer/kev.git kev-source
git -C kev-source archive --format=tar f1535963cea021439370c23127bc970b6788e730 \
  kev pyproject.toml README.md LICENSE | gzip -n > kev-runtime.tar.gz
sha256sum kev-runtime.tar.gz
```

The archive SHA-256 is
`f91272dd2ceb3d595de788aa1d24defc2b08e60588856dd83947536833a9c181`.
Download only `head.pt`, `adapter_config.json`, and
`adapter_model.safetensors` from the pinned Kev revision into one directory.
Download `config.json`, `merges.txt`,
`model.safetensors-00001-of-00001.safetensors`,
`model.safetensors.index.json`, `tokenizer.json`,
`tokenizer_config.json`, and `vocab.json` from the pinned Qwen-Base revision
into another. Transfer these model artifacts and the source archive to the
compute host. No historical market data transfer is required.

```sh
KEV_SOURCE_ARCHIVE=/absolute/path/to/kev-runtime.tar.gz \
  bash scripts/setup_kev_server.sh
KEV_CHECKPOINT_DIR=/absolute/path/to/kev-0.8b \
KEV_BASE_DIR=/absolute/path/to/Qwen3.5-0.8B-Base \
KEV_THREADS=2 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1 \
  nice -n 19 .venv-kev/bin/python adapters/kev_decide.py \
  < events.jsonl > decisions-kev.jsonl
```

The setup installs an official CPU PyTorch wheel, pinned runtime dependencies,
and the checksum-verified Kev source. `requirements-installed.txt` in the
isolated environment records the resolved transitive dependencies. Inference
uses CPU float32 and the checkpoint's supplied temperature. The adapter
rejects silent input truncation, hash mismatches, and invalid probabilities.
The benchmark runner replaces the adapter's scoring-only `latency_ms` with
full request-to-response time, including tokenization and JSON transport.

## Server1 smoke, 2026-09-26

The first causal event, `e000001`, was run once with `nice -n 19`,
`KEV_THREADS=2`, `OMP_NUM_THREADS=2`, and `MKL_NUM_THREADS=2`. The server-side
SHA-256 checks matched the published base, LoRA, and head files. Kev returned
`down` with `P(up)=0.3326515257358551` and `P(down)=0.6673485040664673`,
using 374 input tokens and the checkpoint temperature
`2.3510958125672174`. `benchmark.run.valid_decision()` accepted the row.
The full cold process took 77.83 seconds; model scoring took 17.310 seconds.
Peak resident memory was 5,025,032 KiB (4.79 GiB). All 1,382 weekly states
have 576 characters. Nine requests at the measured warm rate would take
about 156 seconds, plus about 61 seconds for initial loading, below the
one-hour nine-pair deadline. This is a one-event feasibility measurement,
not a completed Kev backtest or proof of every event's runtime.

For the complete weekly stream, `scripts/queue_kev_server.sh` waits for the
seven short-run response streams and the already queued CPU model runs. It
checks the exact 1,382 event IDs, the source event SHA-256
`d17d4fb3bfcacd898e0a81a07ed704d598f931fc4db9ff683ba649646fdbbecc`,
and the pinned model files before invoking `benchmark/run.py --resume` at
`nice 19` with two inference threads. Its output is
`weekly/responses-kev.jsonl`, with progress in `weekly/kev-queue.log` and
`weekly/kev-invoke.log`. Start it on the compute host with:

```sh
nohup nice -n 19 bash scripts/queue_kev_server.sh \
  > weekly/kev-queue.log 2>&1 < /dev/null &
```
