# Reproducible weekly decision benchmark

This directory contains the benchmark code and a pinned inventory of 16 decision engines. `../results/summary.json` is the small public aggregate contract; its current `running` status means no model outcomes have been measured. Never interpret a pending model as a zero-return strategy.

## Market data and protocol

Run `prepare` where the existing warehouse is mounted, normally server1. It reads `/mnt/second/trender/backtests/data/<PAIR>/klines_1m/YYYY-MM.parquet` in place. No historical candles need to be downloaded to a laptop. The legacy rows are a **Binance USDT perpetual futures price proxy**, not venue-specific spot fills. Funding, bid/ask spread, market impact, borrow and liquidations are unavailable.

The default window is 2023-02-01 through 2026-02-28, with nine prespecified pairs: BTC, ETH, SOL, BNB, LINK, DOT, TRX, BCH and UNI against USDT. A decision occurs each Monday at 00:00 UTC after 28 complete UTC daily candles. The request contains only dimensionless returns and volatility calculated from those closed candles. Each weekly interval is nonoverlapping. Entry/rebalance uses the open of Monday 01:00 UTC, one hour after the decision. The exit mark is the open of the following Monday 01:00 UTC. An incomplete lookback removes the request; a later gap or missing fill leaves the causal request intact but excludes that outcome from scoring. The coverage report counts both kinds of exclusions for each pair; the simulator liquidates before a skipped week. It never fills missing candles. A model's recorded inference latency must fit within the one-hour execution delay before its trading result is considered feasible.

All policies use the same long/cash portfolio with target weight in `[0,1]` and the same execution rule. Default costs are 5 basis points fee plus 4 basis points slippage **on each traded side**. Returns and maximum drawdown are percentages of an initial unit of equity for each pair. A `full` row chains valid weekly intervals, holding cash across skipped weeks. A year row resets equity at the year's first decision, attributes the final weekly interval to its decision year and liquidates at its following Monday fill. Year and full rows must not be added together. `hold` targets 100% long; `momentum_7d` targets 100% long after a positive trailing seven-day return, otherwise cash. These rules use the same causal inputs and fills as models.

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

An adapter receives one JSON line `{"id":"e000001","state":"..."}` on stdin and must immediately flush one JSON line with the same ID on stdout. Canonical output is `{"id":"e000001","prediction":"up","probabilities":{"up":0.6,"down":0.4}}`. The predicted class must match the larger probability; ties select `down`. `invoke` adds measured wall-clock `latency_ms`. For nonprobabilistic engines, `{"id":"...","prediction":"down"}` is valid. An older adapter can return `target_weight` in `[0,1]` and optional `prob_up`. The runner rejects missing, repeated, extra, invalid or mismatched IDs. `evaluate` accepts any number of `MODEL_ID=FILE` response files from `models.json`; missing models remain pending. An adapter is responsible for loading the pinned source and weight revision and logging its runtime and dependencies. Its stdout must contain only JSON responses.

The public `summary.json` has `schema_version`, `generated_at`, `status`, `methodology`, `models`, `runs`, `baselines` and `provenance`. `runs` contain per-pair/per-year and full rows: `model_id`, `pair`, `period`, `n_decisions`, `accuracy`, `brier`, `return_pct`, `max_drawdown_pct`, `trade_count`, `latency_ms_p50`, and `latency_ms_p95`. `baselines` contain the same pair/period keys and trading metrics. The private settlement and ledger files contain timestamps and prices; do not publish them as part of the aggregate. The model-facing events contain no pair, date, timestamp, or absolute price. The inventory distinguishes project source commits from weight revisions.

`audit` checks that truncating and mutating future settlement prices does not alter past replay results. Unit tests also change future daily bars and assert earlier model requests and settlement outcomes remain identical. This is a causality check of the harness, not proof that a third-party model was never trained on future market history. For every published model result, record its training cutoff, adapter commit, dependency versions, and response file hash separately; mark a model blocked if those cannot be established.
