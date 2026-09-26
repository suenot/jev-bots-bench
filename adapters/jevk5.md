# JevK5 4B v0.3 GGUF on CPU

The [JevK5 source](https://github.com/allebee/jevk5/tree/1e5ae1b533b9eb80c0cbe3fbd010607d0b4e26ae)
is pinned to `1e5ae1b533b9eb80c0cbe3fbd010607d0b4e26ae` (Apache-2.0).
Its documented `JevK5GGUF` class reads answer-letter log probabilities from
`llama-server` with no generated answer tokens. This adapter uses the 4B v0.3
Q4_K_M file from [JevK5-GGUF](https://huggingface.co/alibiserikbay/JevK5-GGUF/tree/ec67b0bfce5119a8b11a2cdb430bb43e3fa3e82a),
revision `ec67b0bfce5119a8b11a2cdb430bb43e3fa3e82a`, 2,708,804,000 bytes,
SHA-256 `94ca0d7745c47f79091b0892ca657c81d9dc9e4ed0238ba0a7ea261d8938c882`.
JevK5's source documentation says this quantized file agreed with its bf16
answer on 221 of 231 public JevBench items. It is a **different artifact**
from the full precision `alibiserikbay/JevK5` checkpoint currently listed in
`benchmark/models.json`; update the benchmark provenance to the GGUF revision
before publishing any measured JevK5 result. Quantization can change answers.

The source names [llama.cpp commit `9575389609d6f8437de0b205561a4824d217c409`](https://github.com/ggml-org/llama.cpp/tree/9575389609d6f8437de0b205561a4824d217c409)
as a tested runtime for Qwen3.5 GGUF. The setup script verifies the exact
source, runtime, and checkpoint hashes, installs only JevK5's standard-library
GGUF path, and builds `llama-server` with at most two jobs by default.
Its prebuilt Web UI download is disabled because the benchmark only uses the
local HTTP inference API.

Fetch the two source archives and one GGUF checkpoint on a machine with GitHub
and Hugging Face access, then transfer only these artifacts to the compute
host. The source archive SHA-256 values are `6e97dc0a238025a333fa0b6da92cb8017e9b532c5ac7216bb5028b07c960b22f`
for JevK5 and `6929ee4dc32123cfc4d9ecf3fc7da448b4fe51aab5dc665ed3e2992f0106c688`
for llama.cpp. No market history needs to move.

```sh
JEVK5_SOURCE_ARCHIVE=/path/jevk5-source.tar.gz \
LLAMA_SOURCE_ARCHIVE=/path/llama-source.tar.gz \
JEVK5_GGUF_PATH=/path/jevk5-4b-v0.3-Q4_K_M.gguf \
bash scripts/setup_jevk5_server.sh

JEVK5_GGUF_PATH=/path/jevk5-4b-v0.3-Q4_K_M.gguf
OMP_NUM_THREADS=4 nice -n 15 /mnt/third/jev-bots-bench/llama-jevk5/build/bin/llama-server \
  -m "$JEVK5_GGUF_PATH" -c 8192 -ngl 0 -t 4 --host 127.0.0.1 --port 18085
```

In a second shell, after `llama-server` is ready:

```sh
head -n 1 /mnt/third/jev-bots-bench/weekly/events.jsonl | \
  JEVK5_SERVER_URL=http://127.0.0.1:18085 \
  .venv-jevk5/bin/python adapters/jevk5_decide.py

JEVK5_SERVER_URL=http://127.0.0.1:18085 python3 benchmark/run.py invoke \
  --events /mnt/third/jev-bots-bench/weekly/events.jsonl \
  --output /mnt/third/jev-bots-bench/weekly/jevk5.responses.jsonl \
  -- .venv-jevk5/bin/python adapters/jevk5_decide.py
```

The adapter accepts one `{ "id": "...", "state": "..." }` object per line
and emits a same-ID `up`/`down` prediction plus both probabilities. The
decision question is `next_7_day_price_direction`, as in the other adapters.
It uses the published 4B v0.3 temperature `1.22` and knockout temperature
`0.93`. It requests the top 128 token log probabilities and rejects a decision
if an answer letter is absent, rather than accepting the upstream fallback
floor value. Ties select `down`. The benchmark runner measures wall-clock latency
including the server request. The separately started server's model-load time
is excluded, so record it separately if comparing cold starts. This is a
general decision model, not a trading model;
any predictive result must come from the held-out replay. A verified training
cutoff for the underlying base model is unavailable here, so the 2023-2026
trading replay is retrospective, not certified out of sample.

The one-event CPU smoke on server1 produced `down` with `P(down)=0.5115768657`
in 78.5 seconds at two threads and 60.2 seconds at four threads while other
backtests occupied the machine. Extrapolating the four-thread observation to
all 1,382 requests gives about 23 hours for a serial replay under similar
load; actual duration needs measurement. This smoke is not a trading result.
