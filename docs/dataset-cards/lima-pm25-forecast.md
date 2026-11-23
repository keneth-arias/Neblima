# Lima hourly PM2.5 forecast dataset

`airaware/lima-pm25-forecast@0.1.0` supports retrospective forecasts of
fine particulate matter (PM2.5). Each forecasting task contains 24
consecutive hourly values from one series and six ordered hourly targets.
The historical release preserves the published Coordinated Universal Time
(UTC) labels.

## Source, coverage, and quality

Peru's National Meteorology and Hydrology Service (SENAMHI) publishes
*Monitoreo de los contaminantes del aire en Lima Metropolitana* under the
[Open Data Commons Attribution License 1.0](https://opendatacommons.org/licenses/by/1-0/).
The pinned TimeNet revision uses `ODC-By-1.0` as the license identifier.
The SHA-256 checksum of the selected original is
`896ae8a106fb128460e81b3f58096f6b9c4d582ef28fffa46e5394c5875c40d4`.
[Source attribution and receipt](../../DATA_ATTRIBUTION.md)

The first accepted PM2.5 value is January 1, 2015, at 05:00 UTC. The last
is May 31, 2024, at 23:00 UTC. The grid covers 577,717 station-hours across
seven provisional series.

| Grid state | Station-hours |
| --- | ---: |
| A usable value | 367,518 |
| Rows present without a usable value | 210,172 |
| Conflicting readings | 20 |
| No source row | 7 |

Coverage varies across stations and monitored periods. The project accepts
the inferred unit of micrograms per cubic meter (µg/m³). Interval placement,
individual reading quality, and publication delay remain unknown. Daily
regulatory interpretation requires further evidence on time and quality.
[Hourly grid and audit (Spanish)](../../tasks/issue-15-plan.md) ·
[Source policy (Spanish)](../decisions/005-senamhi-operating-policy.md)

## Chronological splits

The cutoffs are March 16, 2022, at 08:00 UTC and February 25, 2023, at
18:00 UTC. The exact cutoff hour belongs to the new split. Each task's
24-hour history and six-hour target interval must fit in one split.
Windows that cross a cutoff are purged.

| Provisional station identity | Train | Validation | Test | Purged |
| --- | ---: | ---: | ---: | ---: |
| Campo de Marte | 42,988 | 5,342 | 4,891 | 29 |
| Carabayllo | 27,189 | 7,452 | 8,258 | 58 |
| Santa Anita | 30,219 | 7,223 | 9,988 | 58 |
| San Borja | 34,643 | 7,461 | 8,061 | 58 |
| San Juan de Lurigancho | 47,058 | 7,715 | 4,999 | 29 |
| San Martín de Porres | 27,956 | 7,783 | 6,311 | 52 |
| Villa María del Triunfo | 27,344 | 7,730 | 8,281 | 29 |
| **Total** | **237,397** | **50,706** | **50,789** | **313** |

The export count of **338,892 tasks** excludes the 313 purged windows.
Nearby windows within a split may share observations, so these counts
describe windows rather than independent samples. Fit preprocessing on
training, select models with validation, and hold test targets for final
scoring. [Split manifest and checksums (Spanish)](../../tasks/issue-19-plan.md)

## Reproduce the dataset

Use an authorized local copy for the real release. To try the same workflow
with synthetic data, follow the [offline replay](../getting-started.md#replay-timef-with-synthetic-data).

1. Match the original against the checksum above and register it with the
   [acquisition tool](../acquisition.md).
2. [Normalize the observations (Spanish)](../../reports/senamhi-normalization.md),
   [curate the measurements (Spanish)](../../tasks/issue-14-plan.md),
   and [build the hourly grid (Spanish)](../../tasks/issue-15-plan.md).
3. [Generate complete windows (Spanish)](../../tasks/issue-18-plan.md) and
   [freeze the time splits (Spanish)](../../tasks/issue-19-plan.md).
4. [Export and verify TimeF](../timef.md#export-the-lima-benchmark) with
   the pinned TimeNet software development kit (SDK) and retain the manifest alongside the dataset.

## Licensing

The source and its converted release retain ODC-BY-1.0 and the SENAMHI
attribution. Neblima's code uses AGPL-3.0-only. The separate TimeNet connector
was written against the upstream application programming interface (API)
under the MIT license. [Licensing decision
(Spanish)](../decisions/003-licencia-agpl-v3.md) ·
[Contribution record (Spanish)](../../tasks/issue-24-plan.md)
