# nico-martin/open-jev CPU adapter

This adapter uses the actual open-jev DeBERTa decision model, not a language
model standing in for it. The [source library](https://github.com/nico-martin/open-jev/tree/52667199e8a55553e1865a41f43fcb7d4dd92779)
is pinned to `52667199e8a55553e1865a41f43fcb7d4dd92779`. The
[public checkpoint](https://huggingface.co/onnx-community/open-jev-deberta-v3-large-ONNX/tree/7c79f25b5ac496089f448a969c801872ad59d31c)
is pinned to `7c79f25b5ac496089f448a969c801872ad59d31c`. Its q4 ONNX
weight data is 477,415,936 bytes, SHA-256
`886cf56af0dd14b6938415af724eb48e5a5d5db3c728c05b50702585c0ea29ab`.
The ONNX graph SHA-256 is
`5be15f8076cc2c16d76fb2e9c8703a0d7d355950422ce47e8dae072ce9ca3b8e`.
The adapter fixes Node.js CPU, q4 weights, the source model's default
temperature `1.05`, and a binary `up`/`down` choice. Its output is the
model's two-class distribution. This checkpoint was trained on nonmarket
domains, so a positive backtest requires independent measurement.

## Reproduce setup

The compute host has no direct Hugging Face or GitHub download path. Prepare
the following files elsewhere and transfer **only model/source artifacts**:

1. The source runtime archive:

   ```sh
   git clone https://github.com/nico-martin/open-jev.git open-jev
   git -C open-jev archive --format=tar 52667199e8a55553e1865a41f43fcb7d4dd92779 src package.json tsconfig.json scripts/build.mjs > open-jev-runtime.tar
   sha256sum open-jev-runtime.tar
   ```

   Expected SHA-256: `e038bdce74fe5b2dbc70c660d3a3194214d143b7d26d391881042ebddffaf31c`.

2. Node.js 22.16.0 Linux x64 tarball from
   [nodejs.org](https://nodejs.org/dist/v22.16.0/). Its SHA-256 is
   `f4cb75bb036f0d0eddf6b79d9596df1aaab9ddccd6a20bf489be5abe9467e84e`.
   Transfer it to `.runtime-nico-open-jev/jev-node-v22.16.0-linux-x64.tar.xz`.
   The setup script verifies and extracts it there.

3. From the pinned checkpoint revision, fetch `config.json`,
   `tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json`,
   `added_tokens.json`, `spm.model`, `open_jev_config.json`,
   `onnx/model_q4.onnx`, and `onnx/model_q4.onnx_data`. Keep the same paths
   beneath the local model directory. Verify the large weight hash above.

Then, at the benchmark repository root:

The checked-in `nico_open_jev_package-lock.json` pins the npm dependency
tree, including Transformers.js 4.3.0 and ONNX Runtime 1.30.0. Setup uses
`npm ci` against that lockfile.

```sh
NICO_OPEN_JEV_SOURCE_ARCHIVE=/path/to/open-jev-runtime.tar \
NICO_OPEN_JEV_MODEL_PATH=/path/to/model \
  bash scripts/setup_nico_open_jev_server.sh

NICO_OPEN_JEV_SOURCE_DIR="$PWD/.runtime-nico-open-jev/source" \
NICO_OPEN_JEV_MODEL_PATH=/path/to/model \
  .runtime-nico-open-jev/node-v22.16.0-linux-x64/bin/node \
  adapters/nico_open_jev_decide.mjs < data/weekly-v1/events.jsonl > decisions.jsonl
```

For the benchmark runner, pass the same environment variables to `invoke`
and put the Node command after `--`. The adapter loads once per stream,
reads one `{id,state}` object per line, and emits one decision per line.
`state` must contain only closed historical observations available at the
decision time. The published runner enforces the same one-hour execution lag
and long/cash policy for every model. The source's 512-token context limit is
checked with `truncation: "error"` to avoid silently changing market input.
At this benchmark's pinned tokenizer revision, all 1,382 published states use
231–234 state tokens, below the checkpoint's 256-token state limit.

One-event Linux x64 CPU smoke with two assigned cores and event `e000001`
returned `up` with `p(up)=0.6171370202118195` in 10.341 seconds of inference,
excluding model load. The response passed the benchmark runner's
`valid_decision` check. This is a protocol check, not a trading result.
