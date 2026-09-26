#!/usr/bin/env bash
set -euo pipefail

bench_root="${1:-/mnt/third/jev-bots-bench}"
source_archive="${ZEFAN_SOURCE_ARCHIVE:?Set ZEFAN_SOURCE_ARCHIVE to the pinned runtime source archive}"
package_archive="${ZEFAN_PACKAGE_ARCHIVE:?Set ZEFAN_PACKAGE_ARCHIVE to the pinned checkpoint package archive}"
base_archive="${ZEFAN_BASE_SMALL_ARCHIVE:?Set ZEFAN_BASE_SMALL_ARCHIVE to the pinned base configuration/tokenizer archive}"
model_root="$bench_root/models/zefan-open-jev"
base_snapshot="$model_root/hub/models--Qwen--Qwen3.5-2B/snapshots/15852e8c16360a2fea060d615a32b45270f8a8fc"
checkpoint="$model_root/Open-Jev-2B/package/checkpoint"

printf '%s  %s\n' '881c65c55696634e98a02b3d6e65bde0045d225fed9e5a6bb984819e88e48002' "$source_archive" | sha256sum --check

mkdir -p "$bench_root/.venv-zefan-open-jev/source" "$model_root/Open-Jev-2B" "$base_snapshot"
tar -xzf "$source_archive" -C "$bench_root/.venv-zefan-open-jev/source"
tar -xzf "$package_archive" --exclude='._*' -C "$model_root/Open-Jev-2B"
tar -xzf "$base_archive" --exclude='._*' -C "$base_snapshot"
# macOS tar may include AppleDouble metadata beside the real files. It is not
# part of either pinned checkpoint and must not enter the composite digest.
find "$model_root/Open-Jev-2B/package" "$base_snapshot" -type f -name '._*' -delete

python3 - "$model_root/Open-Jev-2B/package" "$checkpoint" "$base_snapshot" "$bench_root/adapters/zefan_open_jev_base_files.json" <<'PY'
import hashlib, json, pathlib, sys
package, checkpoint, snapshot, base_manifest_path = (pathlib.Path(value) for value in sys.argv[1:])
manifest = json.loads((package / 'manifest.json').read_text())
for name, expected in manifest['files'].items():
    path = package / name
    if path.stat().st_size != expected['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != expected['sha256']:
        raise SystemExit(f'package manifest mismatch: {name}')
config = json.loads((checkpoint / 'model.json').read_text())
if config['model_id'] != 'Qwen/Qwen3.5-2B' or config['revision'] != '15852e8c16360a2fea060d615a32b45270f8a8fc':
    raise SystemExit('package/base revision mismatch')
base_manifest = json.loads(base_manifest_path.read_text())
if base_manifest['repo'] != config['model_id'] or base_manifest['revision'] != config['revision']:
    raise SystemExit('base file manifest revision mismatch')
for name, expected_file in base_manifest['files'].items():
    path = snapshot / name
    if path.stat().st_size != expected_file['bytes']:
        raise SystemExit(f'base file size mismatch: {name}')
    file_digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            file_digest.update(block)
    if file_digest.hexdigest() != expected_file['sha256']:
        raise SystemExit(f'base file hash mismatch: {name}')
digest = hashlib.sha256()
for path in sorted(checkpoint.rglob('*')):
    if path.is_file():
        digest.update(str(path.relative_to(checkpoint)).encode() + b'\0')
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
expected = '3076462e6356412082e79af909227b39b2863b90def79155ca0821aa506b7ded'
if digest.hexdigest() != expected:
    raise SystemExit('checkpoint composite hash mismatch')
print(f'package verified: {len(manifest["files"])} files; base verified: {len(base_manifest["files"])} files; checkpoint {expected}')
PY

python3 -m venv "$bench_root/.venv-zefan-open-jev"
python_bin="$bench_root/.venv-zefan-open-jev/bin/python"
"$python_bin" -m pip install --disable-pip-version-check --no-input 'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
"$python_bin" -m pip install --disable-pip-version-check --no-input -r "$bench_root/adapters/requirements-zefan-open-jev.txt"
"$python_bin" -m pip install --disable-pip-version-check --no-input --no-deps "$bench_root/.venv-zefan-open-jev/source"
"$python_bin" -m pip freeze > "$bench_root/.venv-zefan-open-jev/requirements-installed.txt"
HF_HUB_CACHE="$model_root/hub" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    "$python_bin" -c 'import jev, torch, transformers, peft; print("Open-Jev CPU runtime imported", torch.__version__, transformers.__version__, peft.__version__)'
