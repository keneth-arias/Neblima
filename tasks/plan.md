# AirAware Perú implementation plan

Source: [initial plan](../docs/initial-plan.md). Tasks are tracked in GitHub Issues and the [AirAware Perú Project](https://github.com/users/keneth-arias/projects/1). This document is the ordered index; issue status is authoritative. This is planning work: no collection, validation or model results are claimed.

## Delivery decisions
- Keep repository name `airaware`; start with measured Lima/Callao PM2.5 and expand nationally after evidence gates.
- Verify upstream APIs and pin revisions before implementation. Keep the independent pipeline separate from the minimal upstream connector.
- Prioritize M0–M3, native TimeF delivery in M5, and baseline/temporal-model work in M8. M4 weather is conditional on verified availability; pollution-only remains the first vertical slice.
- License and measurement-semantics checks are exclusion gates. Coverage targets (four stations and 24 months), hourly cadence, and 72/24-hour windows remain provisional until profiling.
- No bulk dataset publication or external PR creation is authorized by this task-planning request. Expensive/unbounded acquisition and full-scale training retain explicit budget/authorization gates.
- Start with minimal Python/uv tooling; add Polars, DuckDB, HTTPX, Pydantic, geospatial and raster dependencies only when needed. No distributed infrastructure without measured need.

## Dependency flow
M0 upstream/source verification → M1 reproducible acquisition → M2 measured comparison → M3 canonical normalization → M5 pollution-only benchmark/splits → native TimeF validation → M8 baselines/adapter/temporal experiment → submission preparation.
M3 + verified weather → M4 aligned weather configuration. M6 national expansion and M7 enrichment follow the core path.

## Ordered issue index
- [M0 / P0 — Verify pinned TimeNet interfaces and hackathon requirements](https://github.com/keneth-arias/airaware/issues/1)
- [M0 / P0 — Bootstrap reproducible Python tooling and offline CI](https://github.com/keneth-arias/airaware/issues/2)
- [M0 / P0 — Build validated environmental source inventory](https://github.com/keneth-arias/airaware/issues/3)
- [M0 / P0 — Verify SENAMHI resources and redistribution rights](https://github.com/keneth-arias/airaware/issues/4)
- [M0 / P0 — Verify OEFA resources and coordinate semantics](https://github.com/keneth-arias/airaware/issues/5)
- [M1 / P0 — Implement atomic streaming downloads with provenance](https://github.com/keneth-arias/airaware/issues/6)
- [M1 / P0 — Add resumable bounded acquisition and CLI controls](https://github.com/keneth-arias/airaware/issues/7)
- [M1 / P0 — Acquire a reproducible SENAMHI Lima data slice](https://github.com/keneth-arias/airaware/issues/8)
- [M1 / P0 — Acquire bounded OEFA observations and documentation](https://github.com/keneth-arias/airaware/issues/9)
- [M2 / P0 — Profile raw station coverage and signal quality](https://github.com/keneth-arias/airaware/issues/10)
- [M2 / P0 — Compare sources and select the first Lima benchmark](https://github.com/keneth-arias/airaware/issues/11)
- [M3 / P0 — Define canonical observations and station metadata contracts](https://github.com/keneth-arias/airaware/issues/12)
- [M3 / P0 — Normalize SENAMHI into validated partitioned Parquet](https://github.com/keneth-arias/airaware/issues/13)
- [M3 / P0 — Resolve station identities and cross-source duplicates](https://github.com/keneth-arias/airaware/issues/14)
- [M3 / P0 — Construct pollution-only station timelines and masks](https://github.com/keneth-arias/airaware/issues/15)
- [M4 / P1 — Verify weather sources and acquire a station-specific slice](https://github.com/keneth-arias/airaware/issues/16)
- [M4 / P1 — Align meteorology with pollution without future leakage](https://github.com/keneth-arias/airaware/issues/17)
- [M5 / P0 — Build fully observed PM2.5 forecasting windows](https://github.com/keneth-arias/airaware/issues/18)
- [M5 / P0 — Freeze chronological splits and enforce leakage checks](https://github.com/keneth-arias/airaware/issues/19)
- [M5 / P1 — Validate pollution-event labeling methodology](https://github.com/keneth-arias/airaware/issues/20)
- [M5 / P0 — Implement native SENAMHI TimeNet base connector](https://github.com/keneth-arias/airaware/issues/21)
- [M5 / P0 — Export the leakage-safe Lima TimeF benchmark](https://github.com/keneth-arias/airaware/issues/22)
- [M5 / P0 — Run offline end-to-end dataset release checks](https://github.com/keneth-arias/airaware/issues/23)
- [M5 / P0 — Publish dataset methodology and prepare upstream contribution](https://github.com/keneth-arias/airaware/issues/24)
- [M8 / P0 — Evaluate persistence and seasonal forecast baselines](https://github.com/keneth-arias/airaware/issues/25)
- [M8 / P1 — Evaluate a tabular baseline and event metrics](https://github.com/keneth-arias/airaware/issues/26)
- [M8 / P0 — Implement OpenTSLM adapter and bounded model smoke test](https://github.com/keneth-arias/airaware/issues/27)
- [M8 / P0 — Train and evaluate the hackathon temporal-model experiment](https://github.com/keneth-arias/airaware/issues/28)
- [M8 / P0 — Prepare hackathon showcase and submission package](https://github.com/keneth-arias/airaware/issues/29)
- [M6 / P2 — Normalize OEFA and validate national measurement compatibility](https://github.com/keneth-arias/airaware/issues/30)
- [M6 / P2 — Discover Peru OpenAQ observations and aggregator overlap](https://github.com/keneth-arias/airaware/issues/31)
- [M6 / P2 — Add held-out-station evaluation and safe national pretraining splits](https://github.com/keneth-arias/airaware/issues/32)
- [M7 / P2 — Pilot atmospheric and satellite enrichment](https://github.com/keneth-arias/airaware/issues/33)
- [M7 / P2 — Evaluate optional wildfire mobility and contextual features](https://github.com/keneth-arias/airaware/issues/34)
- [M7 / P2 — Generate deterministic temporal QA as a follow-up](https://github.com/keneth-arias/airaware/issues/35)

## Checkpoints
- After upstream/tooling/catalog: offline checks pass; source inventory retains verification dates and blockers.
- After source probes/downloader: content validation and acquisition failure tests pass before real downloads.
- After acquisition/profile/selection: inspect real artifacts, rights, comparison metrics and readiness; record the selected benchmark in an ADR.
- After schema/normalization/deduplication: audit provenance, cadence, units, station identities and missing masks.
- After windows/splits/TimeF: inspect leakage tests and standard SDK round trip; freeze release inputs and evaluation manifests.
- Before training and showcase: dataset gates pass, bounded compute config is recorded, metrics compare identical targets, and limitations are documented.

## Risks and unresolved decisions
Source URLs, download sizes, licenses and coverage are candidates until verified. Failure must leave a documented blocker rather than fabricated progress. Decide final stations/date ranges, regulatory event methodology, code license, dataset licenses, upstream namespaces, artifact hosting and model/compute budget from evidence. The supplied source plan retains its complete discovery list and proposed architecture; proposed commands and paths are not implemented APIs.

## Next work
Begin with the upstream investigation and source inventory, then SENAMHI/OEFA verification. Do not start optional enrichment before the measured comparison and first usable forecasting slice.
