# CPU classification adapters

`gliner_decide.py`, `laya_decide.py`, and `gliformer_decide.py` each accept one
UTF-8 JSON object per line on stdin:

```json
{"id":"opaque-event-id","state":"Causal weekly market features, without dates or absolute prices."}
```

Each emits the same `id`, `prediction` (`up` or `down`), `probabilities`
(`up` and `down`), `latency_ms` for model inference, `source`, `model`, and
`model_revision`. It also emits `prob_up` and a binary long/cash
`target_weight` for the benchmark runner. A tie maps to `down`, matching the
benchmark's strict positive-return definition of `up`. The model loads once
and handles subsequent lines in the same process. Diagnostics go to stderr.

## GLiNER2.5-Decide

The source library is pinned to
[`55656fbfa01d3d4a77485e1a1eeeaf682990ccdf`](https://github.com/fastino-ai/GLiNER2/tree/55656fbfa01d3d4a77485e1a1eeeaf682990ccdf),
and the public Apache-2.0 checkpoint is pinned to
[`7ee5da4c2415e32259bcdc0b1a7367c32ce8d6f6`](https://huggingface.co/fastino/GLiNER2.5-Decide/tree/7ee5da4c2415e32259bcdc0b1a7367c32ce8d6f6).
The `Classifier` interface exposes both class probabilities; the simpler
`AutoExtractor.classify_text()` examples report only the selected class.

### Install and run on Linux CPU

Use Python 3.11 and a virtual environment. Install the CPU PyTorch wheel from
the official index, then the pinned direct dependencies. The first adapter run
downloads the pinned model to the Hugging Face cache; allow space for its
checkpoint and keep that cache for repeated runs.

```sh
python3.11 -m venv .venv-gliner
.venv-gliner/bin/python -m pip install --upgrade pip
.venv-gliner/bin/python -m pip install 'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
.venv-gliner/bin/python -m pip install -r adapters/requirements-gliner-decide.txt
.venv-gliner/bin/python adapters/gliner_decide.py < events.jsonl > decisions.jsonl
```

The state text must describe only information available at the decision time.
Do not include realized future returns. This model is a general classifier,
not a model trained to forecast crypto prices; its scores are benchmark inputs,
not evidence of predictive skill until the held-out replay is measured.

## Laya

The [source library](https://github.com/NandhaKishorM/laya/tree/4066d5d5fbf08b66c6757ddeedbd797bd7655bc0)
and [English checkpoint](https://huggingface.co/convaiinnovations/laya/tree/55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851)
are pinned. Both are Apache-2.0. The direct Python SDK loads one model on CPU
and returns the full `choice` distribution. All three adapters use the same
`next_7_day_price_direction` task and `up`/`down` labels. Laya rounds its
reported probabilities to four decimals; the adapter renormalizes them to
sum to one. Its published confidence metrics are not crypto forecasting
calibration.

```sh
python3.11 -m venv .venv-laya
.venv-laya/bin/python -m pip install --upgrade pip
.venv-laya/bin/python -m pip install 'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
.venv-laya/bin/python -m pip install -r adapters/requirements-laya-decide.txt
python3 adapters/smoke_laya_mock.py
.venv-laya/bin/python adapters/laya_decide.py < events.jsonl > decisions-laya.jsonl
```

## GLiFormer large-v1

The [source library](https://github.com/Knowledgator/GLiFormer/tree/b5c0a0fd2aacff64736fbfa0bac0bdcc032d5eff)
and [checkpoint](https://huggingface.co/knowledgator/gliformer-large-v1/tree/d0a4e53d09cebe6bc963dd9be319d4279084bb2d)
are pinned and Apache-2.0. The adapter runs the documented Python classifier
on CPU. GLiFormer's classifier independently applies sigmoid to each class
logit. Its scores can both be high or both be low. The adapter requests both
scores and divides each by their sum to match the benchmark's binary JSONL
contract. `probability_semantics` records this transformation. These values
are **not a calibrated exclusive-class distribution**, so interpret Brier
scores and reliability plots separately from the native Laya and GLiNER
outputs.

```sh
python3.11 -m venv .venv-gliformer
.venv-gliformer/bin/python -m pip install --upgrade pip
.venv-gliformer/bin/python -m pip install 'torch==2.8.0+cpu' --index-url https://download.pytorch.org/whl/cpu
.venv-gliformer/bin/python -m pip install -r adapters/requirements-gliformer-decide.txt
python3 adapters/smoke_gliformer_mock.py
.venv-gliformer/bin/python adapters/gliformer_decide.py < events.jsonl > decisions-gliformer.jsonl
```
