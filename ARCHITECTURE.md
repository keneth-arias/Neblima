# Neblima architecture

Neblima turns source files into auditable hourly forecasts. The core uses local
files, the `airaware` Python package, and a separate TimeNet environment. The
[public demo](https://neblima.orbitly.lat/) presents a station snapshot and
retrospective results.

## Data flow

Each stage has a local input and output. Acquisition is the network boundary.
The core preparation stages operate on the files and metadata already on disk.

| Stage | Inputs and outputs |
| --- | --- |
| Discover | Validate the resources and evidence in `configs/sources.yaml` with `airaware catalog validate`. |
| Acquire | Import authorized local files or retrieve explicit public resources through `airaware acquire`. Store original bytes under `raw/` and record their origin and SHA-256 checksum. |
| Profile and compare | Use DuckDB to inspect coverage, units, raw tokens, and missingness. Compare candidate series before choosing the initial source. |
| Normalize | Read the original and its manifest. Write Parquet observations with preserved raw fields, interpreted values where justified, and row-level provenance. |
| Curate and align | Apply the historical SENAMHI policy, retain links to exact duplicates, flag conflicts, and build an hourly grid that distinguishes missing values from missing rows. |
| Build the benchmark | Keep complete histories and targets. Use fixed chronological cutoffs and purge any window that crosses a split boundary. |
| Export and evaluate | Write and verify a TimeF release with TimeNet. Compare predictions against identical targets and select models using validation. |
| Publish a demo snapshot | Prepare recent provider-chart readings and six point forecasts for eligible histories. The web renderer consumes a small JSON snapshot. |

The [dataset card](docs/dataset-cards/lima-pm25-forecast.md) records the
selected original, split boundaries, and counts. The [evaluation
guide](docs/evaluation.md) explains the comparisons. Optional weather
alignment has a separate input and availability contract. [Weather alignment
report (Spanish)](reports/alignment/weather-gfs-union-real-20261120.md)

## Where the implementation lives

The main workspace creates `raw/`, `staging/`, `normalized/`, `curated/`,
`benchmarks/`, and `timef/` under `data/`. Commands that accept
`AIRAWARE_DATA_DIR` can use a separate data root. Generated datasets and
model weights belong in local storage.

| Path | Responsibility |
| --- | --- |
| [`src/airaware/`](src/airaware/) | Command-line interface, catalog and observation schemas, acquisition, profiling, curation, hourly alignment, and benchmark logic. |
| [`configs/`](configs/) | Source catalog, acquisition specifications, normalization policies, benchmark options, and upstream revision pins. |
| [`tools/timenet-smoke/`](tools/timenet-smoke/) | Isolated TimeNet environment, exporters, evaluation scripts, and reproducibility tests. |
| [`tools/training/`](tools/training/) | Model probes, evaluation helpers, and plotting scripts. |
| [`tools/web-refresh/`](tools/web-refresh/) | Capture, prediction, correction, and export of a public web snapshot. |
| [`web/`](web/) | Standalone historical station map. |
| [`metadata/`](metadata/) and [`reports/`](reports/) | Versioned acquisition receipts, run summaries, benchmark metrics, and evidence. The legacy CSVs are column templates. |

## Interfaces and invariants

The [observation contract](docs/methodology/observation-contract.md) defines
raw values, missingness, time, units, and provenance. Preserve a measured zero
as zero. Keep publication time unknown until evidence establishes it. Historical
SENAMHI files and recent charts use different time metadata, as described in
the [dataset card](docs/dataset-cards/lima-pm25-forecast.md) and
[demo guide](docs/demo.md).

The [upstream lock](configs/upstream.lock.json) records the inspected TimeNet
and OpenTSLM revisions. TimeNet 0.12.0 runs in its own locked environment.
The [TimeNet guide](docs/timef.md) shows how to build and verify a local
release with the official reader. Source data and the software that processes
it have separate terms. [Data attribution](DATA_ATTRIBUTION.md) ·
[Licensing decision (Spanish)](docs/decisions/003-licencia-agpl-v3.md)
