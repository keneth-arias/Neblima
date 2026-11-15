# Dataset plan

## Scope
Start with Lima, Peru. Prioritize PM2.5 and PM10 if available. Confirm stations, date range, sampling interval, and prediction horizon after reviewing coverage.

## Source discovery
Investigate SENAMHI, Peru's national open data portal, and OpenAQ. These are candidate sources, not verified integrations. Record official endpoints, access requirements, coverage, and redistribution rights in the source inventory before importing anything.

## Collection and normalization
- Preserve original files and record query parameters, retrieval time in UTC, and SHA-256 checksums.
- Retain source timestamps and timezone; normalize timestamps to UTC and use America/Lima for local calendar features.
- Record station coordinates, pollutant, unit, averaging period, measurement method, and source quality flags.
- Keep missing values missing. Document negative values, detection limits, and unit conversions; retain originals.
- Treat the observation CSV as an internal column template, not a validated TimeNet format.

## Quality and evaluation
Report coverage, missingness, duplicate station/pollutant/timestamp/averaging-period keys, gaps, and quality flags. Resolve conflicting duplicates with provenance. Use chronological train/validation/test splits and fit preprocessing only on training data. Compare forecasts with persistence and seasonal baselines; report MAE and RMSE by station, pollutant, and horizon.

## TimeNet delivery
Check the current official data model and connector documentation before implementing. Map sources, signals, time axes, metadata, and task annotations; validate a local TimeNet build and contribute the dataset through a PR. The CSV template alone is not a TimeNet dataset.

## First dataset acceptance
Confirmed source rights, reproducible collection instructions, provenance, a quality report, chronological split definitions, and a validated TimeNet build.
