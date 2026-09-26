# Changelog

All notable changes to this project are documented here.

## [Unreleased]

## [0.6.0] - 2026-09-26

### Added

- Publish complete GLiNER2.5-Decide and nico-martin/open-jev response streams and their environment and artifact provenance.
- Compare three measured engines with hold and seven-day momentum across the same nine pairs and partial or full calendar periods.
- Publish checkpoint hash manifests and a reproducible one-event Nico option-order diagnostic.

### Changed

- Update the live dashboard from one to three verified model runs while the remaining CPU queues continue.

### Fixed

- Compare independently replayed result rows by model, pair, and period instead of depending on response-file argument order.
- Check all local checkpoint files during measured-model setup and verify Nico's npm lockfile in the publication replay.

## [0.5.0] - 2026-09-26

### Added

- Add pinned CPU adapters and reproduction guides for Kev, NanoJev, minojev, AnyJev, mini-jev, and Zefan-Cai/Open-Jev, with real one-event protocol checks.
- Publish Laya's complete response stream, sealed settlement rows, environment record, and a checksum and replay verifier for measured engines.
- Add a model-by-pair full-period comparison matrix with matching hold and seven-day momentum reference rows.
- Add durable, resumable server queues for the longer CPU runs.

### Changed

- Describe this as an exploratory retrospective comparison, including unknown model-training cutoffs and the order in which adapters were finished.
- Update the 16-engine inventory with pinned weight revisions and observed run status.

### Fixed

- Verify exact event IDs before a completed NanoJev or minojev response file is accepted by its queue.

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
