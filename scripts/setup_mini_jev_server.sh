#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_ARCHIVE="${MINI_JEV_SOURCE_ARCHIVE:?Set MINI_JEV_SOURCE_ARCHIVE to the pinned source tar}"
MODEL_PATH="${MINI_JEV_MODEL_PATH:?Set MINI_JEV_MODEL_PATH to the pinned Qwen checkpoint directory}"
SOURCE_DIR="${MINI_JEV_SOURCE_DIR:-$ROOT/.runtime-mini-jev/source}"
VENV="${MINI_JEV_VENV:-$ROOT/.venv-mini-jev}"

printf '%s  %s\n' bb34dfbbabc3f4cbb48a2eb2be0d50b1fee9c5149a666ff899d56202e85df611 "$SOURCE_ARCHIVE" | sha256sum -c -
declare -A SHA256=(
  [config.json]=5beea1a4a34c62782bfb2f911c606741a3bab8f92d80a118fa053c28af12e8ba
  [generation_config.json]=835fffe355c9438e7a25be099b3fccaa98350b83451f9fd2d99512e74f1ade48
  [model.safetensors.index.json]=d6c42883a895dfef5b0080ed2116a1bcd764f558406b98923d675978a1abf29c
  [tokenizer.json]=aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4
  [tokenizer_config.json]=a62ff0a2472a0fa1b8eaabcb57c59b58afa42a22831dc141400b6e0cf2b65ce3
  [vocab.json]=ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910
  [merges.txt]=599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3
  [model-00001-of-00003.safetensors]=75311d91bb08cf0b882913da464a1e722a31fb44db35208663487efb7a3d8ed6
  [model-00002-of-00003.safetensors]=0b48adbb1f60e901153d91907ba11ce63bd4b8b584482e730f48808d055dfba1
  [model-00003-of-00003.safetensors]=7dd39ccca5e4de123c74c14af44c9bf2eb75df33b4614382af0134528e060d5d
)
for name in "${!SHA256[@]}"; do
  printf '%s  %s\n' "${SHA256[$name]}" "$MODEL_PATH/$name" | sha256sum -c -
done

mkdir -p "$SOURCE_DIR"
tar -xf "$SOURCE_ARCHIVE" -C "$SOURCE_DIR"
python3.12 -m venv "$VENV"
"$VENV/bin/python" -m pip install 'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
"$VENV/bin/python" -m pip install -r "$ROOT/adapters/requirements-mini-jev-cpu-lock.txt"
"$VENV/bin/python" -m pip check
printf 'Source: %s\nModel: %s\nVenv: %s\n' "$SOURCE_DIR" "$MODEL_PATH" "$VENV"
