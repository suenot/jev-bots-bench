#!/usr/bin/env bash
set -euo pipefail

bench_root="${1:-/mnt/third/jev-bots-bench}"
archive="${LAYA_SOURCE_ARCHIVE:?Set LAYA_SOURCE_ARCHIVE to the pinned source tarball path}"
expected_source_sha="4203c0832f92a5981a9422107e30b7a6ae157c787fa6e3a9c97b75bcbf2deaf7"
printf '%s  %s\n' "$expected_source_sha" "$archive" | sha256sum --check

cd "$bench_root"
bench_root="$(pwd -P)"
if [[ -n "${LAYA_MODEL_PATH:-}" ]]; then
  (cd "$LAYA_MODEL_PATH" && sha256sum --check "$bench_root/adapters/laya_checkpoint.sha256")
fi
python3 -m venv .venv-laya
python_bin="$bench_root/.venv-laya/bin/python"
"$python_bin" -m pip install --disable-pip-version-check --no-input --upgrade pip
"$python_bin" -m pip install --disable-pip-version-check --no-input 'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
sed '/^laya @ git+/d' adapters/requirements-laya-decide.txt > .venv-laya/pinned-dependencies.txt
"$python_bin" -m pip install --disable-pip-version-check --no-input -r .venv-laya/pinned-dependencies.txt
mkdir -p .venv-laya/source
tar -xzf "$archive" -C .venv-laya/source --strip-components=1
"$python_bin" -m pip install --disable-pip-version-check --no-input --no-deps .venv-laya/source
"$python_bin" -m pip freeze > .venv-laya/requirements-installed.txt
"$python_bin" -c 'import torch, laya; print("torch", torch.__version__, "laya imported")'
