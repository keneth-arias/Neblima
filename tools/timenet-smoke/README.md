# TimeNet tools and reproducibility checks

This environment pins `timenet` and `timenet-connectors` at commit
`9bd1613019ee61fbc52e02106a1a45990ead7a54`. Its lockfile is separate from
the main Neblima environment. The first installation needs internet
access. See the [TimeNet guide](../../docs/timef.md) for the Lima
benchmark export.

## Build the synthetic hello-world dataset

Run the official connector from the repository root. Both registry
arguments point to the same local folder. The command uses the tools'
locked environment through `--no-isolation` and leaves existing versions
in place. The synthetic connector data use CC BY 4.0.

```bash
uv sync --project tools/timenet-smoke --python 3.13.13 --locked

TIMENET_CACHE="$PWD/data/cache/timenet" \
UV_OFFLINE=true \
uv run --project tools/timenet-smoke --locked timenet-build build \
  timenet/hello-world@1.0.0 \
  --local-registry "$PWD/data/timef" \
  --remote-registry "$PWD/data/timef" \
  --no-isolation
```

## Verify the local build

The software development kit (SDK) can verify the files directly and load
the same release through a local registry. Compare values after both reads.

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python - <<'PY'
from pathlib import Path
import timenet
from timenet.reader import TimeFReader
from timenet.registry import LocalRegistry

registry = Path.cwd() / "data/timef"
release = registry / "timenet/hello-world/1.0.0"
with TimeFReader.open(release) as reader:
    reader.verify()
    dataset = reader.read()
    expected = dataset.records[0].signals[0].to_arrow().slice(0, 8).to_pylist()

client = timenet.TimeNet(sources=[LocalRegistry(registry)])
dataset = client.load("timenet/hello-world", version="1.0.0")
assert dataset.records[0].signals[0].to_arrow().slice(0, 8).to_pylist() == expected
print("Records:", len(dataset.records), "Tasks:", len(dataset.tasks))
PY
```

The recorded November 15, 2026 run verified both reads and matched the
installed revisions via `direct_url.json`. It produced three records,
five signals, and five tasks in 4,478,280 bytes. The run receipt
`data/timef/hello-world-validation.json` records the date, packages,
checks, counts, sizes, and file checksums. The example compares the
values and leaves the historical receipt alone. Git excludes the data
root and the local virtual environment. [Official instructions at the
pinned revision](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/docs/get-started.md)

## Verify an hourly PM2.5 round trip

The synthetic test creates a provisional station record with a
Coordinated Universal Time (UTC) origin and one-hour spacing. It verifies
the TimeF output and compares four Arrow values, including a measured
zero and a null. It also checks double precision, typed units, and
provenance.

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked \
  python tools/timenet-smoke/test_senamhi_timef.py
```

## Export a real SENAMHI sample

With both environments installed and the verified normalized Parquet
available, run the sample export against its original station and start
time.

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked \
  python tools/timenet-smoke/export_senamhi.py \
  --normalized data/normalized/senamhi/senamhi-normalization-20261117-v1 \
  --registry data/timef \
  --station-key 2a0d574b25a5dc8c7f6edda9836225860faaa160763d8bea15d95646794f0bd8 \
  --start 2024-05-01T00:00:00Z --hours 24
```

The converter calls local curation and alignment in the main Neblima
environment to verify the upstream artifacts. It writes
`airaware/senamhi-lima-pm25-sample@0.1.0` with published UTC labels,
the accepted inferred unit, and grid provenance. Interval placement and
individual quality remain unknown. The release carries the SENAMHI
attribution and TimeNet's `ODC-By-1.0` identifier.

The real sample preserved 19 finite values and five conflict nulls.
Two fresh registries passed `TimeFReader.verify()` and `LocalRegistry`
loading and matched on identity, clock, Arrow values, and provenance.
A modified input trace was rejected. The two manifest checksums below
differ because of the TimeNet-generated DuckDB control file.

- `0c457bc4b7452da794c3980c1681e4d3c0d361d0073babf72a38f40929724371`
- `dbb6f2c621c4bde20ee571eb2f2db49800ca15783b91a6e96af8e673c16e9d42`

## Run the offline tests

The following Linux workflow uses the same network isolation as
continuous integration. Install the pinned environments before entering
the namespace. The test target uses the external `/usr/bin/time` command
to record runtime and peak memory.

```bash
uv sync --locked
uv sync --project tools/timenet-smoke --python 3.13.13 --locked
sudo -n --preserve-env=HOME,PATH,UV_CACHE_DIR unshare --net \
  --setuid "$(id -u)" --setgid "$(id -g)" -- make test-timef-offline
```

The end-to-end fixture imports a synthetic 73-row CSV with a zero, a null,
and a conflict. It verifies the original, normalizes, curates, aligns,
builds windows, purges split crossings, and writes TimeF. The SDK checks
values, identities, clock labels, and splits. A changed split artifact
must fail before another release is written. For the focused test and
standard setup, see [Getting started](../../docs/getting-started.md).

## Export historical PM2.5 and PM10 windows

Use the historical release path and a new destination on local disk.

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python \
  tools/timenet-smoke/export_qwen_windows.py "$release" "$salida" --joint
```

The manifest pins the training and validation arrays, their identifiers,
and `scaler.json`. Channel order is `pm25, pm10` in histories and targets.
`origin_hour` counts hours since January 1, 1970, at 00:00 UTC. The scaler
and station-level 95th percentiles come from 268,567 distinct
station-hours in training histories. The arrays retain published
concentrations, including zeros. [Export receipt](../../metadata/ventanas-pm25-pm10-entrenamiento.json)

## Verify paired PM2.5 and PM10 validation

`joint_validation.py` checks the historical arrays, the two trained
states, and independent inference replays. Variant A receives PM2.5 only
and can be reconstructed with the PM10 history masked. Variant B
receives both histories. Each replay must reproduce its model's original
window predictions.

Prepare the two inference inputs from the same validation array, keeping
the original ID order and leaving targets out.

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python - "$matrices" "$historias" <<'PY'
import sys
from pathlib import Path
import numpy as np

matrices, salida = map(Path, sys.argv[1:])
salida.mkdir()
with np.load(matrices / "validation.npz", allow_pickle=False) as datos:
    for vista in ("both", "first"):
        historia = datos["history"]
        if vista == "first":
            historia[:, :, 1] = np.nan
        np.savez(salida / f"{vista}.npz", window_id=datos["window_id"],
                 channels=datos["channels"], history=historia)
PY
```

In the SkyPilot training profile, run inference with `first` for A and
`both` for B. Use the corresponding training folder for `$ajuste`.
`gpu_worker.py` applies the profile's GPU memory budget to inference.
[Pinned training configuration](../../configs/training/lima-pm25-pm10-ajuste-v1.json)

```bash
PYTHONPATH=/opt/forecast/src /opt/conda/bin/python /opt/airaware/gpu_worker.py \
  -m opentslm.forecast_inference \
  --input-view "$vista" --data "$historias/$vista.npz" --scaler "$matrices/scaler.json" \
  --checkpoint "$ajuste/step-00015745" --weights /inputs/qwen/weights --batch 16 \
  --output "$ajuste/replay-validation.npz"
```

From the repository root, compare the original and replay predictions
and write the metrics to a new output directory.

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python \
  tools/timenet-smoke/joint_validation.py "$matrices" "$ajuste_a" "$ajuste_b" \
  "$ajuste_a/replay-validation.npz" "$ajuste_b/replay-validation.npz" "$salida"
```

The verifier checks the final update, state checksums, batch logs, scaler,
and frozen validation concentrations. `paired.parquet` contains paired
errors. `metrics.json` groups results by pollutant, station, horizon, and
high concentration. `freeze.json` pins the two models and verified files.
The input is the historical validation split.

If a shutdown leaves a trailing sequence of NUL bytes after the last
complete JSON event, the verifier records the original file name,
checksum, and byte count in `recovered_log_tails`. An incomplete or
corrupted JSON line stops verification. Every step must be documented.
Batches replayed after resumption must preserve their IDs and learning
rate.

## Export PM2.5 histories for inference

Prepare an input file with `window_id` and `history` outside the inference
pod. The exporter verifies the benchmark manifest and preserves the
cohort order.

```sh
uv run --project tools/timenet-smoke --locked python tools/timenet-smoke/export_qwen_windows.py \
  data/timef/airaware/lima-pm25-forecast/0.1.0 history.npz --split validation --history-only
```

The historical exporter verifies targets during preparation. Mount only
the resulting history file for inference and keep the future observations
with the evaluator. Live pilot bundles also require evidence of when
each reading arrived. [Episode forecast plan (Spanish)](../../tasks/pronostico-episodios-lima.md)
