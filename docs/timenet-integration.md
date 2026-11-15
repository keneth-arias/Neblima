# Verified TimeNet integration notes

Checked 2026-11-15 against clean upstream commit
[`9bd1613019ee61fbc52e02106a1a45990ead7a54`](https://github.com/OpenTSLM/TimeNet/tree/9bd1613019ee61fbc52e02106a1a45990ead7a54).
The local checkout SHA matched remote HEAD. Both packages declare 0.12.0 and Python >=3.11;
upstream contributor guidance tests Python 3.11–3.13. This is source inspection, not an AirAware
TimeF runtime validation. AirAware intentionally does not install the SDK/build tool yet.

## Inspected contract
Paths below are relative to the pinned upstream tree.

| Component | Verified contract | Upstream path |
| --- | --- | --- |
| BaseConnector | `download(cache_dir: Path) -> list[TRaw]`, or async download; `convert(raw_refs) -> TimeFDataset` has no network I/O | `packages/timenet/src/timenet/connectors/base.py` |
| Composition | Override `compose(raw_refs, context)` for declared parents; parents are accessed through `context.parents`; use `dataset.import_from` | same file; `docs/connectors.md` |
| Dataset | `TimeFDataset(metadata=...)`; attach records/tasks through `add_record(record=...)` / `add_task(task=...)` | `packages/timenet/src/timenet/dataset/dataset.py` |
| Record/Source | Keyword-only dataclasses; Record holds root Sources and a TimeOrigin; Source holds named child sources and Signals | `dataset/record.py`, `dataset/source.py` under the same package |
| Signal | Keyword-only `spec`, `time_axis`, `name`, `data`; lazy `from_loader` is supported | `dataset/time_series.py` |
| Tasks | Built-in ForecastingTask, ClassificationTask and AnswerTask inherit keyword-only inputs/targets/prompt/split fields; classification also uses label definitions | `packages/timenet/src/timenet/types/tasks.py` |
| Storage | `dataset.write(path=..., values_backend=...)` uses official writer; `TimeFReader.open(version_dir)` reads it | `docs/timef-writer.md`, `docs/timef-reader.md` |

Writer output includes manifest.json and control.duckdb plus Parquet/Zarr signal storage.
The reader is a context manager. `TimeFReader.verify()` checks release file hashes. Do not create
an AirAware lookalike format. Internal observation templates are not TimeF artifacts.

## Missingness, splits and licensing
- Arrow nulls are preserved by `to_arrow`; `to_numpy` and the PyTorch adapter reject actual nulls.
  Handle masks and any justified causal input imputation explicitly before tensor conversion.
  See pinned `docs/data-model/time-series.md`.
- Splits live on Tasks, not Records. A Record can serve multiple splits; our window builder must
  enforce input/target separation itself. Do not copy TSQA's generic stratified splitter for a
  chronological air-quality benchmark. See `docs/data-model/tasks.md` and `docs/connectors.md`.
- `compose` and parent declarations support lineage and pinned parent releases. Confirm final
  namespace availability and exact card requirements when building the first connector.
- TimeNet code is MIT, but data retains source licenses. The hosted registry requires the dataset
  and ancestors to declare open access. `NONE` is not permission to redistribute.
  See pinned `docs/catalog/licensing.md`; AirAware has not chosen its own code license yet.

## Reusable examples and checks
Inspected AGENTS.md, CONTRIBUTING.md and package pyprojects; hello-world's connector/card and TSQA's
card and split guidance. Hello-world is an offline synthetic example; TSQA demonstrates task and card
metadata. A search of connector cards for weather/climate/air-quality/meteorology found no direct
reusable environmental connector at this revision; this is not a full external ecosystem search.

For future upstream changes, follow its per-connector requirements and contributor commands:
`make check`, `make lint-fix`, `make test`, `make test-connectors`, and license checks. Do not
run these against AirAware, whose own commands are documented in CONTRIBUTING.md.

Remaining integration work: source-specific connector, fixture round trip, namespace checks,
nullable-to-tensor tests and standard SDK loading in issues #21–#23. No dataset has been collected.

## Hackathon verification
The [official challenge](https://challenge.timenet.ai/) checked on 2026-11-15 requires onboarding a
TimeNet dataset, training/fine-tuning a temporal model, a showcase, and the submission links listed
in `docs/hackathon.md`. The research notes are not a submission. Verify deadlines and requirements
again before submitting. Each participant must register individually.
