#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_ARCHIVE="${GLIFORMER_SOURCE_ARCHIVE:?Set GLIFORMER_SOURCE_ARCHIVE to the pinned source tar}"
MODEL_PATH="${GLIFORMER_MODEL_PATH:?Set GLIFORMER_MODEL_PATH to the pinned checkpoint directory}"
SOURCE_DIR="${GLIFORMER_SOURCE_DIR:-$ROOT/.runtime-gliformer/source}"
VENV="${GLIFORMER_VENV:-$ROOT/.venv-gliformer}"

printf '%s  %s\n' ba0e024ed2d45b75c6fa8943c1af8edc1c0121ce716d41f972cad27796f9f0ee "$SOURCE_ARCHIVE" | sha256sum -c -
printf '%s  %s\n' f80b29199d66f878669f283703e4dba9fd726755dcc20aba1ed0d24fce4a23f1 "$MODEL_PATH/pytorch_model.bin" | sha256sum -c -
printf '%s  %s\n' 80aec1c8824bd58d6733f27d78a8271420f2c7008e4b0c81313d8da09624eea4 "$MODEL_PATH/gliner_config.json" | sha256sum -c -
printf '%s  %s\n' 2286c2dd1929d355fabff24926d90011f8c4072c520a8ed3a46edaf7c6228da0 "$MODEL_PATH/tokenizer.json" | sha256sum -c -
printf '%s  %s\n' c2043d84b0dee751af5121a7d1f0267ce63a5ea25889fbd524d7789dfff04480 "$MODEL_PATH/tokenizer_config.json" | sha256sum -c -

mkdir -p "$SOURCE_DIR"
tar -xf "$SOURCE_ARCHIVE" -C "$SOURCE_DIR"
python3.12 -m venv "$VENV"
"$VENV/bin/python" -m pip install 'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
"$VENV/bin/python" -m pip install -r "$ROOT/adapters/requirements-gliformer-cpu-lock.txt"
"$VENV/bin/python" -m pip install --no-deps "$SOURCE_DIR"
"$VENV/bin/python" -m pip check
printf 'Source: %s\nModel: %s\nVenv: %s\n' "$SOURCE_DIR" "$MODEL_PATH" "$VENV"
