# Zefan-Cai/Open-Jev 2B on CPU

The [Open-Jev source](https://github.com/Zefan-Cai/Open-Jev/tree/3308a15ccd7eea1df7a37d6ddc39b023b801ba16)
is pinned to `3308a15ccd7eea1df7a37d6ddc39b023b801ba16` (MIT). The
published [Open-Jev-2B package](https://huggingface.co/ZefanCai/Open-Jev-2B/tree/0c7aa498b1627be8da4acf34c863ff0ee0a92785)
is pinned to `0c7aa498b1627be8da4acf34c863ff0ee0a92785` (Apache-2.0
weights). It contains a LoRA adapter, trained decision head, and calibration
temperature. Its `model.json` requires the separate
[Qwen/Qwen3.5-2B base](https://huggingface.co/Qwen/Qwen3.5-2B/tree/15852e8c16360a2fea060d615a32b45270f8a8fc)
at `15852e8c16360a2fea060d615a32b45270f8a8fc`.

The source documents a CPU service through `python -m jev.server --device cpu`.
The JSONL adapter calls that service's `/v1/systemone` endpoint with the same
binary Choice question used for the other models. It rejects a response whose
method, base revision, or trained checkpoint hash differs from the pinned
artifacts. The checkpoint composite SHA-256 is
`3076462e6356412082e79af909227b39b2863b90def79155ca0821aa506b7ded`.
The 4,548,221,488-byte base safetensors file has SHA-256
`aa33250c4fc64891ddfaba3a314fd9542ea371843c387178b425fbcc5ed680b1`.

## Install on the compute host

Fetch only the pinned source archive, the package files, and the base model
files. The runtime-only source archive (`jev/`, `pyproject.toml`, `README.md`,
`LICENSE`, `THIRD_PARTY_NOTICES.md`) has SHA-256
`881c65c55696634e98a02b3d6e65bde0045d225fed9e5a6bb984819e88e48002`.
The package contents are verified against its published 11-file manifest;
the 13 base files are checked against
[`zefan_open_jev_base_files.json`](zefan_open_jev_base_files.json). Archive
metadata may differ between machines without affecting these file checks.

On a machine with Hub access, fetch the pinned revisions and make the small
archives for transfer. Keep the large base safetensors file separate:

```sh
git clone https://github.com/Zefan-Cai/Open-Jev.git open-jev-source
git -C open-jev-source checkout 3308a15ccd7eea1df7a37d6ddc39b023b801ba16
git -C open-jev-source archive --format=tar HEAD jev pyproject.toml README.md LICENSE THIRD_PARTY_NOTICES.md | gzip -n > zefan-open-jev-runtime.tar.gz
hf download ZefanCai/Open-Jev-2B --revision 0c7aa498b1627be8da4acf34c863ff0ee0a92785 --local-dir zefan-package
tar -czf zefan-open-jev-package.tar.gz -C zefan-package package
hf download Qwen/Qwen3.5-2B --revision 15852e8c16360a2fea060d615a32b45270f8a8fc --local-dir qwen2b
tar -czf zefan-qwen2b-small.tar.gz --exclude=model.safetensors-00001-of-00001.safetensors -C qwen2b .
```

Place the base weight file at
`/mnt/third/jev-bots-bench/models/zefan-open-jev/hub/models--Qwen--Qwen3.5-2B/snapshots/15852e8c16360a2fea060d615a32b45270f8a8fc/model.safetensors-00001-of-00001.safetensors`.
This is the Hugging Face cache snapshot path; `HF_HUB_OFFLINE=1` prevents a
network fetch during inference. The setup script verifies all hashes, checks
the package/base revision pairing, and installs CPU PyTorch plus pinned runtime
dependencies in its own virtual environment.

```sh
ZEFAN_SOURCE_ARCHIVE=/path/zefan-open-jev-runtime.tar.gz \
ZEFAN_PACKAGE_ARCHIVE=/path/zefan-open-jev-package.tar.gz \
ZEFAN_BASE_SMALL_ARCHIVE=/path/zefan-qwen2b-small.tar.gz \
bash scripts/setup_zefan_open_jev_server.sh
```

Then start the local service. The port is bound only when model loading
finishes; `/health` returns `ready` afterward. Keep it on loopback.

```sh
root=/mnt/third/jev-bots-bench
HF_HUB_CACHE="$root/models/zefan-open-jev/hub" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 TOKENIZERS_PARALLELISM=false \
nice -n 15 "$root/.venv-zefan-open-jev/bin/python" -m jev.server \
  --checkpoint "$root/models/zefan-open-jev/Open-Jev-2B/package/checkpoint" \
  --device cpu --max-length 4096 --batch-size 1 --no-prefix-cache \
  --host 127.0.0.1 --port 18086
```

In a second shell, first make one real request, then let the benchmark runner
record wall-clock latency for the full causal event stream:

```sh
head -n 1 /mnt/third/jev-bots-bench/weekly/events.jsonl | \
  ZEFAN_OPEN_JEV_SERVER_URL=http://127.0.0.1:18086 \
  python3 adapters/zefan_open_jev_decide.py

ZEFAN_OPEN_JEV_SERVER_URL=http://127.0.0.1:18086 python3 benchmark/run.py invoke \
  --events /mnt/third/jev-bots-bench/weekly/events.jsonl \
  --output /mnt/third/jev-bots-bench/weekly/zefan_open_jev.responses.jsonl \
  -- python3 adapters/zefan_open_jev_decide.py
```

Open-Jev scores each candidate separately; the two-label question requires
two forward passes. On server1, one real `e000001` request with `nice -n 15`
and two OpenMP threads took **316.668 seconds**: `down`, P(up) =
`0.315500372780907`. The same event with four threads took **361.692
seconds**: `down`, P(up) = `0.3150875693790762`. Both responses reported the
pinned model, base revision, `lora_decision_head` method, and checkpoint hash.
The small probability difference is a CPU thread-count numerical difference;
these measurements were made while other benchmark jobs shared the host.
The test service was stopped after the second request; no full run was started.

At these observed rates, 1,382 serial events would take roughly 122-139
hours, before setup or variation in host load. Nine sequential pair requests
would take about 47.5-54.3 minutes, which leaves little margin within the
benchmark's one-hour simultaneous-request deadline. A full run should use a
fixed thread count and recheck that deadline under its actual host load. Its
2026 training history also leaves possible pretraining overlap with the
historical market window; any result is retrospective unless that overlap is
ruled out.
