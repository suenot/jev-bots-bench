#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_ARCHIVE="${MINOJEV_SOURCE_ARCHIVE:?Set MINOJEV_SOURCE_ARCHIVE to the pinned source tar}"
MODEL_PATH="${MINOJEV_MODEL_PATH:?Set MINOJEV_MODEL_PATH to the pinned general/ checkpoint directory}"
SOURCE_DIR="${MINOJEV_SOURCE_DIR:-$ROOT/.runtime-minojev/source}"
VENV="${MINOJEV_VENV:-$ROOT/.venv-minojev}"

printf '%s  %s\n' 9df15ceda2c36de782f82d8c79cc6fb43b43e839e55c3cdca4908f5f95d3e028 "$SOURCE_ARCHIVE" | sha256sum -c -
printf '%s  %s\n' 169ad53ec313c3a34b06c0809216e4fc072cce444a5d4ff2b59690d064130ed5 "$MODEL_PATH/backbone/model.safetensors" | sha256sum -c -
printf '%s  %s\n' 35209573555f0442254c257e8ff57f04652ecb24c2db8d05b3240c9e16777bb2 "$MODEL_PATH/head.safetensors" | sha256sum -c -
printf '%s  %s\n' 7ff92f3743e215748ac37dca3c1537ecc1c28cd2aaaa2b8ddf2fc4618ebb6ec7 "$MODEL_PATH/config.json" | sha256sum -c -
printf '%s  %s\n' db21e5529322523f48341a67b677e772ab7818e06226e145e8cec40b22197269 "$MODEL_PATH/backbone/config.json" | sha256sum -c -
printf '%s  %s\n' be75606093db2094d7cd20f3c2f385c212750648bd6ea4fb2bf507a6a4c55506 "$MODEL_PATH/backbone/tokenizer.json" | sha256sum -c -
printf '%s  %s\n' bd66398c16582f40ef7d7ff7e34d9d327d67d97ee7f97648cfc8fb598967e321 "$MODEL_PATH/backbone/minojev_tokenizer.json" | sha256sum -c -
printf '%s  %s\n' c4f4c62b741ab2940841480f9942f378d7d3878d47c2babb862af7381c59b952 "$MODEL_PATH/backbone/tokenizer_config.json" | sha256sum -c -

mkdir -p "$SOURCE_DIR"
tar -xf "$SOURCE_ARCHIVE" -C "$SOURCE_DIR"
python3.12 -m venv "$VENV"
"$VENV/bin/python" -m pip install 'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
"$VENV/bin/python" -m pip install -r "$ROOT/adapters/requirements-minojev-cpu-lock.txt"
"$VENV/bin/python" -m pip install --no-deps "$SOURCE_DIR"
"$VENV/bin/python" -m pip check
printf 'Source: %s\nModel: %s\nVenv: %s\n' "$SOURCE_DIR" "$MODEL_PATH" "$VENV"
