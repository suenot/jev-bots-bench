# Reproducible weekly decision benchmark

This directory contains the benchmark code and a pinned inventory of 16 decision engines. `../results/summary.json` is the small public aggregate contract. Its `running` status means the campaign is still in progress; inspect each model's status and measured rows. Never interpret a pending model as a zero-return strategy.

## Market data and protocol

Run `prepare` where the existing warehouse is mounted, normally server1. It reads `/mnt/second/trender/backtests/data/<PAIR>/klines_1m/YYYY-MM.parquet` in place. No historical candles need to be downloaded to a laptop. The legacy rows are a **Binance USDT perpetual futures price proxy**, not venue-specific spot fills. Funding, bid/ask spread, market impact, borrow and liquidations are unavailable.

The default window is 2023-02-01 through 2026-02-28, with nine prespecified pairs: BTC, ETH, SOL, BNB, LINK, DOT, TRX, BCH and UNI against USDT. A decision occurs each Monday at 00:00 UTC after 28 complete UTC daily candles. The request contains only dimensionless returns and volatility calculated from those closed candles. Each weekly interval is nonoverlapping. Entry/rebalance uses the open of Monday 01:00 UTC, one hour after the decision. The exit mark is the open of the following Monday 01:00 UTC. An incomplete lookback removes the request; a missing entry or exit minute open leaves the causal request intact but excludes that outcome from scoring. Missing intervening daily candles do not select the scored sample, because they are not needed to calculate the two scheduled fills. The coverage report counts exclusions for each pair; the simulator liquidates before a skipped week. It never fills missing candles. Every model response needs a measured inference latency within the one-hour execution delay or `evaluate` refuses to publish its trading result.

All policies use the same long/cash portfolio with target weight in `[0,1]` and the same execution rule. Default costs are 5 basis points fee plus 4 basis points slippage **on each traded side**. Returns and maximum drawdown are percentages of an initial unit of equity for each pair. Drawdown is sampled only at weekly exit marks and can miss worse swings within a week. A `full` row chains valid weekly intervals, holding cash across skipped weeks. A year row resets equity at the year's first decision, attributes the final weekly interval to its decision year and liquidates at its following Monday fill. Year and full rows must not be added together. `hold` targets 100% long; `momentum_7d` targets 100% long after a positive trailing seven-day return, otherwise cash. These rules use the same causal inputs and fills as models.

The 2023 rows start in March after the 28-day lookback, and the 2026 rows end
in February. They are partial calendar years, not annualized returns.

## Run on server1

Use an isolated Python environment with `pyarrow` installed. The evaluation and tests use only the standard library; `prepare` alone needs `pyarrow`. Paths below keep full event and settlement data on server1. Output under `../results/summary.json` is aggregate and can be committed after review.

```sh
python3 benchmark/run.py prepare \
  --events /mnt/third/jev-bots-bench/weekly/events.jsonl \
  --settlements /mnt/third/jev-bots-bench/weekly/settlements.jsonl \
  --coverage /mnt/third/jev-bots-bench/weekly/coverage.json
python3 benchmark/run.py audit \
  --events /mnt/third/jev-bots-bench/weekly/events.jsonl \
  --settlements /mnt/third/jev-bots-bench/weekly/settlements.jsonl
python3 benchmark/run.py invoke \
  --events /mnt/third/jev-bots-bench/weekly/events.jsonl \
  --output /mnt/third/jev-bots-bench/weekly/gliner25.responses.jsonl \
  -- python3 adapters/gliner_decide.py
python3 benchmark/run.py evaluate \
  --events /mnt/third/jev-bots-bench/weekly/events.jsonl \
  --settlements /mnt/third/jev-bots-bench/weekly/settlements.jsonl \
  --responses gliner25=/mnt/third/jev-bots-bench/weekly/gliner25.responses.jsonl \
  --ledger /mnt/third/jev-bots-bench/weekly/ledger.jsonl \
  --output results/summary.json
```

An adapter receives one JSON line `{"id":"e000001","state":"..."}` on stdin and must immediately flush one JSON line with the same ID on stdout. Canonical output is `{"id":"e000001","prediction":"up","probabilities":{"up":0.6,"down":0.4}}`. The predicted class must match the larger probability; ties select `down`. `invoke` replaces any adapter timing with measured wall-clock `latency_ms`, writes each response durably, and can resume an exact response prefix with `--resume`. For nonprobabilistic engines, `{"id":"...","prediction":"down"}` is valid and Brier is absent. An older adapter can return `target_weight` in `[0,1]` and optional `prob_up`. The runner rejects missing, repeated, extra, invalid or mismatched IDs. `evaluate` accepts any number of `MODEL_ID=FILE` response files from `models.json`; missing models remain pending. It rejects a response if any single request, or a conservative rolling group of up to nine requests that could share a Monday deadline, takes over one hour under serial serving. An adapter is responsible for loading the pinned source and weight revision and logging its runtime and dependencies. Its stdout must contain only JSON responses.

The public `summary.json` has `schema_version`, `generated_at`, `status`, `methodology`, `models`, `runs`, `baselines` and `provenance`. `runs` contain per-pair/per-year and full rows: `model_id`, `pair`, `period`, `n_decisions`, `accuracy`, `brier`, `return_pct`, `max_drawdown_pct`, `trade_count`, `latency_ms_p50`, and `latency_ms_p95`. `baselines` contain the same pair/period keys and trading metrics.
`models.json` supplies fallback statuses when no response file is passed to
`evaluate`; the generated `results/summary.json` is the source of truth for
which engines have published measurements.

For a CPU-heavy adapter, split only the model-facing event stream. Each shard
starts its own pinned adapter process. The helper verifies that a merged
response file contains every original event ID exactly once and restores
original order before evaluation:

```sh
python3 scripts/shard_events.py split --events weekly/events.jsonl \
  --dir weekly/simple-shards --shards 4
for i in 00 01 02 03; do
  OMP_NUM_THREADS=4 python3 benchmark/run.py invoke \
    --events "weekly/simple-shards/events-$i.jsonl" \
    --output "weekly/simple-shards/responses-$i.jsonl" \
    -- .venv-simple-jev/bin/python adapters/simple_jev_decide.py &
done
wait
python3 scripts/shard_events.py merge --events weekly/events.jsonl \
  --responses weekly/simple-shards/responses-*.jsonl \
  --output weekly/responses-simple_jev.jsonl
```

The full evaluation still sees one ordered response stream for each model.
After the short CPU runs finish, the pinned NanoJev and minojev setups can be
run sequentially with `bash scripts/queue_nano_mino_server.sh`. The queue waits
for complete GLiNER and nico response streams, records all 1,382 events with
`invoke --resume`, and keeps each model to two low-priority CPU threads. Its
per-model logs and responses are written under `weekly/`; restart the same
script if a run is interrupted.
The pinned mini-jev CPU runner can follow minojev with
`bash scripts/run_mini_jev_after_mino.sh`; it checks the predecessor's exact
event IDs before starting its own resumable 1,382-event pass.

When a complete model run is published, its response file and the previously
committed settlement hash are available under `results/` and `data/weekly-v1/`.
Run `python3 scripts/verify_published.py` to check hashes and recompute every
published model row without the raw minute archive. The optional detailed
ledger can stay on the compute host. The model-facing events contain no pair,
date, timestamp, or absolute price. Their sequential IDs correlate with
preparation order, but the audited adapter paths keep IDs as response metadata
and score only the historical state plus a fixed question. Relative price
patterns could still identify a period or pair indirectly; the protocol does
not prove anonymity. The inventory distinguishes project source commits from
weight revisions.

`audit` checks that truncating and mutating future settlement prices does not alter past replay results. Unit tests also change future daily bars and assert earlier model requests and settlement outcomes remain identical. This is a causality check of the harness, not proof that a third-party model was never trained on future market history. For every published model result, record the adapter commit, dependency versions, response file hash, and any documented training cutoff. An unknown cutoff must be marked unknown: that result is a retrospective diagnostic, not an out-of-sample claim.
