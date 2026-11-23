# Dataset design

Neblima starts with measured particulate matter in Lima. The
[Lima PM2.5 dataset card](dataset-cards/lima-pm25-forecast.md) documents
the completed benchmark. Additional coverage, including Callao and
other parts of Peru, depends on compatible sources and verified data
rights.

## Select a source

Use the [source catalog](sources.md) to compare SENAMHI, OEFA, OpenAQ,
and resources from Peru's national open data portal. Verify the
resource URL, access requirements, coverage, measurement method, and
redistribution rights before importing data. Preserve source-specific
identities and document which evidence supports combining series.

## Preserve and normalize observations

Keep source bytes intact and record acquisition parameters, time in
Coordinated Universal Time (UTC), and the SHA-256 checksum. Preserve
original time fields and interpret them only with documented evidence.
Use `America/Lima` for local calendar operations when appropriate.

Record the station coordinates, pollutant, unit, averaging period,
method, and flags when available. Keep missing observations missing
and document any rules for negatives, detection limits, or unit
conversions. [Observation contract](methodology/observation-contract.md)

## Measure quality and evaluate forecasts

Measure coverage, gaps, duplicates, and conflicts by station,
pollutant, time, and averaging period. Retain provenance when resolving
conflicts. Split data chronologically and fit preprocessing using
training data. Use validation to choose configurations and reserve
test targets for final scoring.

Compare against persistence and seasonal baselines. Report mean
absolute error (MAE) and root mean squared error (RMSE) where supported,
with counts by station, pollutant, and horizon. [Benchmark
results](evaluation.md)

## Prepare a TimeF release

Map sources, signals, time axes, metadata, and tasks to the pinned
TimeNet application programming interface (API). A release needs
documented rights, reproducible acquisition, traceable processing,
measured quality, fixed time splits, and a verified build. The legacy
CSV is a column template. Generate the release with the official
TimeNet tools and follow the work plan's authorization for upstream
contributions. [TimeF export guide](timef.md) ·
[Work plan (Spanish)](../tasks/plan.md)
