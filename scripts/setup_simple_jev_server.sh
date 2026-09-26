#!/usr/bin/env bash
set -euo pipefail

bench_root="${1:-/mnt/third/jev-bots-bench}"
archive="${SIMPLE_JEV_SOURCE_ARCHIVE:?Set SIMPLE_JEV_SOURCE_ARCHIVE to the pinned runtime archive}"
expected_sha="b54815a83d2e1143abcb8faf0a29696f7f59bd3845db15445fba2b77bf735cb5"
printf '%s  %s\n' "$expected_sha" "$archive" | sha256sum --check

mkdir -p "$bench_root/simple-jev-source"
tar -xzf "$archive" -C "$bench_root/simple-jev-source"
python3 -m venv "$bench_root/.venv-simple-jev"
python_bin="$bench_root/.venv-simple-jev/bin/python"
"$python_bin" -m pip install --disable-pip-version-check --no-input --upgrade pip
"$python_bin" -m pip install --disable-pip-version-check --no-input 'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
"$python_bin" -m pip install --disable-pip-version-check --no-input -r "$bench_root/adapters/requirements-simple-jev-decide.txt"
"$python_bin" -m pip install --disable-pip-version-check --no-input "$bench_root/simple-jev-source/hf-server"
"$python_bin" -m pip freeze > "$bench_root/.venv-simple-jev/requirements-installed.txt"
"$python_bin" -c 'import hf_server, torch, transformers; print("simple-jev", torch.__version__, transformers.__version__)'
