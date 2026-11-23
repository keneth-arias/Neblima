# Verify one training step on Lima PM2.5

This experiment verified one AdamW update on an RTX 5070 Ti with the
Qwen3.5-0.8B text decoder, temporal projector, and regression head
from the OpenTSLM fork. Qwen's published weights use Apache-2.0,
the fork uses MIT, and Neblima's integration uses AGPL-3.0-only.
SENAMHI data retain their source terms. [OpenTSLM
adapter](https://github.com/keneth-arias/OpenTSLM/pull/1) ·
[Model revision](https://huggingface.co/Qwen/Qwen3.5-0.8B/tree/2fc06364715b967f1860aea9cf38778875588b17) ·
[Data attribution](../DATA_ATTRIBUTION.md)

## Input and result

The probe uses the first training task in the frozen benchmark. It
checks the release manifest against the expected SHA-256, calls
`TimeFReader.verify()`, and checks the series, provisional station,
unit, hourly axis, and input-target boundary. The input has 24 measured
values through January 2, 2015, at 04:00 UTC. Targets run from 05:00
to 10:00 UTC on the same day. [Baseline report
(Spanish)](../reports/baselines/lima-pm25.md)

The probe calculates the mean and population standard deviation on
the history. For zero standard deviation, it uses a scale of one.
It applies the history-based transform to the targets for mean
squared error. The decoder receives the history and mask. The receipt
keeps the predictions before the update and the original targets in
µg/m³.

One example, one newly initialized regression head, and one update
in 32-bit precision produced a normalized loss of 0.6275. The
largest absolute change in the inspected decoder weight and head was
about 0.0001. PyTorch reported peak allocated memory of 8.46 GiB.
One prediction was negative before the update. The probe verifies
the training path. The [evaluation guide](evaluation.md) reports
accuracy against baselines. [Execution receipt](../metadata/qwen-smoke.json)

## Reproduce the probe

Install the TimeNet environment and prepare the frozen release. Use
a local OpenTSLM checkout at the pinned fork revision with its model
weights already cached. Run from the Neblima root and set `fork`
to the path to your checkout. [Upstream pins](../configs/upstream.lock.json) ·
[Adapter environment setup](https://github.com/keneth-arias/OpenTSLM/blob/20573a0f67f0f53bcd7d06a28869379e80d2d652/environments/forecast/README.md)

```bash
uv sync --project tools/timenet-smoke --locked
fork=/path/to/OpenTSLM
PYTHONPATH="$fork/src" uv run --offline --locked --project "$fork/environments/forecast" \
  python tools/training/qwen_smoke.py \
  --release data/timef/airaware/lima-pm25-forecast/0.1.0
```

The JSON receipt includes the TimeF, split, grid, and training
environment checksums alongside its leakage checks. The probe discards
the updated weights. Tests without a graphics processing unit verify
that changing synthetic targets leaves the history and mask identical.
