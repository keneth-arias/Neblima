# Compare sources and forecast coverage

The local comparison measures how many hourly forecast windows each source
can support. The current `comparison-v3` policy accepts historical Lima
PM2.5 from the selected SENAMHI original for retrospective evaluation using
published UTC labels. Reading quality and interval placement remain
unknown. Daily regulatory labels require further evidence. [Source policy
(Spanish)](decisions/005-senamhi-operating-policy.md)

## Run the comparison

From the repository root, with the authorized originals and manifests
available locally, run the comparison.

```bash
uv run --locked airaware compare run
```

The defaults use [`configs/benchmark.yaml`](../configs/benchmark.yaml) and
[`configs/profiling.json`](../configs/profiling.json). Use `--policy`,
`--inputs`, and `--output-root` to override the paths. Each configuration
file can be up to 64 KiB. Set `AIRAWARE_DATA_DIR` to use a different data
root. The command works offline and exits with status 1 if it can't
verify or process the inputs.

The comparison preserves provisional identities, source contexts, and
native clock labels. Each origin uses consecutive finite hourly values
for its history and future targets. The scenarios pair 24, 48, 72, or 168
history hours with 6, 12, 24, or 48 future hours. Lima means Lima Province
in the Lima Department. PM10 and Callao use separate scenarios.

## Read the counts

Rows fall into mutually exclusive categories in this order. They can
be outside scope, have a nonhourly period, have an unparseable or unaligned
clock, lack a finite value, have an ambiguous interval, or be accepted.
Accepted rows minus consolidated repetitions give the unique points in
the diagnostic view. Simultaneous coverage counts distinct stations at
one timestamp, which can include stations without a complete forecast
window at that origin.

Candidate origins sit between the first and last admissible points and
leave room for the full history and target interval. The report separates
incomplete histories, complete histories with incomplete targets, and
complete windows. Runs of consecutive hours provide counts without
imputation. Contexts and stations stay separate. Numeric magnitude alone
doesn't exclude a reading.

`forecasting-readiness.parquet` records source and policy checksums,
identity, scenario, counts, clock limits, and blockers. Structural
coverage can be measured while `scientific_valid_windows` remains null.
The [dataset card](dataset-cards/lima-pm25-forecast.md) documents how the
selected source proceeds to actual windows and split manifests.

## Understand policy versions

The current policy follows the change introduced by `comparison-v2`.
It reports observed windows, stations, coverage runs, and losses without
a fixed station quota or minimum consecutive months. The historical
`comparison-v1` remains readable for reproducibility. Keep historical
results and their configuration hashes together. The v2 report keeps
`components`, `scientific_score`, and `sensitivity_equal` null and uses
`quorum_stations=1` for simultaneous file coverage.

## Inspect the artifacts

`source-overlap.parquet` counts shared timestamps on the original clocks
by signal and geography. The diagnostic doesn't match stations across
providers. Scientific overlap remains unknown until clock compatibility is
verified. Missing timestamps can produce zero diagnostic overlap even
when observations existed.

Each run publishes two Parquet files, `summary.json`, and `manifest.json`
to a new folder under `reports/generated/comparison/`. The workflow
verifies originals before and after processing and before publication.
It publishes the artifacts together by rename. A failure removes only
the current run's temporary files. DuckDB uses two threads, a 768 MB
working memory setting, a 10 GB temporary-storage limit, and disabled
automatic extensions. The process can use more memory than DuckDB's
setting.

Document each source's blockers in the configuration, even if review
produces an empty list. Record the evidence for changes to units, clocks,
quality, or rights. [Comparison report
(Spanish)](../reports/dataset-comparison.md) · [Initial benchmark selection
(Spanish)](../reports/benchmark-selection.md)
