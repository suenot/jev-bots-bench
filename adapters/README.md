# CPU classification adapters

Each adapter accepts one
UTF-8 JSON object per line on stdin:

```json
{"id":"opaque-event-id","state":"Causal weekly market features, without dates or absolute prices."}
```

Each emits the same `id`, `prediction` (`up` or `down`), `latency_ms` for model
inference, `source`, `model`, `model_revision`, and a binary long/cash
`target_weight`. Adapters with a usable two-class distribution also emit
`probabilities` (`up` and `down`) and `prob_up`; GLiNER's documented interface
returns only the selected class, so its Brier score is absent. A tie maps to
`down`, matching the benchmark's strict positive-return definition of `up`.
The model loads once and handles subsequent lines in the same process.
Diagnostics go to stderr. The benchmark runner replaces adapter-reported
latency with wall-clock request-to-response time, including cold start on the
first request.

## GLiNER2.5-Decide

The source library is pinned to
[`55656fbfa01d3d4a77485e1a1eeeaf682990ccdf`](https://github.com/fastino-ai/GLiNER2/tree/55656fbfa01d3d4a77485e1a1eeeaf682990ccdf),
and the public Apache-2.0 checkpoint is pinned to
[`7ee5da4c2415e32259bcdc0b1a7367c32ce8d6f6`](https://huggingface.co/fastino/GLiNER2.5-Decide/tree/7ee5da4c2415e32259bcdc0b1a7367c32ce8d6f6).
The released checkpoint uses the `AutoExtractor` architecture and its
`classify_text()` interface reports the selected class. The adapter does not
invent a probability distribution for it.

### Install and run on Linux CPU

Use Python 3.12 (the server1 environment) and a virtual environment. Install the CPU PyTorch wheel from
the official index, then the pinned direct dependencies. The first adapter run
downloads the pinned model to the Hugging Face cache; allow space for its
checkpoint and keep that cache for repeated runs.

```sh
python3 -m venv .venv-gliner
.venv-gliner/bin/python -m pip install --upgrade pip
.venv-gliner/bin/python -m pip install 'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
.venv-gliner/bin/python -m pip install -r adapters/requirements-gliner-decide.txt
.venv-gliner/bin/python adapters/gliner_decide.py < events.jsonl > decisions.jsonl
```

On the tested server, PyPI and the PyTorch wheel index work, while direct
GitHub and Hugging Face model downloads do not. Download the source archive at
the [pinned source commit](https://github.com/fastino-ai/GLiNER2/archive/55656fbfa01d3d4a77485e1a1eeeaf682990ccdf.tar.gz)
elsewhere, transfer it to the server, and run
`GLINER_SOURCE_ARCHIVE=/absolute/path/to/GLiNER2.tar.gz bash scripts/setup_gliner_server.sh`.
The archive SHA-256 is
`060577b496e84cd818fbbb60bcb39541032ea6e49ec638393c2101050fba5b49`.
Likewise transfer the files for the pinned checkpoint revision to a server
directory and set `GLINER_MODEL_PATH=/absolute/path/to/checkpoint`. It must
contain `model.safetensors`, both config files, and the tokenizer files. The
checkpoint's `model.safetensors` SHA-256 is
`40a5a23ff860dc3dff426cecd1048cacdd29c648c96db209dad818e9686dc997`.
With `GLINER_MODEL_PATH` set, the setup script verifies every transferred
checkpoint file against [`gliner25_checkpoint.sha256`](gliner25_checkpoint.sha256)
before installing packages. Keep the pinned local directory for inference.
Only source code and model weights are transferred; historical candles stay
beside the warehouse replay.

The state text must describe only information available at the decision time.
Do not include realized future returns. This model is a general classifier,
not a model trained to forecast crypto prices; its scores are benchmark inputs,
not evidence of predictive skill until the held-out replay is measured.

## Laya

The [source library](https://github.com/NandhaKishorM/laya/tree/4066d5d5fbf08b66c6757ddeedbd797bd7655bc0)
and [English checkpoint](https://huggingface.co/convaiinnovations/laya/tree/55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851)
are pinned. Both are Apache-2.0. The direct Python SDK loads one model on CPU
and returns the full `choice` distribution. The adapters use the same
`next_7_day_price_direction` task and `up`/`down` labels. Laya rounds its
reported probabilities to four decimals; the adapter renormalizes them to
sum to one. Its published confidence metrics are not crypto forecasting
calibration.

```sh
LAYA_SOURCE_ARCHIVE=/absolute/path/to/laya-source.tar.gz bash scripts/setup_laya_server.sh
python3 adapters/smoke_laya_mock.py
LAYA_MODEL_PATH=/absolute/path/to/laya-checkpoint \
  .venv-laya/bin/python adapters/laya_decide.py < events.jsonl > decisions-laya.jsonl
```

The server cannot fetch GitHub or Hugging Face directly. Obtain the source
archive for the pinned commit and the five checkpoint files
(`model.safetensors`, `rl_agent_config.json`, `encoder/config.json`, and both
`tokenizer/` JSON files), then transfer only those artifacts. The setup script
verifies source archive SHA-256
`4203c0832f92a5981a9422107e30b7a6ae157c787fa6e3a9c97b75bcbf2deaf7`.
Set `LAYA_MODEL_PATH` during setup as well to verify the checkpoint's
`model.safetensors` SHA-256
`891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c`.
The setup script checks all five transferred files against
[`laya_checkpoint.sha256`](laya_checkpoint.sha256).
The local path selects the exact transferred files; the adapter reports the
pinned upstream model revision in every response.

## GLiFormer large-v1

The [source library](https://github.com/Knowledgator/GLiFormer/tree/b5c0a0fd2aacff64736fbfa0bac0bdcc032d5eff)
and [checkpoint](https://huggingface.co/knowledgator/gliformer-large-v1/tree/d0a4e53d09cebe6bc963dd9be319d4279084bb2d)
are pinned and Apache-2.0. The adapter runs the documented Python classifier
on CPU. GLiFormer's classifier independently applies sigmoid to each class
logit. Its scores can both be high or both be low. The adapter requests both
scores and divides each by their sum to match the benchmark's binary JSONL
contract. `probability_semantics` records this transformation. These values
are **not a calibrated exclusive-class distribution**, so interpret Brier
scores and reliability plots separately from the native Laya and GLiNER
outputs.

```sh
python3.11 -m venv .venv-gliformer
.venv-gliformer/bin/python -m pip install --upgrade pip
.venv-gliformer/bin/python -m pip install 'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
.venv-gliformer/bin/python -m pip install -r adapters/requirements-gliformer-decide.txt
python3 adapters/smoke_gliformer_mock.py
.venv-gliformer/bin/python adapters/gliformer_decide.py < events.jsonl > decisions-gliformer.jsonl
```

For the checksum-verified offline CPU checkpoint and fixed dependency set used
in this campaign, follow [`gliformer.md`](gliformer.md) and
`scripts/setup_gliformer_server.sh`.

## Simple Jev with Qwen3.5-0.8B

The [Simple Jev source](https://github.com/featherless-ai/simple-jev/tree/c077d5dfdb5c2c7dd24b17d5f556f07e0162dc1c)
is pinned to `c077d5dfdb5c2c7dd24b17d5f556f07e0162dc1c`. Its documented
CPU Transformers path uses a base model rather than a trained trading head.
This adapter fixes [Qwen3.5-0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B/tree/2fc06364715b967f1860aea9cf38778875588b17)
at revision `2fc06364715b967f1860aea9cf38778875588b17`, float32 on CPU,
Simple Jev's `baseline` prompt policy, and one binary Choice question. It
loads the model once for the JSONL stream, with no HTTP service required.

On a machine with GitHub access, prepare the 72 KB runtime-only archive:

```sh
git clone https://github.com/featherless-ai/simple-jev.git simple-jev-source
git -C simple-jev-source archive --format=tar c077d5dfdb5c2c7dd24b17d5f556f07e0162dc1c common hf-server | gzip -n > simple-jev-runtime.tar.gz
sha256sum simple-jev-runtime.tar.gz
```

Its expected SHA-256 is
`b54815a83d2e1143abcb8faf0a29696f7f59bd3845db15445fba2b77bf735cb5`.
Download the pinned model repository files to a local directory, then transfer
that directory and this archive to the compute host. The setup script checks
the archive hash and installs a CPU PyTorch wheel plus the pinned source:

```sh
SIMPLE_JEV_SOURCE_ARCHIVE=/absolute/path/to/simple-jev-runtime.tar.gz bash scripts/setup_simple_jev_server.sh
SIMPLE_JEV_MODEL_PATH=/absolute/path/to/Qwen3.5-0.8B .venv-simple-jev/bin/python adapters/simple_jev_decide.py < events.jsonl > decisions-simple-jev.jsonl
```

`SIMPLE_JEV_MODEL_PATH` avoids Hugging Face network access at inference time.
The pinned `model.safetensors-00001-of-00001.safetensors` is 1,746,942,600
bytes with SHA-256
`04b1c301231dd422b8860db31311ab2721511346a32cb1e079c4c4e5f1fe4696`.
The one-event CPU smoke returned a valid binary distribution in 19.4 seconds
of inference (excluding model load); a full run may take hours.
Only the model files and source archive cross the network; the raw market
history remains at the compute host. These probabilities come from a general
language model's answer-token logits and are not calibrated to future crypto
returns. The source and base model are separate revision pins.

## Other CPU decision engines

- [`kev.md`](kev.md): the released Kev-0.8B trained LoRA and pointer head with
  its separate Qwen3.5-0.8B-Base on CPU.
- [`jevk5.md`](jevk5.md): pinned JevK5 4B Q4_K_M GGUF through its own
  `JevK5GGUF` interface and a pinned llama.cpp HTTP server.
- [`semif.md`](semif.md): SemIf direct option scoring with a pinned
  Qwen3.5-4B GGUF and reference tokenizer.
- [`nico_open_jev.md`](nico_open_jev.md): the released open-jev DeBERTa ONNX
  decision head on Node.js CPU with q4 weights.
- [`nanojev.md`](nanojev.md): the released game-trained NanoJev decision head,
  loaded and scored on CPU without changing its weights.
- [`minojev.md`](minojev.md): the released minojev general decision head and
  Qwen3-1.7B backbone on CPU.
- [`anyjev.md`](anyjev.md): AnyJev's zero-label L0 path with a fixed
  Qwen3.5-0.8B base and no market-fitted artifacts.
- [`mini_jev.md`](mini_jev.md): mini-jev's frozen Qwen3-4B letter scorer on
  CPU float32, without a separately trained decision head.
- [`zefan_open_jev.md`](zefan_open_jev.md): the released Open-Jev-2B trained
  head with its fixed Qwen3.5-2B base through a local CPU service.

Each guide records source and weight revisions separately, checkpoint hashes,
setup commands, a real one-event protocol smoke, and the limits of that smoke.
Full trading P&L appears only after a complete response file passes evaluation.
