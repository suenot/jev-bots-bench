#!/usr/bin/env bash
set -euo pipefail

bench_root="${1:-/mnt/third/jev-bots-bench}"
cd "$bench_root"
bench_root="$(pwd -P)"
if [[ -n "${GLINER_MODEL_PATH:-}" ]]; then
  (cd "$GLINER_MODEL_PATH" && sha256sum --check "$bench_root/adapters/gliner25_checkpoint.sha256")
fi
python3 -m venv .venv-gliner
python_bin="$bench_root/.venv-gliner/bin/python"
"$python_bin" -m pip install --disable-pip-version-check --no-input --upgrade pip
"$python_bin" -m pip install --disable-pip-version-check --no-input 'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
if [[ -n "${GLINER_SOURCE_ARCHIVE:-}" ]]; then
  archive="$GLINER_SOURCE_ARCHIVE"
  expected_sha="060577b496e84cd818fbbb60bcb39541032ea6e49ec638393c2101050fba5b49"
  printf '%s  %s\n' "$expected_sha" "$archive" | sha256sum --check
  tar -xzf "$archive" -C "$bench_root"
  sed '/^gliner2\[/d' adapters/requirements-gliner-decide.txt > .venv-gliner/pinned-dependencies.txt
  "$python_bin" -m pip install --disable-pip-version-check --no-input -r .venv-gliner/pinned-dependencies.txt
  "$python_bin" -m pip install --disable-pip-version-check --no-input './GLiNER2-55656fbfa01d3d4a77485e1a1eeeaf682990ccdf[local]'
else
  "$python_bin" -m pip install --disable-pip-version-check --no-input -r adapters/requirements-gliner-decide.txt
fi
"$python_bin" -m pip freeze > .venv-gliner/requirements-installed.txt
"$python_bin" -c 'import torch, gliner2; print("torch", torch.__version__, "gliner2 imported")'
