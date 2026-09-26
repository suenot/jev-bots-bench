# SemIf-OpenJev CPU adapter

This adapter runs [SemIf-OpenJev source commit
`23cf1f39fc9534fe81437200959b6dfc7106e45a`](https://github.com/TheoLeeCJ/SemIf-OpenJev/tree/23cf1f39fc9534fe81437200959b6dfc7106e45a)
through its `llamacpp_backend.score()` direct option-logit path. SemIf is a
decision interface, not a trained market forecast model. The frozen base model
is [Qwen3.5-4B commit
`851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`](https://huggingface.co/Qwen/Qwen3.5-4B/tree/851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a).
The quantized checkpoint is [bartowski's Q4_K_M GGUF commit
`4168f45a16a1290d65a4ec0fa312ae917a4c15d6`](https://huggingface.co/bartowski/Qwen_Qwen3.5-4B-GGUF/tree/4168f45a16a1290d65a4ec0fa312ae917a4c15d6),
the file recommended in the pinned SemIf README. Its file size is
3,013,027,808 bytes and its SHA-256 is
`13c16f426047e2de38cd075bdade4a7bcbc8c774384876f677740cda65f8a983`.
The adapter verifies both before loading it.

The input is the benchmark's `{ "id": "...", "state": "..." }` JSONL stream.
For each event, the SemIf question is `next_7_day_price_direction` and its
two options are `Up` and `Down`, in that order. The adapter maps SemIf's two
conditional option scores to `up` and `down`; ties are `down`. These scores
are not calibrated forecasts. The result records SemIf source, base-model and
GGUF revisions, checkpoint checksum, prompt hash, and token count. The model
is loaded once for all lines. Only already closed candles enter `state`; the
adapter reads no future prices or benchmark settlement files.

## Prepare code and weights

Create the small pinned source archive on a machine with GitHub access:

```sh
git clone https://github.com/TheoLeeCJ/SemIf-OpenJev.git semif-source
git -C semif-source archive --format=tar 23cf1f39fc9534fe81437200959b6dfc7106e45a \
  pyproject.toml README.md LICENSE src | gzip -n > semif-runtime.tar.gz
sha256sum semif-runtime.tar.gz
```

Expected archive SHA-256:
`7d4476eb65dbb259010ece167e9ef5c08d0c9f1fdd8a60886ab051a126b97fc1`.
Download `Qwen_Qwen3.5-4B-Q4_K_M.gguf` from the pinned GGUF revision above.
For the reference tokenizer, download `chat_template.jinja`, `config.json`,
`merges.txt`, `tokenizer.json`, `tokenizer_config.json`, and `vocab.json` from
the pinned Qwen base revision into one directory. The exact tokenizer and GGUF
must agree. The adapter verifies SHA-256 for all six reference tokenizer files,
and SemIf checks tokenization before scoring every event.

Transfer only this archive, the tokenizer files, and the GGUF to the compute
host. The historical market files remain there. On Linux Python 3.12:

```sh
SEMIF_SOURCE_ARCHIVE=/absolute/path/to/semif-runtime.tar.gz \
SEMIF_LLAMA_WHEEL=/absolute/path/to/llama_cpp_python-0.3.35-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl \
  bash scripts/setup_semif_server.sh
SEMIF_GGUF_PATH=/absolute/path/to/Qwen_Qwen3.5-4B-Q4_K_M.gguf \
SEMIF_TOKENIZER_PATH=/absolute/path/to/qwen-tokenizer \
SEMIF_THREADS=2 \
  .venv-semif/bin/python adapters/semif_decide.py < events.jsonl > decisions-semif.jsonl
```

The setup installs the [official prebuilt CPU wheel](https://github.com/abetlen/llama-cpp-python#pre-built-wheel-new)
for pinned `llama-cpp-python==0.3.35` and SemIf's GGUF requirements, without
its separate Torch scoring path. Download the wheel from the linked CPU index
and transfer it when GitHub Releases is unavailable on the compute host; its
SHA-256 is `d172f3d3c8cdd194c3c47c71cb077ed6e61354a2d0f939ceeac0c8fd29999596`.
Omit `SEMIF_LLAMA_WHEEL` when the host can fetch the official wheel itself.
`SEMIF_THREADS` defaults to 2; increase it only when the machine
has spare CPU capacity. `SEMIF_MAX_TOKENS` defaults to 2048 and rejects longer
prompts instead of truncating them. The loader hashes the whole GGUF, so the
first event includes checkpoint verification and model-load time. The benchmark
runner measures wall-clock request-to-response time separately from the
adapter's `latency_ms`, which covers the direct scoring call.

## Verified one-event smoke

On the CPU compute host, the pinned source, six tokenizer files, CPU wheel,
and GGUF passed their checksum checks. With `SEMIF_THREADS=1`, `nice -n 10`,
and the first published event (`e000001`), the adapter returned `down` with
`p(up)=0.44880323745740147`, `p(down)=0.5511967625425985`, and prompt SHA-256
`a057d8a66f63d877103b1e40313af2da579404ae0ce40740a8d5e9e3baac1dd1`.
The model used 445 input tokens and took 181.3 seconds for the direct scoring
call while other benchmark jobs were running. This proves the real model path
and JSONL contract work; it is not a completed backtest or a portable speed
measurement.

The same event with `SEMIF_THREADS=4` and `nice -n 10` returned the identical
probabilities and prompt hash. The direct scoring call took 72.5 seconds; the
full cold-start request took 135.74 seconds, including checkpoint hashing and
model loading. The benchmark's `valid_decision()` accepted the response. If
every one of the 1,382 events took 72.5 seconds with one resident process, a
full pass would take about 27.8 hours plus startup. This is only a planning
estimate from one event on a heavily loaded host; event lengths and contention
will change actual throughput. No full SemIf backtest has been run yet.
