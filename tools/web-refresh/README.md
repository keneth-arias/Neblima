# Export a Gemma 3 1B forecast for the web

The refresh tool prepares a small six-hour forecast snapshot from SENAMHI
hourly charts. It uses 24 consecutive readings, a fixed Gemma checkpoint
at update 4,500 from seed 27, and the frozen peak correction. The
[evaluation guide](../../docs/evaluation.md) describes the model
comparisons and the [demo guide](../../docs/demo.md) describes what the
deployed interface displays.

## Produce a snapshot

The stages share one working directory. The runner needs the pinned
model artifacts for prediction and correction.

1. Run `refresh.py capture DIRECTORY` to query up to 12 SENAMHI charts
   with Lightpanda. Each query has a 45-second and 1 MB cap. Capture
   verifies the name, pollutant, dates, values, and duplicates and keeps
   the original responses and receipts. A window uses one station code
   and complete history, without merging instruments or imputing values.
2. Run `refresh.py predict DIRECTORY` to restore Gemma on the local
   graphics processing unit (GPU) with read-only weights and generation
   configuration.
3. Run `refresh.py correct DIRECTORY` to apply the frozen correction
   on the CPU and verify the relationship between the checkpoint,
   histories, and correction.
4. Run `refresh.py export DIRECTORY` to check identities, dimensions,
   and finite values for each of six horizons and write `actual.json`.

The common origin is the latest published reading. When all stations are
more than six hours behind the Lima reference clock, capture stops and
preserves the previous public version. Sites without a capture show no
reading.

## Read the snapshot contract

Version 2 uses `clock: provider_wall_clock`, `generated_at_utc`,
`source_revision`, `model`, `timeline`, and `stations`. Each station
contains source receipts, the chosen station code, its latest reading,
and eight windows aligned to `timeline`. Each window separates
`history` (24), `observed` (6), and `forecast` (6 or null), and records
`origin` and `target_times`.

SENAMHI does not declare an offset for the source chart labels. The
snapshot preserves those dates and times through midnight. Capture and
calculation timestamps use Coordinated Universal Time (UTC). Credit
SENAMHI under Open Data Commons Attribution License 1.0 when displaying
the snapshot. [Data attribution](../../DATA_ATTRIBUTION.md)

## Verify the tool

After installing the pinned TimeNet environment, run these commands
from the repository root without provider access.

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked \
  python -m unittest discover -s tools/web-refresh -p 'test_*.py'
uv run --locked ruff check tools/web-refresh
uv run --locked ruff format --check tools/web-refresh
```

Run the main [contribution checks](../../CONTRIBUTING.md#prepare-and-check-your-change)
before submitting changes.

## Deployment context

The refresh workload runs in MicroK8s on `bm`. The renderer and
publication flow for `qriqs/airaware-web` are maintained in
`ml-infra/workloads/web-refresh/`. The initial schedule set
`NOT_BEFORE=2026-11-23T14:00:00Z` to gate queries before 09:00 in
`America/Lima` on November 23, 2026. An authorized manual run without
that value can validate an immediate update.
