# Build and verify a TimeF release

TimeF is TimeNet's time-series dataset format. Neblima uses the official
writer and reader from TimeNet 0.12.0 in a separate environment. The
[upstream lock](../configs/upstream.lock.json) records the exact commit.

## Verify the local pipeline

From the repository root, install both environments once. The first
installation needs internet access. The test target also uses the external
`/usr/bin/time` command to record runtime and peak memory.

```bash
make setup
uv sync --project tools/timenet-smoke --python 3.13.13 --locked
make test-timef-offline
```

The Make target disables uv's network access, runs formatting and static
checks on the tooling, and executes the TimeF tests. Continuous integration
also runs the target in an isolated Linux network namespace. The tests use
synthetic data and local inputs. [Tool reference and smoke tests](../tools/timenet-smoke/README.md)

## Export the Lima benchmark

Start with the verified historical SENAMHI audit, hourly grid, and splits
described in the [dataset card](dataset-cards/lima-pm25-forecast.md). The
example uses the standard local paths.

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked \
  python tools/timenet-smoke/export_benchmark.py \
  --timeline data/curated/senamhi-lima-hourly \
  --splits data/benchmarks/lima-pm25-h24-f6-splits \
  --audit data/curated/senamhi-lima-audit.parquet \
  --registry data/timef --version 0.1.0
```

The exporter verifies intermediate manifests and checksums before writing.
The output is `data/timef/airaware/lima-pm25-forecast/0.1.0/`. Each
`ForecastingTask` has a 24-hour input record and six ordered scalar
targets. Task metadata preserves the window ID, series ID, time origin,
and first future hour. [Export evidence (Spanish)](../tasks/issue-22-plan.md)

## Verify the written release

Open the release with TimeNet's software development kit (SDK), run its
integrity verifier, and read the task count.

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python - <<'PY'
from pathlib import Path

from timenet.reader import TimeFReader

release = Path("data/timef/airaware/lima-pm25-forecast/0.1.0")
with TimeFReader.open(release) as reader:
    reader.verify()
    dataset = reader.read()
    print(f"{len(dataset.tasks):,} forecasting tasks")
PY
```

For the full release, the expected count is 338,892. For a small reader
exercise, run the synthetic pipeline from [Getting started](getting-started.md).
The [pinned upstream API review (Spanish)](timenet-integration.md) documents
the interfaces behind this workflow. Track the upstream contribution in
[TimeNet pull request #796](https://github.com/OpenTSLM/TimeNet/pull/796).
