#!/usr/bin/env bash
set -euo pipefail

bench_root="${1:-/mnt/third/jev-bots-bench}"
archive="${ANYJEV_SOURCE_ARCHIVE:?Set ANYJEV_SOURCE_ARCHIVE to the pinned runtime archive}"
expected_sha="4796ba3b9a50757dd82487797fc443ffd1560daa3939032a07d78215fa5951ba"
printf '%s  %s\n' "$expected_sha" "$archive" | sha256sum --check

mkdir -p "$bench_root/anyjev-source"
tar -xzf "$archive" -C "$bench_root/anyjev-source"
python3 -m venv "$bench_root/.venv-anyjev"
python_bin="$bench_root/.venv-anyjev/bin/python"
"$python_bin" -m pip install --disable-pip-version-check --no-input --upgrade pip
"$python_bin" -m pip install --disable-pip-version-check --no-input 'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
"$python_bin" -m pip install --disable-pip-version-check --no-input -r "$bench_root/adapters/requirements-anyjev-decide.txt"
"$python_bin" -m pip install --disable-pip-version-check --no-input --no-deps "$bench_root/anyjev-source"
"$python_bin" -m pip freeze > "$bench_root/.venv-anyjev/requirements-installed.txt"
"$python_bin" -c 'import anyjev, torch, transformers; print("anyjev", torch.__version__, transformers.__version__)'
