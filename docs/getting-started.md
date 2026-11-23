# Getting started

Set up the Python tools, validate the source inventory, and replay the
forecasting pipeline with synthetic data. The setup runs from the root of
your own checkout.

## Set up your workspace

Install Git, Make, and [uv 0.11.20 or later](https://docs.astral.sh/uv/getting-started/installation/).
Neblima uses Python 3.13.13 locally. Continuous integration (CI) checks both
Python 3.11 and 3.13.13. The team develops on Linux. On Windows, use the Windows
Subsystem for Linux to run the Linux workflow.

```bash
git clone https://github.com/keneth-arias/Neblima.git
cd Neblima
uv python install
make setup
make init
make doctor
```

Setup uses the versions in `.python-version` and `uv.lock`. The diagnostic
reports `"ready": true` when Python, Git, uv, the source catalog, the Lima time
zone, and the local data folders pass their checks.

The default data root is `data/` relative to your current folder. To use a
different data root for workspace setup and commands that support it, export
`AIRAWARE_DATA_DIR` before running them. An explicit `--data-dir` takes
precedence when the command offers it. The application reads your shell
environment and leaves `.env` loading to you.

```bash
export AIRAWARE_DATA_DIR="$HOME/neblima-data"
make init
make doctor
```

## Validate the checkout

After installing dependencies, you can validate the catalog and run the
check suite without contacting data providers.

```bash
UV_OFFLINE=true uv run --locked airaware catalog validate
UV_OFFLINE=true make check
```

Catalog validation prints a JSON count and a breakdown by status. The full
check also verifies the lockfile, formatting, static analysis, type checks,
and the main test suite. For packaging and the online dependency audit, see
the [contribution guide](../CONTRIBUTING.md).

## Replay TimeF with synthetic data

Install the separate TimeNet environment once, then run the focused
end-to-end test offline. TimeF is TimeNet's time-series dataset format.

```bash
uv sync --project tools/timenet-smoke --python 3.13.13 --locked

UV_OFFLINE=true uv run --project tools/timenet-smoke --locked \
  python -m unittest discover -s tools/timenet-smoke -p 'test_offline_pipeline.py'
```

The test creates a small synthetic file, imports its original bytes,
normalizes and curates the records, builds chronological splits, and checks
the resulting TimeF release with TimeNet. It also tests that a modified
split artifact is rejected. To run the whole TimeNet tool suite and verify
the export format with the official reader, see the [TimeNet guide](timef.md).

## Work with real observations

Start from a licensed local copy of the original file. Check its checksum
against the [acquisition receipt](../metadata/senamhi-lima-download.json),
then follow the [dataset card](dataset-cards/lima-pm25-forecast.md) for the
normalization, window generation, and export steps. The [source
catalog](sources.md) tracks the evidence and restrictions for other candidates.
