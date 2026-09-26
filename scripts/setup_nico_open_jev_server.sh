#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_ARCHIVE="${NICO_OPEN_JEV_SOURCE_ARCHIVE:?Set NICO_OPEN_JEV_SOURCE_ARCHIVE to the pinned runtime archive}"
MODEL_PATH="${NICO_OPEN_JEV_MODEL_PATH:?Set NICO_OPEN_JEV_MODEL_PATH to the pinned checkpoint directory}"
NODE_DIR="${NICO_OPEN_JEV_NODE_DIR:-$ROOT/.runtime-nico-open-jev/node-v22.16.0-linux-x64}"
NODE_ARCHIVE="${NICO_OPEN_JEV_NODE_ARCHIVE:-$ROOT/.runtime-nico-open-jev/jev-node-v22.16.0-linux-x64.tar.xz}"
SOURCE_DIR="${NICO_OPEN_JEV_SOURCE_DIR:-$ROOT/.runtime-nico-open-jev/source}"
SOURCE_SHA="e038bdce74fe5b2dbc70c660d3a3194214d143b7d26d391881042ebddffaf31c"
WEIGHT_SHA="886cf56af0dd14b6938415af724eb48e5a5d5db3c728c05b50702585c0ea29ab"
GRAPH_SHA="5be15f8076cc2c16d76fb2e9c8703a0d7d355950422ce47e8dae072ce9ca3b8e"
NODE_SHA="f4cb75bb036f0d0eddf6b79d9596df1aaab9ddccd6a20bf489be5abe9467e84e"

printf '%s  %s\n' "$SOURCE_SHA" "$SOURCE_ARCHIVE" | sha256sum -c -
printf '%s  %s\n' "$WEIGHT_SHA" "$MODEL_PATH/onnx/model_q4.onnx_data" | sha256sum -c -
printf '%s  %s\n' "$GRAPH_SHA" "$MODEL_PATH/onnx/model_q4.onnx" | sha256sum -c -
printf '%s  %s\n' "$NODE_SHA" "$NODE_ARCHIVE" | sha256sum -c -
mkdir -p "$(dirname "$NODE_DIR")"
tar -xJf "$NODE_ARCHIVE" -C "$(dirname "$NODE_DIR")"
test -x "$NODE_DIR/bin/node"
test -f "$MODEL_PATH/config.json"
test -f "$MODEL_PATH/onnx/model_q4.onnx"

mkdir -p "$SOURCE_DIR"
tar -xf "$SOURCE_ARCHIVE" -C "$SOURCE_DIR"
cp "$ROOT/adapters/nico_open_jev_package-lock.json" "$SOURCE_DIR/package-lock.json"
export PATH="$NODE_DIR/bin:$PATH"
cd "$SOURCE_DIR"
npm ci --no-audit --no-fund
npm run build
printf 'Source: %s\nModel: %s\nNode: %s\n' "$SOURCE_DIR" "$MODEL_PATH" "$NODE_DIR"
