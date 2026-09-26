# Changelog

All notable changes to this project are documented here.

## [Unreleased]

## [0.4.0] - 2026-09-26

### Added

- Add checksum-verified CPU adapters and reproduction guides for JevK5 GGUF, SemIf, nico-martin/open-jev ONNX, and GLiFormer large-v1.
- Add a deterministic event sharding and response merge helper for long CPU inference runs.

### Changed

- Pin the exact GGUF and ONNX weight revisions used in real one-event protocol smokes, separate from upstream source commits. Mark full runs as pending until their complete responses pass evaluation.

## [0.3.0] - 2026-09-26

### Added

- Publish actual nine-pair, three-year baseline aggregates and precise engine compatibility statuses.
- Add verified CPU adapters and setup paths for GLiNER2.5-Decide, Laya, and Simple Jev; show code and weight revisions separately.
- Resume long model invocations from an exact response prefix.

### Fixed

- Score a week when its scheduled entry and exit minute opens exist, without selecting on the completeness of intervening future days. Supersede the original settlement hash before model evaluation.
- Enforce a one-hour model deadline across potentially simultaneous decisions and make partial adapter output subject to timeout.
- Label drawdown as sampled at weekly marks and leave Brier absent for class-only responses.

### Security

- Exclude local Vercel environment and project-link files from static deployment uploads.

## [0.2.0] - 2026-09-26

### Added

- Commit 1,382 causal model-facing weekly requests, pair coverage, and SHA-256 commitments for the sealed settlement file before model inference.

## [0.1.0] - 2026-09-26

### Added

- Public source inventory for 16 Jev-style decision engines and their pinned revisions.
- Causal warehouse replay, fixed long/cash policy, comparison baselines, and prefix audit.
- CPU adapters for GLiNER2.5-Decide, Laya, and GLiFormer.
- Static dashboard with model coverage and per-pair results loaded from the public summary.
