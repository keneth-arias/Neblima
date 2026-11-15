# AirAware

Air quality time-series data for Lima and Peru, for the [TimeNet hackathon](https://challenge.timenet.ai/).

## Goal
Collect traceable air quality observations, prepare a reproducible dataset, and evaluate air quality forecasts. Start with Lima and expand to other Peruvian cities when coverage and data rights allow.

## Layout
- `data/raw/`: original downloads, excluded from Git.
- `data/processed/`: dataset outputs, excluded from Git.
- `metadata/sources.csv`: source inventory and licensing review.
- `metadata/observations.csv`: proposed internal observation column template, not a TimeNet export.
- `docs/dataset-plan.md`: collection and quality plan.
- `docs/hackathon.md`: submission checklist.
- `notebooks/`: exploratory analyses.

No data has been collected yet; collectors and a TimeNet connector remain to be implemented. Source licenses must be checked before redistribution. This scaffold does not assert a dataset license.

## Start here
Inventory sources, confirm rights, then select a Lima station, pollutant, and date range. Preserve original downloads with retrieval times, request parameters, and SHA-256 checksums before normalization. Keep credentials in local environment variables; never commit them.

## Project tasks
Follow the [implementation plan](tasks/plan.md), the [GitHub Project](https://github.com/users/keneth-arias/projects/1), and [GitHub issues](https://github.com/keneth-arias/airaware/issues). The [initial project brief](docs/initial-plan.md) preserves the complete research scope. Proposed pipeline commands in that brief remain tasks to implement.
