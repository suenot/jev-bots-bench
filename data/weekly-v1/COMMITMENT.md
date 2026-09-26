# Weekly benchmark input commitment

The model-facing requests in `events.jsonl` were prepared on 2026-09-26 from
the existing warehouse, before running any of the sixteen candidate engines.
The request stream contains 1,382 opaque IDs and causal feature text. The
paired settlement file has 1,381 scorable rows. It is kept separate during
inference and will be published with the final results so anyone can check
these hashes and replay the exact evaluation.

| Artifact | SHA-256 |
| --- | --- |
| `events.jsonl` | `d17d4fb3bfcacd898e0a81a07ed704d598f931fc4db9ff683ba649646fdbbecc` |
| `settlements.jsonl` | `888eccbc7c999a606436559425966f459901d222f81a9af1bf3010db9294b0a6` |
| `coverage.json` | `8c3fc4541be7e2bf9aae5ea43bd4b1a6691065bd80df76e5ee18974b13058d49` |
| `benchmark/run.py` on server1 | `1e20a30540e8e4a20fa133f677b22d4380b26dd7bc57c5bed390dcdaeb00d0e0` |

This supersedes the settlement hash `85277838f76a88b0958881604e24f4c91120f377802075b6fa362fdd58507e05`
from the first commit. An audit found that the first runner required complete
future daily candles for a week even though only its scheduled entry and exit
minute opens are needed. The corrected rule adds one scorable ETH week and
does not alter any model-facing request: the event hash is identical. The
original runner hash was
`a323007554441ac4301ed45ed41e10431824c5e1b721db31ba0f25ded4235de9`.
We made this correction before evaluating or publishing any model P&L. Both
commit versions remain in Git history for review.

Inputs: legacy Binance USDT perpetual-futures minute candles in the server1
warehouse, from February 2023 through February 2026, for BTC, ETH, SOL, BNB,
LINK, DOT, TRX, BCH, and UNI. The market data archive itself was not copied to
the repository or to the author's laptop. `coverage.json` records valid and
excluded weeks for each pair. The [benchmark instructions](../../benchmark/README.md)
show the preparation and replay commands.

Publishing the settlement hash before model outputs prevents changing the
labels or fill prices in response to a model result. The commit does not prove
that a model trained later never saw market history during pretraining.
