#!/usr/bin/env bash
set -euo pipefail

bench_root="${1:-/mnt/third/jev-bots-bench}"
archive="${SEMIF_SOURCE_ARCHIVE:?Set SEMIF_SOURCE_ARCHIVE to the pinned runtime archive}"
expected_sha="7d4476eb65dbb259010ece167e9ef5c08d0c9f1fdd8a60886ab051a126b97fc1"
printf '%s  %s\n' "$expected_sha" "$archive" | sha256sum --check

mkdir -p "$bench_root/semif-source"
tar -xzf "$archive" -C "$bench_root/semif-source"
python3 -m venv "$bench_root/.venv-semif"
python_bin="$bench_root/.venv-semif/bin/python"
"$python_bin" -m pip install --disable-pip-version-check --no-input --upgrade pip
# The GGUF scorer imports only tokenizer, NumPy, and llama.cpp code. The
# source package's Torch requirement is for its separate full-precision path.
if [[ -n "${SEMIF_LLAMA_WHEEL:-}" ]]; then
  expected_wheel_sha="d172f3d3c8cdd194c3c47c71cb077ed6e61354a2d0f939ceeac0c8fd29999596"
  printf '%s  %s\n' "$expected_wheel_sha" "$SEMIF_LLAMA_WHEEL" | sha256sum --check
  "$python_bin" -m pip install --disable-pip-version-check --no-input "$SEMIF_LLAMA_WHEEL"
  "$python_bin" -m pip install --disable-pip-version-check --no-input \
    -r "$bench_root/adapters/requirements-semif-decide.txt"
else
  "$python_bin" -m pip install --disable-pip-version-check --no-input \
    --only-binary llama-cpp-python \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu \
    -r "$bench_root/adapters/requirements-semif-decide.txt"
fi
"$python_bin" -m pip install --disable-pip-version-check --no-input --no-deps \
  "$bench_root/semif-source"
"$python_bin" -m pip freeze > "$bench_root/.venv-semif/requirements-installed.txt"
"$python_bin" -c 'import semif_phase1, llama_cpp, transformers; print("semif", semif_phase1.__version__, llama_cpp.__version__, transformers.__version__)'
