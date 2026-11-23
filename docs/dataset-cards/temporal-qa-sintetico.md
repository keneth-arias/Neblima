# Synthetic temporal questions with verifiable answers

`temporal-qa-sintetico@0.1.0` is a synthetic question-answering fixture.
Neblima generates hourly values deterministically from seeds. The fixture
contains no real air quality measurements. [Generator](../../src/airaware/temporal_qa.py)

Each `TemporalQuestion` records the question family, series and source
observation IDs, Coordinated Universal Time (UTC) window, prompt, and
answer. Tests recalculate the answer from the underlying series and
window. An answer contains the requested value and its unit where
applicable.

## Question families

The generator creates disjoint consecutive windows. Offsets are hours
from the start of each series. The answer strings below preserve the
Spanish values used by the fixture.

| Family | Hours | Question | Answer |
| --- | --- | --- | --- |
| Trend | 0–48 | How does the mean in the second half compare with the first? | `aumento`, `disminución`, or `sin cambio` |
| Maximum | 48–72 | What is the maximum reading? | Value and unit, such as `42.17 ug/m3` |
| Time | 72–96 | When does the maximum first occur? | Timestamp, such as `2026-01-01T05:00:00+00:00` |
| Comparison | 96–120 | Which series has the higher mean over this window? | Series ID or `empate` |

The seeded congruential generator uses a triangular daily cycle and
a level shift for each series. The same seed and inputs produce the
same fixture across platforms.

## Keep forecasting targets separate

`TemporalQuestion` cases use their own schema. `validate_qa_separated`
rejects forecast target fields and windows that overlap reserved
forecast target intervals. The [tests](../../tests/test_temporal_qa.py)
check that injecting target values, adding a forecast column, or
overlapping the intervals fails.

## Map to TimeNet tasks

The November 20, 2026 review checked the TimeNet API at the commit
in the [upstream lock](../../configs/upstream.lock.json). This fixture
provides the fields below and does not assign TimeNet splits.

| Neblima field | TimeNet representation |
| --- | --- |
| `prompt` | `AnswerTask.prompt` |
| `answer` | `AnswerTask.targets` with one text target |
| `SyntheticSeries.values` | `Signal` values inside an input `Record` |
| `family` | Record annotation following the TSQA convention, using the key `task` |
| `question_id`, `observation_ids` | Neblima-specific provenance |
| `window_start`, `window_end_exclusive` | Neblima window bounds retained with the question |

The TSQA connector's stratified split belongs to that dataset. A
Lima forecasting release uses chronological splits. [AnswerTask at the
pinned commit](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/types/tasks.py#L436) ·
[TSQA connector at the pinned commit](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet-connectors/src/timenet_connectors/datasets/chengsenwang/tsqa/connector.py#L1)

## Reproduce the fixture

From the repository root, after installing the main environment,
run the generator offline. No provider access is required.

```bash
UV_OFFLINE=true uv run --locked python - <<'PY'
from datetime import UTC, datetime

from airaware.temporal_qa import build_synthetic_series, generate_questions

inicio = datetime(2026, 1, 1, tzinfo=UTC)
a = build_synthetic_series(
    series_id="sintetica-a", seed=2026, hours=120, block_hour=24, start=inicio
)
b = build_synthetic_series(
    series_id="sintetica-b", seed=2027, hours=120, block_hour=96, start=inicio
)
for pregunta in generate_questions(a, b):
    print(pregunta.question_id, "->", pregunta.answer)
PY
```

The fixture code uses AGPL-3.0-only and its values come from the generator.
The synthetic fixture has no verified versioned TimeF export. A separate
document records the later experiment with real SENAMHI records and the
checks that keep those questions away from forecasting targets.
[Real-data validation report (Spanish)](../../reports/preguntas-temporales-reales.md)
