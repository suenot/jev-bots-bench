# Weekly benchmark input commitment

The model-facing requests in `events.jsonl` were prepared on 2026-09-26 from
the existing warehouse, before running any of the sixteen candidate engines.
The request stream contains 1,382 opaque IDs and causal feature text. The
paired settlement file has 1,380 scorable rows. It is kept separate during
inference and will be published with the final results so anyone can check
these hashes and replay the exact evaluation.

| Artifact | SHA-256 |
| --- | --- |
| `events.jsonl` | `d17d4fb3bfcacd898e0a81a07ed704d598f931fc4db9ff683ba649646fdbbecc` |
| `settlements.jsonl` | `85277838f76a88b0958881604e24f4c91120f377802075b6fa362fdd58507e05` |
| `coverage.json` | `226de57c15849b8ced64741d027f6f7462e607796a3c5fd4373abf9a21c8d766` |
| `benchmark/run.py` on server1 | `a323007554441ac4301ed45ed41e10431824c5e1b721db31ba0f25ded4235de9` |

Inputs: legacy Binance USDT perpetual-futures minute candles in the server1
warehouse, from February 2023 through February 2026, for BTC, ETH, SOL, BNB,
LINK, DOT, TRX, BCH, and UNI. The market data archive itself was not copied to
the repository or to the author's laptop. `coverage.json` records valid and
excluded weeks for each pair. The [benchmark instructions](../../benchmark/README.md)
show the preparation and replay commands.

Publishing the settlement hash before model outputs prevents changing the
labels or fill prices in response to a model result. The commit does not prove
that a model trained later never saw market history during pretraining.
