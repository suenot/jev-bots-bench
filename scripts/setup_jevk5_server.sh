#!/usr/bin/env bash
set -euo pipefail

bench_root="${1:-/mnt/third/jev-bots-bench}"
jevk5_archive="${JEVK5_SOURCE_ARCHIVE:?Set JEVK5_SOURCE_ARCHIVE to the pinned JevK5 source archive}"
llama_archive="${LLAMA_SOURCE_ARCHIVE:?Set LLAMA_SOURCE_ARCHIVE to the pinned llama.cpp source archive}"
model_path="${JEVK5_GGUF_PATH:?Set JEVK5_GGUF_PATH to the pinned GGUF checkpoint}"

printf '%s  %s\n' '6e97dc0a238025a333fa0b6da92cb8017e9b532c5ac7216bb5028b07c960b22f' "$jevk5_archive" | sha256sum --check
printf '%s  %s\n' '6929ee4dc32123cfc4d9ecf3fc7da448b4fe51aab5dc665ed3e2992f0106c688' "$llama_archive" | sha256sum --check
printf '%s  %s\n' '94ca0d7745c47f79091b0892ca657c81d9dc9e4ed0238ba0a7ea261d8938c882' "$model_path" | sha256sum --check

mkdir -p "$bench_root/.venv-jevk5/source" "$bench_root/llama-jevk5"
tar -xzf "$jevk5_archive" -C "$bench_root/.venv-jevk5/source" --strip-components=1
tar -xzf "$llama_archive" -C "$bench_root/llama-jevk5" --strip-components=1
python3 -m venv "$bench_root/.venv-jevk5"
"$bench_root/.venv-jevk5/bin/python" -m pip install --disable-pip-version-check --no-input --no-deps "$bench_root/.venv-jevk5/source"
cmake -S "$bench_root/llama-jevk5" -B "$bench_root/llama-jevk5/build" -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF -DGGML_AVX2=ON -DLLAMA_USE_PREBUILT_UI=OFF
cmake --build "$bench_root/llama-jevk5/build" --target llama-server -j "${JEVK5_BUILD_JOBS:-2}"
"$bench_root/.venv-jevk5/bin/python" -c 'from jevk5 import JevK5GGUF; print("JevK5GGUF imported")'
