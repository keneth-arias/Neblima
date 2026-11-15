# AirAware foundation architecture

The independent AirAware pipeline will produce verified source artifacts and curated observations;
a minimal upstream TimeNet connector will convert supported releases with official TimeF APIs.
The current foundation implements only local workspace preparation, source metadata validation,
and environment diagnostics. No acquisition or scientific processing is implemented yet.

## Current components

- `src/airaware/catalog.py`: Pydantic source contract and safe YAML loading. Null metadata is unknown.
- `src/airaware/cli.py`: offline command interface; errors do not echo configuration values.
- `configs/sources.yaml`: 37 candidate resources from the supplied brief; all unverified.
- `configs/upstream.lock.json`: inspected upstream revisions, not installed SDK dependencies.
- `uv.lock`: exact resolved application/dev dependencies; Python is independently pinned.
- `.github/workflows/ci.yml`: locked setup, offline checks, distribution build and online advisory audit.

## Planned data flow
`raw` (immutable source bytes) → `staging` (source parsing) → `normalized` (canonical Parquet)
→ `curated` (compatible, deduplicated observations) → `benchmarks` (windows and frozen splits)
→ `timef` (official writer outputs).

`AIRAWARE_DATA_DIR` selects the local artifact root. The default is `./data` relative to the working
directory; run commands from the repo root. Git ignores all artifacts under `data`, retaining only
placeholders. External data roots are the operator's responsibility to keep outside other repos.
Future acquisition manifests must include URLs, timestamps, SHA-256, query parameters and rights.

## Boundaries and decisions
Use plain local files initially; embedded analytical tools are introduced when transformations need
them. Do not create a database service, scheduler, object-storage account or model-serving layer now.
See [ADR-001](docs/decisions/001-local-first-foundation.md) for the accepted setup decision and
[TimeNet investigation](docs/timenet-integration.md) for verified interfaces and remaining work.
