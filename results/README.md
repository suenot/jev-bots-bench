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
Checkpoint manifests under `../adapters/` list the local model files expected
by the three published adapters, including tokenizers and configuration. The
current setup scripts check every listed file for reproduction; the publication
verifier pins the manifests themselves and Nico's npm lockfile. These full-file
manifests were recorded after the initial inference runs and checked against
the retained server copies. The earlier setup checks covered source archives
and, where applicable, weight files, so the manifests are a retrospective
reproducibility record rather than a pre-inference commitment for auxiliary
files.

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

## Nico option-order diagnostic

The pinned `nico-martin/open-jev` adapter chose `up` on all 1,382 requests.
Its long/cash policy therefore equals the always-long hold baseline for every
pair and period. The recorded `up` probabilities vary (about 0.538 to 0.706),
but this is not evidence of directional forecasting skill. We reviewed the
upstream label mapping: the option order is preserved through encoding,
inference and the named output probabilities. A fresh run of event `e000001`
with the canonical options `["up", "down"]` reproduced `up` with probability
0.6171370202. Keeping the event, model and option text fixed but reversing
the options to `["down", "up"]` returned `down` with probability 0.6154262652.
This one-event control demonstrates sensitivity to option order. It does not
establish what all 1,382 reversed-order predictions would be. The published
canonical stream and its trading rule were not changed after this inspection.
Run the [one-event probe](../scripts/probe_nico_option_order.mjs) with the
pinned runtime and model as described in
[`../adapters/nico_open_jev.md`](../adapters/nico_open_jev.md#option-order-control).
