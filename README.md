# Jev Bots Bench

Public, reproducible comparison of 16 open-source typed-decision engines from
[the source inventory](https://www.suenot.com/blog/jev-open-source-alternatives/)
when they are plugged into **one fixed long/cash trading policy**. These projects
are decision engines and research tools, not sixteen ready-made trading bots.
The [live dashboard](https://jev-bots-bench.marketmaker.cc/) separates measured
results from pending, blocked, and incompatible projects.

## Source and results

- [`benchmark/models.json`](benchmark/models.json): all 16 upstream source URLs,
  full pinned code commits, and distinct model-weight revisions where known.
- [`benchmark/run.py`](benchmark/run.py) and
  [`benchmark/README.md`](benchmark/README.md): causal market preparation,
  replay, baselines, validation, and exact server-side commands.
- [`data/weekly-v1/`](data/weekly-v1/COMMITMENT.md): 1,382 committed model inputs,
  pair coverage, and the pre-inference hash of sealed outcomes.
- [`adapters/`](adapters/): engine-specific JSONL adapters, pinned dependencies,
  and setup instructions. An adapter is measured only after a real model run.
- [`results/summary.json`](results/summary.json): public aggregate data used by
  the dashboard. Empty results are explicitly labeled; no synthetic P&L is shown.
- [`site/`](site/): source of the dashboard.

The market data stays on the machine running the benchmark. `prepare` reads
one-minute Parquet candles from a local warehouse path (`--root`), writes a
small model-facing JSONL with only historical relative returns and volatility,
and keeps timestamps, pair names, and future outcomes in a separate settlement
file. The default nine pairs cover February 2023 through February 2026 where
complete historical windows exist. A closed Sunday candle can influence a
Monday decision; the earliest modeled fill is Monday 01:00 UTC. Every pair has
its own portfolio. A complete method and known limits are in the benchmark
README.

The legacy price series is a Binance USDT perpetual-futures proxy. Funding,
venue spread, real fills, and model training-data cutoff are not recovered from
these candles. A historical replay using a model released later is diagnostic,
not a live or truly point-in-time investment result. The harness checks that
its *inputs* never contain a future candle; that does not certify what a
third-party model saw during training.

## Repeat a run

```sh
git clone https://github.com/suenot/jev-bots-bench.git
cd jev-bots-bench
python3 -m unittest discover -s benchmark/tests -v
python3 benchmark/run.py prepare --root /path/to/warehouse \
  --events /path/to/work/events.jsonl \
  --settlements /path/to/work/settlements.jsonl \
  --coverage /path/to/work/coverage.json
python3 benchmark/run.py audit \
  --events /path/to/work/events.jsonl \
  --settlements /path/to/work/settlements.jsonl
```

Use the model-specific setup in [`adapters/README.md`](adapters/README.md),
then run `invoke` and `evaluate` exactly as shown in
[`benchmark/README.md`](benchmark/README.md). `prepare` requires `pyarrow`;
the unit tests and replay use the Python standard library. Do not commit raw
warehouse files, private credentials, or large model checkpoints.

## Previous trading-bot study

The earlier [Jev trading-bot review](https://marketmaker.cc/ru/blog/post/jev-bots-three-year-profitability/)
examined 28 different trading projects. Its bot-level backtests and the present
decision-engine comparison answer different questions; their P&L figures should
not be ranked against one another. The upstream bot sources are linked from
that review and the public [pinned research catalog and replay code](https://github.com/suenot/jev-trading-bots-research).

This repository's own code is MIT-licensed. Linked upstream projects and model
weights retain their individual licenses and access terms.
