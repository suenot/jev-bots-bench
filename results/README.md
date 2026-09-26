# Published benchmark results

`summary.json` powers the public site. Every measured model has one complete
`responses/<model-id>.jsonl` stream in the same order as
`../data/weekly-v1/events.jsonl`: 1,382 decisions. The sealed
`../data/weekly-v1/settlements.jsonl` has 1,381 outcomes because one scheduled
fill is missing. A missing outcome is excluded for every policy; the model
request remains in the response stream.

`model-provenance.json` names the exact upstream source and weight revisions,
checksums of transferred source archives and weight files, adapter checksum,
dependency environment, response checksum and model training cutoff when
known. The source and weight archives are large and stay outside this Git
repository. The small dependency environment records are in `environments/`.

To verify the published result without the raw minute candles:

```sh
git clone https://github.com/suenot/jev-bots-bench.git
cd jev-bots-bench
python3 scripts/verify_published.py
```

The verifier checks hashes of files published in this repository and response
counts, evaluates the committed model responses against the committed
settlement file, and compares every published aggregate metric. Source archives
and model weights are too large for this repository; their listed hashes must
be checked separately when obtaining those artifacts. To regenerate events and
settlements from raw Parquet candles, follow `../benchmark/README.md`. The
earlier commitment to the settlement hash is in
`../data/weekly-v1/COMMITMENT.md` and its Git history.

These checks establish that the posted table follows the posted inputs,
responses and calculation code. They cannot establish that a model released
after the historical period was never trained on that period. Unknown training
cutoffs remain marked unknown, and such results are retrospective diagnostics.
