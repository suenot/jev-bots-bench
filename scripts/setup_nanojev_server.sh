#!/usr/bin/env bash
set -euo pipefail

bench_root="${1:-/mnt/third/jev-bots-bench}"
archive="${NANOJEV_SOURCE_ARCHIVE:?Set NANOJEV_SOURCE_ARCHIVE to the pinned runtime archive}"
expected_sha="3370f5dec53956138a42342b4d1bd180ea697796317570294de58d3395bb018f"
printf '%s  %s\n' "$expected_sha" "$archive" | sha256sum --check

mkdir -p "$bench_root/nanojev-source"
tar -xzf "$archive" -C "$bench_root/nanojev-source"
python3 -m venv "$bench_root/.venv-nanojev"
python_bin="$bench_root/.venv-nanojev/bin/python"
"$python_bin" -m pip install --disable-pip-version-check --no-input --upgrade pip
"$python_bin" -m pip install --disable-pip-version-check --no-input \
  'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
"$python_bin" -m pip install --disable-pip-version-check --no-input \
  -r "$bench_root/adapters/requirements-nanojev-decide.txt"
"$python_bin" -m pip freeze > "$bench_root/.venv-nanojev/requirements-installed.txt"
"$python_bin" -c 'import torch, transformers, safetensors; print("nanojev", torch.__version__, transformers.__version__, safetensors.__version__)'
