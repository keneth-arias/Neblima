# Profile local source files

The profiler measures structure, coverage, and missingness in original
files that you already acquired. It produces diagnostic views before
normalization and benchmark selection. [Measured results
(Spanish)](../reports/profiling.md)

## Run the profiler

From the repository root, after `make setup`, run the following commands
with your local originals and acquisition manifests.

```bash
uv run --locked airaware profile run --config configs/profiling.json
uv run --locked airaware profile run --source senamhi-lima-csv
```

Set `AIRAWARE_DATA_DIR` when your `raw/` folder is outside the default data
root. Keep the acquisition structure intact. The command runs offline.
An unknown source fails before processing. If a selected source fails,
the output records it in `errors`, the other sources can finish, and the
command exits with status 1.

Each run writes a new folder under `reports/generated/profiling/`. The
profiler checks checksums, columns, delimiters, and expected row counts.
Before publishing, it verifies the original again. Failure cleans up
only the current run's temporary files.

DuckDB reads strings, keeps empty fields and markers, rejects malformed
rows, and writes Parquet with Zstandard compression. It uses two threads,
a 768 MB working memory setting, a 10 GB temporary-storage limit, and
disabled automatic extensions. The process may use more memory than the
DuckDB setting. The environment pins DuckDB in [`uv.lock`](../uv.lock).

## Inspect the output

Use the source checksum and algorithm in each Parquet file to identify
its inputs. Metrics are deterministic for the same inputs and software
versions. Execution time and output folder name can vary.

| File | Unit of analysis | Content |
| --- | --- | --- |
| `datasets.parquet` | Source | Rows, columns, exact repeats, station groups, dates, and clock states. |
| `stations.parquet` | Provisional station group | Original name and context, rows, series, dates, and parsed clocks. |
| `signals.parquet` | Signal within a context | Cells, distributions, conflicts, gaps, and constants. |
| `tokens.parquet` | Raw token within a context and dimension | Marker and invalid numeric tokens, unparseable dates, and clocks. |
| `manifest.json` | Source run | Input, algorithm, DuckDB version, runtime, and output checksums. |

Provisional identity groups original names, coordinates, altitude, and
location text. OEFA also uses zone and datum. Its `series_context` lists
the assessment, averaging period, unit, analysis type, sample type, and
origin. SENAMHI uses an empty context array. A station can have multiple
contexts. The profiler keeps units and signal contexts separate.

The signal denominator is every row in the context. The exclusive
counts `finite_count`, `empty_count`, `marker_count`,
`invalid_numeric_count`, and `nonfinite_count` sum to `rows`. A marker
in a wide OEFA file can mean the signal was outside that row's analysis.
The profiler preserves literal tokens and recognizes `-`, `NA`, `N/A`,
`ND`, `NAN`, and `NULL` after trimming for classification. Empty cells
remain empty and decimal commas retain their original representation.

## Interpret clock and quality diagnostics

The profiler parses the original clock syntax. SENAMHI dates have eight
digits and its times have up to six digits. OEFA accepts an ISO date and
an `HH:MM:SS` clock, optionally prefixed with the spreadsheet date
December 30 or 31, 1899. A standalone spreadsheet date doesn't establish
midnight. Date extrema include valid dates without a parsed clock. Clock
extrema describe the parsed subset and do not establish UTC coverage.

`unparsed_start_rows` is partitioned in order into unparseable dates,
missing clocks, and unsupported clocks. Token dimensions `start_date`,
`start_clock`, and `signal` are separate views. Don't add their counts
as distinct source rows.

`exact_duplicate_rows` counts extra decoded rows with identical fields.
`duplicate_extra_rows` counts repeated series, start, and end groups
with a parseable start. `conflict_slots` counts groups with more than
one distinct finite value. These counts leave all original rows intact.

Hourly metrics require the exact period `1 hora`, a finite value, an
aligned start, and an unambiguous interval. `expected_hour_slots` spans
the first through last admissible value, inclusive. `missing_hour_slots`
subtracts distinct admissible hours, and `longest_gap_hours` measures
the largest internal gap. Without an admissible value, these metrics
stay null. Constant streaks end at gaps or conflicts.

Numeric summaries include finite zeros, negatives, and repeats.
`is_constant` is null without finite values. `extreme_count` applies
the exploratory bounds Q1 − 3 × IQR and Q3 + 3 × IQR, where IQR is the
interquartile range. These flags describe distributions and have no role
in regulatory thresholds, model fitting, or imputation. [Comparison
methods](comparison.md) · [Source limitations](sources.md)
