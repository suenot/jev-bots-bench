#!/usr/bin/env bash
set -euo pipefail

bench_root="${1:-/mnt/third/jev-bots-bench}"
archive="${KEV_SOURCE_ARCHIVE:?Set KEV_SOURCE_ARCHIVE to the pinned runtime archive}"
expected_sha="f91272dd2ceb3d595de788aa1d24defc2b08e60588856dd83947536833a9c181"
printf '%s  %s\n' "$expected_sha" "$archive" | sha256sum --check

mkdir -p "$bench_root/kev-source"
tar -xzf "$archive" -C "$bench_root/kev-source"
python3 -m venv "$bench_root/.venv-kev"
python_bin="$bench_root/.venv-kev/bin/python"
"$python_bin" -m pip install --disable-pip-version-check --no-input --upgrade pip
"$python_bin" -m pip install --disable-pip-version-check --no-input \
  'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
"$python_bin" -m pip install --disable-pip-version-check --no-input \
  -r "$bench_root/adapters/requirements-kev-decide.txt"
"$python_bin" -m pip install --disable-pip-version-check --no-input --no-deps \
  "$bench_root/kev-source"
"$python_bin" -m pip freeze > "$bench_root/.venv-kev/requirements-installed.txt"
"$python_bin" -c 'import kev, torch, transformers, peft; print("kev", torch.__version__, transformers.__version__, peft.__version__)'
