# AnyJev L0 with a fixed Qwen base

The pinned [AnyJev source](https://github.com/nokia-applied-research/AnyJev/tree/795a4970b47218b7c0686cd579d691fc2cf8df2f)
provides a zero-label `L0` choice path: read one-token answer logits under each
cyclic permutation of the options and marginalize them. Its `L1` temperature
calibrator and `L2` decision head require labeled examples. This benchmark uses
only `L0`, with `prior="none"` so no running estimate or future event can affect
a decision. The two option permutations are always scored. These probabilities
are choice scores; they have **not** been calibrated to market outcomes.

The base is the same
[Qwen3.5-0.8B revision](https://huggingface.co/Qwen/Qwen3.5-0.8B/tree/2fc06364715b967f1860aea9cf38778875588b17)
used by the Simple Jev adapter: `2fc06364715b967f1860aea9cf38778875588b17`,
float32 on CPU. This fixes the base model while testing the AnyJev readout.
The weight file `model.safetensors-00001-of-00001.safetensors` is 1,746,942,600
bytes and has SHA-256
`04b1c301231dd422b8860db31311ab2721511346a32cb1e079c4c4e5f1fe4696`.
The adapter verifies that hash and the SHA-256 of all eight local model config,
index, preprocessing, and tokenizer files before loading the checkpoint offline.
The exact file hashes are in `anyjev_decide.py`. There is
no trading-trained AnyJev checkpoint in this configuration.

## Reproduce

Prepare a source archive from the exact commit on a host with GitHub access:

```sh
git clone https://github.com/nokia-applied-research/AnyJev.git anyjev-source
git -C anyjev-source archive --format=tar 795a4970b47218b7c0686cd579d691fc2cf8df2f anyjev pyproject.toml README.md LICENSE | gzip -n > anyjev-runtime.tar.gz
sha256sum anyjev-runtime.tar.gz
```

Its SHA-256 must be
`4796ba3b9a50757dd82487797fc443ffd1560daa3939032a07d78215fa5951ba`.
With that archive and the pinned Qwen checkpoint already on the compute host,
run:

```sh
ANYJEV_SOURCE_ARCHIVE=/absolute/path/to/anyjev-runtime.tar.gz bash scripts/setup_anyjev_server.sh
ANYJEV_MODEL_PATH=/absolute/path/to/Qwen3.5-0.8B ANYJEV_THREADS=2 \
  nice -n 10 .venv-anyjev/bin/python adapters/anyjev_decide.py \
  < events.jsonl > decisions-anyjev.jsonl
```

Each input line contains only `{"id":"...","state":"..."}`. The `state`
must describe information known at the decision time. The adapter never reads
the realized return, benchmark labels, later events, or fitted artifacts.
The fixed question is `next_7_day_price_direction`, with `Up` and `Down` as
options; ties become `down` by benchmark convention. The output includes
`source_revision`, `model_revision`, `decision_level`, `permutations`, and
`training_labels_used` for audit.

## One-event protocol smoke

On server1, the first existing weekly event (`e000001`) returned `down` with
`P(up)=0.343074077167144` and `P(down)=0.656925922832856`. The response
reported `L0`, two permutations, no prior, and zero training labels.
`benchmark.run.valid_decision()` accepted it. With `ANYJEV_THREADS=2` and
`nice -n 10`, scoring took 35.765 seconds; the complete cold request took
72.25 seconds and peaked at about 5.0 GB resident memory. A naive linear
projection over the current 1,382-event set is about 13.7 hours of scoring,
but throughput can vary substantially under shared server load. This is a
protocol smoke, not a trading result; no full backtest was launched here.

Suggested manifest status: `ready_zero_shot_l0` — "Pinned AnyJev L0 with
Qwen3.5-0.8B CPU, two option permutations and no task labels; market
probabilities are uncalibrated. L1/L2 need a separate past-only training split
and fitted artifacts." This replaces the blanket blocker that a base model
has not been selected. A calibrated or market-fitted variant would require
historical labels from a disjoint pretest period, its own saved calibration
artifact/checkpoint, and a new leakage audit.
