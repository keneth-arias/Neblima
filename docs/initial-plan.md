# AirAware Perú: Environmental Time-Series Dataset Engineering

## 1. Role and objective

Act as a senior data engineer, environmental data scientist, ML platform engineer and open-source contributor.

Design and implement a reproducible, resource-efficient data engineering pipeline for AirAware Perú, a temporal AI project participating in the TimeNet Online Hackathon.

Project references:

- Hackathon: https://challenge.timenet.ai/
- TimeNet: https://github.com/OpenTSLM/TimeNet
- OpenTSLM: https://github.com/OpenTSLM/OpenTSLM
- Documentation: https://docs.timenet.ai/

The primary objective is to discover, collect, profile, compare, validate, normalize and integrate publicly available air-quality and complementary environmental time-series datasets covering Lima, Callao and Peru.

The final objective is to produce one or more high-quality, versioned TimeF datasets that can be used to train and fine-tune temporal AI models based on open-weight language models.

The initial use case is forecasting PM2.5 concentrations and high-pollution episodes in metropolitan Lima. The architecture must support future expansion throughout Peru.

Prioritize data quality, scientific validity, reproducibility and licensing over raw dataset size.

## 2. Engineering principles

Follow these principles throughout implementation:

- Open-source software and openly accessible data where possible.
- Reproducible and deterministic data processing.
- Immutable raw source data.
- Explicit data provenance and lineage.
- Idempotent and resumable downloads.
- Incremental ingestion.
- Schema validation and automated quality checks.
- Memory-efficient processing of large datasets.
- Configuration-driven pipelines.
- No unnecessary infrastructure or distributed processing frameworks.
- No temporal leakage between training, validation and test datasets.
- No undocumented data imputation.
- No fabricated observations, station coordinates, timestamps or measurement units.
- No redistribution of data without compatible licensing.
- Prefer simple, maintainable implementations over premature abstractions.

Use English for source code and technical documentation. Preserve original Spanish field names and metadata in raw source artifacts.

## 3. Phase 0: Repository and TimeNet architecture investigation

Before implementing anything:

1. Inspect the current working repository and existing code.
2. Inspect the latest TimeNet repository, documentation, examples, AGENTS.md and CONTRIBUTING.md.
3. Determine the supported Python versions, dependencies and connector interfaces.
4. Inspect existing implementations of BaseConnector, TimeFDataset, Signal, Source, Record, ForecastingTask, ClassificationTask and AnswerTask.
5. Inspect existing connectors such as hello-world and TSQA.
6. Investigate how TimeNet handles missing observations, temporal axes, metadata, annotations, dataset composition, lineage, splits and licensing.
7. Identify existing environmental or meteorological connectors that can be reused.
8. Pin the relevant upstream Git commits and dependency versions.
9. Verify the current hackathon submission requirements.

Do not assume API signatures based on older TimeNet implementations.

Produce:

- `PLAN.md`
- `ARCHITECTURE.md`
- `docs/timenet-integration.md`
- An ordered implementation backlog with dependencies and acceptance criteria.

## 4. Phase 1: Dataset discovery and source inventory

Perform a comprehensive search in Spanish and English for public environmental time-series datasets covering Peru.

Investigate government portals, scientific repositories, international organizations, university research repositories and public APIs.

### Priority 0: Official physical air-quality measurements

| Source | URL |
|---|---|
| SENAMHI Lima air quality | https://www.datosabiertos.gob.pe/dataset/monitoreo-de-los-contaminantes-del-aire-en-lima-metropolitana-servicio-nacional-de |
| SENAMHI Lima CSV | https://www.datosabiertos.gob.pe/dataset/monitoreo-de-los-contaminantes-del-aire-en-lima-metropolitana-servicio-nacional-de-0 |
| SENAMHI data dictionary | https://www.datosabiertos.gob.pe/dataset/monitoreo-de-los-contaminantes-del-aire-en-lima-metropolitana-servicio-nacional-de-1 |
| SENAMHI metadata | https://www.datosabiertos.gob.pe/dataset/monitoreo-de-los-contaminantes-del-aire-en-lima-metropolitana-servicio-nacional-de-2 |
| OEFA national air quality | https://www.datosabiertos.gob.pe/dataset/vigilancia-y-seguimiento-ambiental-en-la-calidad-del-aire-organismo-de-evaluaci%C3%B3n-y |
| OEFA CSV | https://www.datosabiertos.gob.pe/dataset/vigilancia-y-seguimiento-ambiental-en-la-calidad-del-aire-organismo-de-evaluaci%C3%B3n-y-0 |
| OEFA monitoring portal | https://sistemas.oefa.gob.pe/pifa/mfe/ |
| SENAMHI monitoring service | https://www.gob.pe/9433 |
| DIGESA Lima historical data | https://www.digesa.minsa.gob.pe/DCOVI/mapas/DIGESA_AIR_MR_CalidadAireAnual_LIMA.html |
| SENAMHI reports | https://www.gob.pe/institucion/senamhi/colecciones/51679-vigilancia-de-la-calidad-del-aire-en-el-area-metropolitana-de-lima-y-callao |

The government catalogs list approximately 65 MB of SENAMHI observations and 1.23 GB of OEFA observations. Treat these as catalog metadata until actual downloads have been verified.

### Priority 1: Additional observations and processed datasets

| Source | URL |
|---|---|
| OpenAQ Explorer | https://explore.openaq.org/ |
| OpenAQ API v3 | https://docs.openaq.org/ |
| OpenAQ S3 archive | https://registry.opendata.aws/openaq/ |
| OpenAQ archive documentation | https://docs.openaq.org/aws/about |
| World Air Quality Index Peru | https://aqicn.org/country/peru/es/ |
| WAQI historical data | https://aqicn.org/historical/ |
| AirNow International | https://gispub.epa.gov/airnowembassy/ |
| Calidad Aire Lima | https://github.com/Cristhianbgf/calidad-aire-lima |
| Limaair | https://github.com/quishqa/limaair |
| WHO air quality database | https://www.who.int/data/gho/data/themes/air-pollution |
| INEI environmental statistics | https://www1.inei.gob.pe/biblioteca-virtual/boletines/estadisticas-ambientales/ |
| MINAM SINIA | https://sinia.minam.gob.pe/portal/datos-abiertos/ |

Identify whether these sources provide original measurements, duplicated government observations, aggregated statistics, derived measurements or modeled values.

Verify whether AirNow has relevant historical stations in Peru before implementing an integration.

### Priority 2: Meteorological data

| Source | URL |
|---|---|
| SENAMHI hourly meteorology | https://www.datosabiertos.gob.pe/dataset/variables-meteorologicas-de-las-estaciones-autom%C3%A1ticas-de-intercambio-internacional-servicio |
| SENAMHI station network | https://www.senamhi.gob.pe/servicios/?p=estaciones |
| Open-Meteo historical weather | https://open-meteo.com/en/docs/historical-weather-api |
| Open-Meteo historical forecasts | https://open-meteo.com/en/docs/historical-forecast-api |
| ERA5 and ERA5-Land | https://cds.climate.copernicus.eu/ |
| NASA POWER | https://power.larc.nasa.gov/docs/services/api/temporal/hourly/ |
| NOAA Integrated Surface Database | https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database |
| NOAA atmospheric soundings | https://www.ncei.noaa.gov/products/weather-balloon/integrated-global-radiosonde-archive |

Investigate the availability of the following variables:

- Temperature
- Relative humidity
- Dew point
- Atmospheric pressure
- Wind speed and direction
- Precipitation
- Solar radiation
- Cloud cover
- Boundary-layer height
- Atmospheric stability
- Temperature inversions
- Visibility

### Priority 3: Satellite and atmospheric reanalysis

| Source | URL |
|---|---|
| CAMS EAC4 global reanalysis | https://ads.atmosphere.copernicus.eu/datasets/cams-global-reanalysis-eac4 |
| Copernicus Sentinel-5P | https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-5p |
| NASA MODIS MAIAC MCD19A2 | https://www.earthdata.nasa.gov/ |
| ACAG global surface PM2.5 | https://sites.wustl.edu/acag/surface-pm2-5/ |
| Open-Meteo CAMS air quality | https://open-meteo.com/en/docs/air-quality-api |
| Processed Lima CAMS dataset | https://zenodo.org/records/18673925 |
| NASA FIRMS wildfire observations | https://firms.modaps.eosdis.nasa.gov/ |

Treat satellite observations, atmospheric reanalysis and modeled pollutant concentrations as separate data categories. Do not treat them as independent ground-level pollution measurements.

### Priority 4: Additional contextual data

Investigate publicly available historical time-series data for:

- Traffic intensity and mobility.
- Industrial emissions.
- Wildfire events and biomass burning.
- Electricity generation and industrial activity.
- Construction and dust emissions.
- Public holidays and calendar events.
- Land use, elevation and urban morphology.

Include static contextual datasets only when they have a documented relationship to the forecasting problem.

### Dataset catalog requirements

Create a machine-readable `configs/sources.yaml` inventory containing:

- Unique source identifier.
- Dataset name and description.
- Publisher.
- Original catalog URL.
- Resolved download URLs or API endpoints.
- Geography.
- Historical coverage.
- Temporal and spatial resolution.
- Available variables and units.
- Measurement methodology.
- Data category.
- File formats and size.
- Authentication requirements.
- API limits.
- Update frequency.
- License and attribution.
- Redistribution permissions.
- Known limitations.
- Download priority.
- Acquisition status.
- Last verification timestamp.

Use explicit statuses such as discovered, verified, downloaded, profiled, integrated, blocked, duplicate and excluded.

Keep inaccessible sources in the inventory with an explanation instead of silently removing them.

## 5. Phase 2: Data acquisition

Implement a modular acquisition pipeline supporting:

- HTTP and HTTPS file downloads.
- REST APIs.
- Public S3 object storage.
- CSV, compressed CSV, JSON and Parquet.
- XLSX metadata and data dictionaries.
- NetCDF, GRIB and Zarr for scientific datasets, when required.

Start by downloading SENAMHI and OEFA, including all associated documentation.

Resolve actual resource URLs from upstream catalog pages. Do not save HTML error responses as CSV files.

Implement:

- Streaming downloads.
- Bounded concurrency.
- Connection and read timeouts.
- Exponential backoff and retry policies.
- Rate-limit awareness.
- Resume support when available.
- SHA-256 checksums.
- Atomic file writes.
- Content-type and file-format verification.
- Download manifests.
- Local caching.
- Configurable date and geographical filters.
- Optional authentication through environment variables.

For OpenAQ, discover Peruvian location identifiers before downloading archive objects. Do not download the global archive.

For satellite and reanalysis sources, restrict requests to relevant geographical boundaries, station coordinates, variables and historical periods.

Estimate download volume and storage requirements before initiating large acquisitions. Require explicit approval for expensive or unbounded downloads.

Never bypass authentication requirements, provider restrictions or rate limits.

## 6. Phase 3: Raw storage and data lineage

Use a layered storage architecture.

```text
data/
├── raw/
│   ├── senamhi/
│   ├── oefa/
│   ├── digesa/
│   ├── openaq/
│   ├── weather/
│   └── satellite/
├── staging/
├── normalized/
├── curated/
├── benchmarks/
└── timef/
```

### Raw layer

Preserve original downloaded artifacts without modification.

Record source URL, retrieval timestamp, checksum, content length, license and source version.

### Staging layer

Parse source-specific schemas, encodings, field names and timestamps.

Preserve all original fields required to investigate normalization issues.

### Normalized layer

Store validated and standardized observations using partitioned Apache Parquet.

### Curated layer

Contain deduplicated, scientifically compatible and quality-controlled time series.

### Benchmark layer

Contain explicit forecasting tasks, targets, split assignments and reproducible window definitions.

### TimeF layer

Contain the final datasets written through the official TimeNet implementation.

Do not commit bulk data, credentials, generated caches or model checkpoints to Git.

## 7. Phase 4: Exploratory data analysis and source comparison

Profile every acquired dataset before integrating it.

Calculate:

### Dataset-level statistics

- Raw and valid row counts.
- Compressed and uncompressed size.
- Unique monitoring stations.
- Geographic coverage.
- Earliest and latest valid timestamps.
- Number of variables.
- Temporal resolution distribution.
- Total measured station-hours.
- Total unique pollutant measurements.
- Available years and months.
- Schema inconsistencies.

### Station-level statistics

- Coordinates and elevation.
- Administrative location and UBIGEO.
- Available pollutants.
- Station classification and instrumentation, when documented.
- Operational periods.
- Sampling interval.
- Observation completeness by month and year.
- Longest continuous valid sequence.
- Longest missing-data gap.
- Duplicate and conflicting measurements.

### Signal-level statistics

- Missing and invalid observations.
- Negative concentrations.
- Documented sentinel values.
- Minimum, maximum and percentiles.
- Extreme values and outlier candidates.
- Flatline sequences.
- Seasonal and daily patterns.
- Autocorrelation.
- Cross-pollutant correlations.
- Relationships with meteorological variables.
- Pollution-event frequency.

Do not automatically delete extreme pollution events simply because they are statistical outliers.

### Forecasting readiness

For every station and pollutant, calculate valid window counts for:

- Lookback periods of 24, 48, 72 and 168 hours.
- Forecast horizons of 6, 12, 24 and 48 hours.
- Multiple input completeness requirements.
- Fully observed target windows as the default benchmark.

Quantify how many windows remain after each quality rule.

### Cross-source comparison

Compare datasets using the following dimensions:

| Criterion | Proposed weight |
|---|---:|
| Valid measured data completeness | 25% |
| Usable forecasting windows | 20% |
| Historical coverage | 15% |
| Temporal resolution | 10% |
| Geographic and station coverage | 10% |
| Licensing and redistribution | 10% |
| Metadata and provenance quality | 5% |
| Acquisition reliability | 5% |

Use documented scoring formulas based on measured properties. Treat incompatible licensing and unverified measurement semantics as exclusion gates rather than weaknesses that can be offset by a high numerical score.

Rank sources separately for:

1. Primary forecasting labels.
2. Peru-wide temporal pretraining.
3. Meteorological input features.
4. Independent validation.
5. Spatial and satellite enrichment.

Compare overlapping station measurements using aligned time periods, compatible units, documented aggregation methods, bias, MAE, RMSE and correlation.

Distinguish genuinely independent observations from copies of the same original measurement.

Produce:

- `reports/dataset-comparison.md`
- `reports/dataset-profile.parquet`
- `reports/station-coverage.parquet`
- `reports/signal-quality.parquet`
- `reports/source-overlap.parquet`
- `reports/forecasting-readiness.parquet`
- Coverage heatmaps, missing-data plots and station maps.

## 8. Phase 5: Canonical data model

Design a normalized, provider-independent observation schema.

Recommended fields:

```text
observation_id
source_id
source_record_id
source_artifact_sha256
provider_station_id
canonical_station_id
sensor_id
latitude
longitude
altitude_m
department
province
district
ubigeo
parameter
original_parameter
value
unit
original_value
original_unit
timestamp_utc
timestamp_local
interval_start_utc
interval_end_utc
sampling_interval_seconds
aggregation_method
measurement_method
observation_type
quality_flag
is_valid
is_imputed
available_at_utc
forecast_issue_time_utc
source_version
```

Use separate metadata tables for stations, sensors, sources, licenses and station relocations.

Support observation categories including:

- Ground-based measured.
- Derived from physical measurements.
- Satellite observed.
- Atmospheric modeled.
- Reanalysis.
- Forecast.
- Imputed.

Not every source will supply every field. Preserve null values and document unknown semantics rather than inventing metadata.

Use WGS84 coordinates where the upstream coordinate reference system is known. Preserve the original coordinates and CRS.

For OEFA, investigate UTM easting, northing, zone and datum fields before converting coordinates.

Normalize pollutant names and units only when the conversion is scientifically justified. Gas conversions involving mass and volumetric concentrations require documented reference conditions.

## 9. Phase 6: Normalization, deduplication and alignment

Implement deterministic transformations.

- Convert verified local Peruvian timestamps to UTC using `America/Lima`.
- Preserve local timestamps for calendar-based analyses.
- Distinguish observation start times from end times.
- Preserve the original measurement cadence.
- Normalize parameter identifiers.
- Normalize compatible units.
- Interpret documented missing-value codes.
- Detect invalid and conflicting observations.
- Standardize station metadata.
- Detect station relocations and instrumentation changes.
- Match stations across providers using identifiers, coordinates and documented provenance.

Do not assume that nearby stations are equivalent.

For deduplication, distinguish:

- Exact duplicate records.
- Repeated observations distributed by multiple aggregators.
- Conflicting measurements from the same sensor.
- Independent measurements from different sensors at the same location.

Use a documented source-precedence policy. Prefer authoritative, validated observations when records refer to the same original measurement.

Generate hourly aligned data only when supported by the original sampling frequency. Never convert daily pollutant measurements into artificial hourly ground truth.

Store missing-data masks separately. Do not replace missing pollution observations with zero.

If input imputation is necessary, use only information available before the prediction cutoff. Preserve the imputation method and input mask.

## 10. Phase 7: Multivariate environmental time-series construction

Build station-level time series using ground-based pollution measurements as the reference timeline.

Join the following inputs when available:

- PM2.5, PM10 and NO₂.
- Other measured pollutants.
- Station meteorology.
- Reanalysis-derived historical weather.
- Archived weather forecasts.
- Calendar variables.
- Nearby station measurements.
- Satellite and aerosol observations.
- Station elevation and other static metadata.

Implement spatial joins appropriate to each dataset, such as nearest validated weather station or documented gridded interpolation.

Store distances, grid resolution, temporal offsets, product identifiers and join methodology.

Do not claim neighborhood-level resolution from coarse atmospheric model grids.

Keep the following experimental dataset configurations distinct:

1. Pollution observations only.
2. Pollution and historical weather.
3. Pollution, weather and neighboring stations.
4. Pollution, weather and atmospheric reanalysis.
5. Pollution, weather and satellite observations.
6. Operational forecasting using weather forecasts available at prediction time.

Use these configurations for later ablation studies.

## 11. Phase 8: Forecasting task construction

The initial task is next-24-hour PM2.5 forecasting for metropolitan Lima.

Default configuration:

```yaml
target: pm2_5
frequency: 1h
lookback_hours: 72
forecast_horizon_hours: 24
stride_hours: 24
minimum_input_completeness: 0.90
minimum_target_completeness: 1.00
timezone: America/Lima
```

Treat these values as configurable initial engineering choices. Adjust them based on the actual profiling results.

### Task A: Multistep forecasting

Input: previous 72 hours of measured pollutant and meteorological signals.

Target: next 24 hours of measured PM2.5 concentrations.

### Task B: Scalar prediction

Predict the mean PM2.5 concentration over the next 24 hours.

### Task C: Pollution-event classification

Determine whether the subsequent 24-hour mean exceeds a documented pollution threshold.

Investigate the applicable Peruvian environmental standards:

https://www.gob.pe/institucion/minam/normas-legales/3670-003-2017-minam

Verify averaging periods, completeness requirements and regulatory interpretation.

Distinguish a rolling 24-hour threshold event from a calendar-day exceedance. Do not label a rolling-window event as a legal ECA violation unless the calculation satisfies the relevant regulatory methodology.

Never represent regulatory thresholds as concentrations below which health risks are absent.

### Task D: Temporal question answering

Optional extension after forecasting is operational.

Generate deterministic, verifiable questions about:

- Increasing and decreasing pollution trends.
- Historical peak concentrations.
- Pollution episode timing.
- Differences between stations.
- Observed relationships with wind and precipitation.
- Forecasted pollutant concentrations.

Generate answers using verified calculations rather than invented language-model responses.

Do not generate unsupported causal explanations.

## 12. Phase 9: Dataset splits and leakage prevention

Implement chronological train, validation and test splits.

Choose final dates only after inspecting real historical coverage.

Default strategy:

- Earliest 70% of the usable timeline: training.
- Subsequent 15%: validation.
- Latest 15%: testing.

Use actual time boundaries, not random row assignments.

Requirements:

- Assign windows after establishing split boundaries.
- Prevent input and target observations from overlapping across partitions in the primary benchmark.
- Apply an appropriate boundary purge based on input and forecast horizon lengths.
- Fit scalers, imputers, feature selection and learned transformations using training data only.
- Do not expose future PM2.5 observations as input.
- Do not use realized future weather data as a substitute for historical weather forecasts.
- Record the issue and availability timestamps of forecast features.
- Account for real-world publication delays when evaluating operational forecasts.
- Prevent duplicates from crossing partitions.
- Freeze the test set before model experimentation.

Implement a secondary spatial evaluation using entirely held-out stations.

Optionally implement national pretraining followed by Lima fine-tuning. Prevent the pretraining dataset from containing observations corresponding to the held-out evaluation targets.

Produce immutable split manifests and automated leakage tests.

## 13. Phase 10: TimeNet and TimeF integration

Follow the upstream documentation:

- https://docs.timenet.ai/connectors.html
- https://docs.timenet.ai/data-model/tasks.html
- https://docs.timenet.ai/build.html
- https://docs.timenet.ai/timef-format.html
- https://docs.timenet.ai/catalog/licensing.html

Proposed dataset identifiers:

| Dataset ID | Purpose |
|---|---|
| `airaware/lima-senamhi` | Authoritative metropolitan Lima observations |
| `airaware/peru-oefa` | National environmental observations |
| `airaware/peru-openaq` | Additional ground-based observations |
| `airaware/peru-weather` | Meteorological observations or derived products |
| `airaware/peru-atmospheric` | Atmospheric and satellite-derived data |
| `airaware/lima-air-quality` | Curated Lima forecasting benchmark |
| `airaware/peru-air-quality` | Future national temporal benchmark |

Verify naming conventions and namespace availability before finalizing these identifiers.

Prefer independent base datasets and a composed benchmark dataset with pinned parent releases where supported.

Do not force all sources into a single dataset if their licenses, observation types or scientific semantics differ.

### Connector implementation

Follow TimeNet's existing connector conventions.

Expected connector structure, subject to verification against the pinned upstream version:

```text
timenet_connectors/
└── datasets/
    └── airaware/
        ├── lima_senamhi/
        │   ├── __init__.py
        │   ├── dataset.yaml
        │   ├── connector.py
        │   ├── requirements.txt
        │   └── tests/
        ├── peru_oefa/
        └── lima_air_quality/
```

Implement the appropriate connector interface.

Separate network acquisition from local conversion. Conversion must be deterministic and must not depend on live network requests.

Define:

- Record hierarchies.
- Sources and sensors.
- Signals and typed units.
- Time origins and regular or irregular axes.
- Missing-data representation.
- Station metadata.
- Data annotations.
- Forecasting tasks.
- Classification tasks.
- Task splits.
- Versioned dataset cards.
- Dataset lineage.
- Licensing and attribution.

Use shared signal descriptors and reference existing records or intervals where supported to avoid duplicating large overlapping windows.

Use TimeNet's official writer, reader and validation mechanisms. Do not implement a custom lookalike TimeF format.

Expected TimeF artifacts include:

```text
manifest.json
control.duckdb
Parquet or Zarr signal values
```

Validate that each generated dataset can be loaded through the standard TimeNet SDK.

Investigate nullable signal behavior in the selected TimeNet version and implement explicit missing-data handling before PyTorch tensor conversion.

## 14. Phase 11: Baseline training and model readiness

Before attempting temporal-language-model fine-tuning, establish forecasting baselines.

Implement:

- Last-observation persistence.
- Seasonal persistence using the same hour on the previous day.
- Historical seasonal averages.
- LightGBM or XGBoost.
- Optional small temporal neural-network baseline.

Calculate:

- MAE.
- RMSE.
- MASE where appropriate.
- Forecast error by horizon.
- Error by station and season.
- Precision and recall.
- F1.
- PR-AUC for pollution events.
- Calibration metrics for probabilistic classification.
- Performance during severe pollution episodes.

Use the same targets and frozen evaluation partitions for every model.

Provide an adapter that converts TimeNet tasks into the dataset interface required by OpenTSLM.

Investigate compatible 270M to 3B open-weight models. Prioritize a 1B model and memory-efficient training.

Do not begin expensive full-scale model training until the dataset and leakage checks pass.

Model fine-tuning is a separate follow-up milestone, but the dataset must be ready for it.

## 15. Recommended technology stack

Prefer:

| Component | Technology |
|---|---|
| Language | Python |
| Dependency management | uv |
| Data transformations | Polars |
| Embedded analytical queries | DuckDB |
| Columnar storage | Apache Parquet and PyArrow |
| HTTP acquisition | HTTPX |
| Validation | Pydantic and explicit schema checks |
| Geospatial processing | GeoPandas, Shapely, PyProj |
| Scientific raster processing | Xarray |
| Data analysis | Jupyter |
| Visualization | Plotly or Matplotlib |
| CLI | Typer |
| Testing | pytest and Hypothesis |
| Linting and formatting | Ruff |
| Type checking | Upstream-compatible tooling |
| CI/CD | GitHub Actions |
| Optional object storage | S3-compatible storage |

Use dependencies only when needed.

Avoid introducing Spark, Kafka, Airflow or Kubernetes until profiling establishes a concrete need.

Process larger-than-memory datasets using streaming readers, lazy queries, partition pruning and incremental Parquet writes.

## 16. Proposed project repository

```text
airaware-peru/
├── AGENTS.md
├── README.md
├── PLAN.md
├── ARCHITECTURE.md
├── CONTRIBUTING.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── Makefile
├── .env.example
├── .gitignore
├── configs/
│   ├── sources.yaml
│   ├── schemas/
│   ├── quality.yaml
│   ├── geography.yaml
│   ├── thresholds.yaml
│   └── benchmark.yaml
├── src/airaware/
│   ├── cli.py
│   ├── catalog/
│   ├── acquisition/
│   ├── profiling/
│   ├── schemas/
│   ├── normalization/
│   ├── quality/
│   ├── geospatial/
│   ├── alignment/
│   ├── benchmarks/
│   └── timenet/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   └── regression/
├── notebooks/
├── reports/
├── docs/
│   ├── sources/
│   ├── methodology/
│   └── dataset-cards/
├── data/
└── .github/workflows/
```

Adapt this structure to existing repository conventions.

Keep the independent AirAware pipeline separate from the minimal upstream TimeNet contribution.

## 17. Developer experience and CLI

Provide a unified CLI with commands equivalent to:

```bash
uv sync --locked

uv run airaware discover
uv run airaware catalog validate

uv run airaware download --source senamhi-lima
uv run airaware download --source oefa-peru
uv run airaware download --priority core

uv run airaware profile --source senamhi-lima
uv run airaware profile --all
uv run airaware compare

uv run airaware normalize --all
uv run airaware validate --all
uv run airaware deduplicate
uv run airaware align --region lima

uv run airaware benchmark build --name lima-pm25
uv run airaware benchmark validate --name lima-pm25

uv run airaware export timef --dataset lima-air-quality
uv run airaware report
```

These are proposed AirAware CLI commands to implement, not existing TimeNet commands.

Support dry-run, offline, date-range, source, region, bounded concurrency, output-directory and resume options.

Provide concise Makefile targets wrapping common workflows.

Validate the upstream connector separately using the pinned TimeNet CLI and documented build commands.

## 18. Phase 12: Testing and CI/CD

Implement automated tests for:

- Source catalog schema.
- HTTP error handling.
- Download checksums.
- Repeated and interrupted downloads.
- CSV encoding and delimiter handling.
- Data dictionary mapping.
- Timestamp conversion.
- Unit conversion.
- Coordinate transformation.
- Station matching.
- Deduplication.
- Missing-data handling.
- Temporal resampling.
- Forecast target construction.
- Chronological split integrity.
- Leakage prevention.
- TimeF write/read round trips.
- Dataset reproducibility.

Keep unit tests independent of external services.

Use small synthetic fixtures and, where licensing permits, representative source samples.

Mark live integration tests separately.

CI must validate code formatting, typing, unit tests, schemas, leakage tests and a small offline TimeF build.

Do not download the complete OEFA dataset on every pull request.

Follow the upstream TimeNet contribution checks before preparing the dataset PR.

## 19. Phase 13: Documentation and dataset publication

Produce a complete dataset card describing:

- Dataset purpose.
- Source organizations and attribution.
- Measurement methodology.
- Geographic coverage.
- Actual historical coverage.
- Pollutant and meteorological variables.
- Sampling frequency.
- Quality-control methodology.
- Missing-data statistics.
- Known biases.
- Station distribution.
- Temporal and spatial split methodology.
- Licensing and redistribution constraints.
- Reproduction instructions.
- Intended and inappropriate uses.
- Limitations of pollution-risk predictions.

Publish source code, reproducible acquisition instructions and compatible dataset artifacts.

Prepare a minimal upstream TimeNet contribution containing the connector, dataset card, tests and relevant documentation.

Do not publish data or open external pull requests without explicit authorization.

## 20. Implementation milestones and priorities

### M0: Research and repository bootstrap

- Inspect upstream TimeNet.
- Discover and catalog sources.
- Confirm project structure and dependency versions.
- Document unresolved questions.

### M1: Core data acquisition

- Download SENAMHI Lima and metadata.
- Download OEFA Peru and metadata.
- Verify artifacts and checksums.
- Produce initial structural profiles.

### M2: Dataset comparison and selection

- Calculate actual data quality and coverage.
- Compare station and pollutant availability.
- Calculate usable forecasting windows.
- Select the best subset for Lima forecasting.

### M3: Normalization

- Implement canonical observation schemas.
- Normalize units, coordinates and timestamps.
- Deduplicate and preserve provenance.
- Export validated Parquet datasets.

### M4: Weather integration

- Acquire station-specific historical weather.
- Align pollution and meteorological observations.
- Validate temporal and spatial joins.

### M5: First TimeF release

- Build SENAMHI base connector.
- Construct the Lima forecasting benchmark.
- Assign leakage-safe splits.
- Validate the TimeF dataset through the upstream reader.
- Prepare the TimeNet contribution.

### M6: National data expansion

- Integrate OEFA.
- Discover additional Peruvian observations through OpenAQ.
- Evaluate cross-source compatibility.
- Build Peru-wide base datasets.

### M7: Optional enrichment

- Integrate atmospheric reanalysis.
- Integrate satellite observations.
- Add wildfire and mobility context.
- Evaluate additional data configurations.

### M8: Model readiness and evaluation

- Train forecasting baselines.
- Produce frozen benchmark metrics.
- Implement the OpenTSLM dataset adapter.
- Prepare the next phase of temporal AI fine-tuning.

The hackathon-critical path is M0 through M5, followed by the baseline and temporal-model work in M8. Complete that path before spending substantial time on optional enrichment.

## 21. Acceptance criteria

The dataset engineering phase is complete when:

- All identified sources are inventoried with verified access status.
- SENAMHI and OEFA have been downloaded and profiled, or documented blockers explain why acquisition failed.
- Dataset comparisons use measured statistics instead of catalog assumptions.
- Every curated observation has traceable provenance.
- Dataset licensing is documented.
- Canonical schemas and quality rules are tested.
- Duplicate observations are resolved or explicitly marked.
- Forecasting targets contain valid measured observations.
- Chronological splits pass leakage tests.
- At least one native TimeF dataset builds reproducibly.
- The dataset can be loaded using the standard TimeNet SDK.
- A baseline model can consume the benchmark.
- Documentation is sufficient for another contributor to reproduce the results.
- The upstream dataset contribution is ready for review.

Initial target readiness guidelines:

- At least four usable Lima monitoring stations.
- At least 24 months of usable observations.
- At least 90% input completeness for retained benchmark windows.
- Fully observed 24-hour forecasting targets.
- Sufficient positive pollution events for meaningful held-out classification evaluation.

These are provisional targets, not official hackathon requirements. Report measured results and justify any necessary adjustments.

## 22. Codex execution instructions

Start in planning mode.

First inspect the repository, upstream TimeNet implementation and source availability. Produce a detailed implementation plan and dependency graph.

Then:

1. Divide the work into small, independently testable tasks.
2. Prioritize M0, M1 and M2.
3. Validate actual SENAMHI and OEFA data before committing to the final forecasting formulation.
4. Record decisions in architecture decision records.
5. Maintain `PLAN.md` with completed tasks, blockers and remaining work.
6. Run relevant tests after each implementation step.
7. Use small commits following conventional commit conventions when authorized.
8. Report measured results and unresolved uncertainties.
9. Never claim that a dataset was successfully collected or validated without inspecting the actual artifacts.
10. Avoid premature model training and infrastructure provisioning.

Make progress using locally verified evidence. When a source is inaccessible, document the failure, attempt supported alternatives and continue with independent tasks.

The first practical outcome should be a reproducible acquisition pipeline, a complete source inventory and a comparative data-quality report for SENAMHI Lima and OEFA Peru.

Use those measured results to decide the exact content of AirAware Perú's first TimeF dataset.