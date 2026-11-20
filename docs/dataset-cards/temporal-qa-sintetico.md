# Preguntas temporales sintéticas con respuestas calculables

**Conjunto SINTÉTICO.** Las series y sus valores se generan de forma determinista con
`src/airaware/temporal_qa.py` a partir de una semilla; no contienen ninguna observación real
de SENAMHI, OEFA ni de otra fuente. Este conjunto no sirve para medir ni interpretar la
calidad del aire de Lima.

`temporal-qa-sintetico@0.1.0` acompaña la primera entrega de la issue #35: preguntas de
tendencia, máximo, momento y comparación sobre una serie horaria sintética identificada como
tal. Cada caso (`TemporalQuestion`) incluye identificador, familia, series e identificadores
de observación de origen, ventana en UTC, pregunta en texto y respuesta calculada por una
función pura. La verificación de ida y vuelta (pregunta → respuesta → verificación) recalcula
cada respuesta desde las series y la ventana y se comprueba en las pruebas. El texto de
respuesta es solo el valor calculado con su unidad, sin explicaciones causales.

## Familias y respuestas

| Familia | Pregunta | Respuesta (formato) |
| --- | --- | --- |
| tendencia | media de la primera mitad frente a la segunda | `aumento`, `disminución` o `sin cambio` |
| máximo | valor máximo de la ventana | valor con unidad, p. ej. `42.17 ug/m3` |
| momento | instante del primer máximo | ISO 8601 UTC, p. ej. `2026-01-01T05:00:00+00:00` |
| comparación | media mayor de dos series en la misma ventana | identificador de la serie o `empate` |

Las ventanas son consecutivas y disjuntas por serie: tendencia (horas 0–48), máximo (48–72),
momento (72–96) y comparación (96–120), contadas desde el origen de la serie. El generador
es un congruencial propio (determinista entre plataformas) con ciclo diario triangular y un
salto de nivel por serie; dos ejecuciones producen el mismo conjunto.

## Separación de los objetivos de pronóstico

Los casos de QA usan la estructura `TemporalQuestion`, distinta de las ventanas de
pronóstico de #18: no comparten campos con las columnas de `windows.parquet` (conjunto
`FORECAST_TARGET_FIELDS`) ni ventanas con sus intervalos objetivo. La función
`validate_qa_separated` y las pruebas de `tests/test_temporal_qa.py` fallan si se mezclan:
añadir una columna de pronóstico a la pregunta, inyectar valores objetivo en un caso de QA o
solapar una ventana de QA con un objetivo hace fallar la suite. Las pruebas del pronóstico y
los ejemplos de demostración de [tools/timenet-smoke](../../tools/timenet-smoke/README.md)
permanecen separados de estos casos y así se registra en esta tarjeta.

## Alineación con la interfaz de preguntas temporales de TimeNet

Contrato consultado el **2026-11-20 (UTC)** en la revisión fijada
`9bd1613019ee61fbc52e02106a1a45990ead7a54` (`configs/upstream.lock.json`), mediante lectura
puntual y de solo lectura de dos archivos; no se modificó la interfaz externa ni se instaló
timenet en el paquete principal.

| Campo de AirAware | Contrato TimeNet | Evidencia fijada |
| --- | --- | --- |
| `prompt` | `AnswerTask.prompt` (texto de la pregunta) | [types/tasks.py, AnswerTask](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/types/tasks.py#L436) |
| `answer` | `AnswerTask.targets` como tupla de un solo texto | [types/tasks.py, AnswerTask](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/types/tasks.py#L436) |
| `SyntheticSeries.values` | valores de la `Signal` dentro del `Record` que forma `AnswerTask.inputs` | [conector TSQA](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet-connectors/src/timenet_connectors/datasets/chengsenwang/tsqa/connector.py#L1) |
| `family` | anotación del `Record` con la convención de TSQA (`Annotation` con clave `task`) | [conector TSQA](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet-connectors/src/timenet_connectors/datasets/chengsenwang/tsqa/connector.py#L1) |
| `question_id`, `observation_ids` | trazabilidad propia de AirAware; sin equivalente obligatorio en `AnswerTask` | — |
| `window_start`, `window_end_exclusive` | TSQA no modela ventanas: la ventana queda en el texto y en estos campos; no se inventan `horizon`/`lookback` de `ForecastingTask` | [types/tasks.py](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet/src/timenet/types/tasks.py#L485) |
| `split` | pertenece a `Task` en TimeNet; esta entrega no asigna partición; la estratificada 80/10/10 con semilla 42 de TSQA no sirve como separación temporal de Lima | [conector TSQA](https://github.com/OpenTSLM/TimeNet/blob/9bd1613019ee61fbc52e02106a1a45990ead7a54/packages/timenet-connectors/src/timenet_connectors/datasets/chengsenwang/tsqa/connector.py#L1) |

La conversión a un conjunto TimeF y la asignación de particiones quedan pendientes para una
entrega posterior de #35.

## Reproducir

Sin red ni dependencias nuevas, desde la raíz del proyecto:

```bash
uv run --locked python - <<'PY'
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

La suite `tests/test_temporal_qa.py` verifica determinismo, ida y vuelta de cada respuesta y
la separación de los objetivos de pronóstico.

## Licencias y pendiente

El código es propio de AirAware bajo **AGPL-3.0-only** (LICENSE y NOTICE). La serie es
sintética: no tiene licencia de datos de terceros ni atribución externa. La versión con
datos reales SENAMHI queda **pendiente** hasta acreditar trazabilidad de derechos compatible
con la redistribución; ver la [atribución del original](../../DATA_ATTRIBUTION.md) y la
[tarjeta de pronóstico](lima-pm25-forecast.md). Tampoco se generó todavía el conjunto como
archivo versionado ni se validó con el runtime de TimeNet; ambas tareas corresponden a
entregas posteriores de #35.
