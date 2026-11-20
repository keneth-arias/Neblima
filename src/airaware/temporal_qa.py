"""Preguntas temporales con respuestas calculables sobre series identificadas.

Primera entrega de la issue #35: generación determinista de preguntas de tendencia, máximo,
momento y comparación. La vía sintética usa una serie horaria generada de forma
determinista (generador congruencial propio, sin datos reales ni red); la vía observada
(`ObservedSeries`) recibe registros reales con atribución obligatoria y se apoya en
`build_temporal_question` y `generate_questions_for_windows`, que también sostienen la vía
sintética. Cada respuesta la calcula una función pura y se verifica de ida y vuelta
(pregunta → respuesta → verificación): el texto de respuesta es solo el valor calculado con
su unidad, sin explicaciones causales.

Alineación con la interfaz de preguntas temporales de TimeNet (revisión fijada
9bd1613019ee61fbc52e02106a1a45990ead7a54, consultada el 2026-11-20 UTC):

- prompt  -> AnswerTask.prompt (texto de la pregunta).
- answer  -> AnswerTask.targets como tupla de un solo texto.
- SyntheticSeries.values -> valores de la Signal dentro del Record que forma
  AnswerTask.inputs; TSQA crea un Record por muestra con OrdinalAxis, que no debe copiarse
  para fechas físicas (la conversión a TimeF con RegularAxis queda pendiente).
- family  -> convención de anotación del Record de TSQA (Annotation con clave "task").
- question_id y observation_ids -> trazabilidad propia de AirAware, sin equivalente
  obligatorio en AnswerTask.
- window_start y window_end_exclusive -> TSQA no modela ventanas: la ventana queda expresada
  en el texto y en estos campos; no se inventan parámetros horizon/lookback de
  ForecastingTask.
- split   -> pertenece a Task en TimeNet; esta entrega no asigna partición y la partición
  estratificada 80/10/10 de TSQA no sirve como separación temporal para Lima.

Los enlaces fijados a AnswerTask y al conector TSQA están en la tarjeta
docs/dataset-cards/temporal-qa-sintetico.md; la lectura fue puntual y de solo lectura.

Separación probada: los casos de QA son estructuras distintas de las ventanas de pronóstico
de senamhi_windows y no comparten campos ni ventanas con sus objetivos; la función
validate_qa_separated y las pruebas de tests/test_temporal_qa.py fallan si se mezclan. Las
pruebas del pronóstico y los ejemplos de demostración de tools/timenet-smoke permanecen
separados de estos casos y así se registra en la tarjeta del conjunto.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from datetime import UTC, datetime, timedelta
from statistics import fmean
from typing import Literal, Protocol

PM25_UNIT = "ug/m3"

QAFamily = Literal["trend", "maximum", "moment", "comparison"]
QA_FAMILIES: tuple[QAFamily, ...] = ("trend", "maximum", "moment", "comparison")

HOUR = timedelta(hours=1)
_MINIMUM_HOURS = 120

# Ventanas consecutivas y disjuntas por serie, contadas en horas desde el origen.
_TREND_START_HOUR = 0
_TREND_HOURS = 48
_MAXIMUM_START_HOUR = 48
_MAXIMUM_HOURS = 24
_MOMENT_START_HOUR = 72
_MOMENT_HOURS = 24
_COMPARISON_START_HOUR = 96
_COMPARISON_HOURS = 24

# Generador congruencial propio: determinista entre plataformas y sin el azar global.
_LCG_MULTIPLIER = 1_664_525
_LCG_INCREMENT = 1_013_904_223
_LCG_MODULUS = 2**32
_BASE_LEVEL = 20.0
_BLOCK_SHIFT = 12.0
_DIURNAL_AMPLITUDE = 1.5
_NOISE_AMPLITUDE = 6.0

# Columnas de la ventana de pronóstico (windows.parquet de #18) usadas como referencia del
# objetivo: ningún campo de QA debe coincidir con ellas y ninguna ventana de QA debe solapar
# el intervalo que cubren target_start..target_end (inclusivo).
FORECAST_TARGET_FIELDS = frozenset(
    {
        "window_id",
        "series_id",
        "station_key",
        "history_start",
        "origin_at",
        "target_start",
        "target_end",
        "target_values",
        "target_mean",
    }
)


def _check_aligned(instant: datetime) -> None:
    """Exigir instantes con zona horaria y alineados a la hora."""
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Se requiere instante con zona horaria confirmada")
    exact = instant.astimezone(UTC)
    if exact.minute or exact.second or exact.microsecond:
        raise ValueError("El instante debe coincidir con una hora exacta")


def _check_values(values: Sequence[float]) -> None:
    for value in values:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError("Los valores deben ser números finitos y no negativos")


@dataclass(frozen=True)
class SyntheticSeries:
    """Serie horaria sintética identificada como tal; no contiene observaciones reales."""

    series_id: str
    start: datetime
    values: tuple[float, ...]
    block_hour: int
    synthetic: bool
    pollutant: str = "PM2.5"

    def __post_init__(self) -> None:
        if self.synthetic is not True:
            raise ValueError("La serie debe quedar identificada como sintética (synthetic=True)")
        if not self.series_id.strip():
            raise ValueError("La serie requiere identificador no vacío")
        if not self.pollutant.strip():
            raise ValueError("La serie requiere etiqueta de contaminante no vacía")
        _check_aligned(self.start)
        if not self.values:
            raise ValueError("La serie requiere al menos un valor")
        _check_values(self.values)
        if not 0 < self.block_hour < len(self.values):
            raise ValueError("El cambio de bloque debe quedar dentro de la serie")

    @property
    def observation_ids(self) -> tuple[str, ...]:
        """Identificador trazable de cada casilla horaria de origen."""
        return tuple(f"obs:{self.series_id}:{index:04d}" for index in range(len(self.values)))


class HourlySeries(Protocol):
    """Contrato mínimo de una serie horaria para las preguntas de QA."""

    @property
    def series_id(self) -> str: ...

    @property
    def start(self) -> datetime: ...

    @property
    def pollutant(self) -> str: ...

    @property
    def values(self) -> tuple[float, ...]: ...

    @property
    def observation_ids(self) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class ObservedSeries:
    """Serie horaria observada en registros reales, con atribución obligatoria.

    Los valores provienen de una fuente trazable (por ejemplo, el paquete TimeF verificado
    de la issue #35); la atribución identifica a la fuente y su licencia. Los identificadores
    de observación fijan la hora UTC exacta de cada casilla, que junto al identificador de
    serie permite recuperar la fila original en los insumos.
    """

    series_id: str
    start: datetime
    values: tuple[float, ...]
    attribution: str
    pollutant: str = "PM2.5"

    def __post_init__(self) -> None:
        if not self.series_id.strip():
            raise ValueError("La serie requiere identificador no vacío")
        if not self.attribution.strip():
            raise ValueError("La serie observada requiere atribución de su fuente")
        if not self.pollutant.strip():
            raise ValueError("La serie requiere etiqueta de contaminante no vacía")
        _check_aligned(self.start)
        if not self.values:
            raise ValueError("La serie requiere al menos un valor")
        _check_values(self.values)

    @property
    def observation_ids(self) -> tuple[str, ...]:
        """Hora UTC exacta de cada casilla: clave de recuperación del registro original."""
        origin = self.start.astimezone(UTC)
        return tuple(
            f"obs:{self.series_id}:{(origin + index * HOUR).isoformat()}"
            for index in range(len(self.values))
        )


def build_synthetic_series(
    *, series_id: str, seed: int, hours: int, block_hour: int, start: datetime
) -> SyntheticSeries:
    """Generar la serie sintética determinista con ciclo diario triangular y salto de bloque."""
    if hours < _MINIMUM_HOURS:
        raise ValueError(f"La serie requiere al menos {_MINIMUM_HOURS} horas para las familias")
    if not 0 < block_hour < hours:
        raise ValueError("El cambio de bloque debe quedar dentro de la serie")
    state = seed % _LCG_MODULUS
    values: list[float] = []
    for index in range(hours):
        state = (_LCG_MULTIPLIER * state + _LCG_INCREMENT) % _LCG_MODULUS
        noise = state / _LCG_MODULUS * _NOISE_AMPLITUDE
        phase = index % 24
        diurnal = (phase if phase < 12 else 23 - phase) * _DIURNAL_AMPLITUDE
        level = _BASE_LEVEL + (_BLOCK_SHIFT if index >= block_hour else 0.0)
        values.append(round(level + diurnal + noise, 2))
    return SyntheticSeries(
        series_id=series_id,
        start=start,
        values=tuple(values),
        block_hour=block_hour,
        synthetic=True,
    )


def answer_maximum(values: Sequence[float]) -> str:
    """Devolver el máximo de la ventana como valor con unidad, sin explicaciones."""
    if not values:
        raise ValueError("La ventana no tiene valores")
    return f"{max(values):.2f} {PM25_UNIT}"


def answer_moment(values: Sequence[float], *, start: datetime) -> str:
    """Devolver el instante UTC del primer máximo en formato ISO 8601; el valor es el instante."""
    if not values:
        raise ValueError("La ventana no tiene valores")
    _check_aligned(start)
    index = max(range(len(values)), key=lambda position: values[position])
    return (start.astimezone(UTC) + index * HOUR).isoformat()


def answer_trend(values: Sequence[float]) -> str:
    """Comparar las medias de dos mitades iguales; etiqueta categórica sin causa."""
    if len(values) < 2 or len(values) % 2:
        raise ValueError("La ventana de tendencia requiere un número par de horas")
    half = len(values) // 2
    first_mean = fmean(values[:half])
    second_mean = fmean(values[half:])
    if second_mean > first_mean:
        return "aumento"
    if second_mean < first_mean:
        return "disminución"
    return "sin cambio"


def answer_comparison(
    values_a: Sequence[float], values_b: Sequence[float], *, series_id_a: str, series_id_b: str
) -> str:
    """Devolver el identificador de la serie con media mayor; empate exacto si coinciden."""
    if not values_a or not values_b:
        raise ValueError("Las ventanas comparadas no tienen valores")
    for series_id in (series_id_a, series_id_b):
        if not series_id.strip():
            raise ValueError("La comparación requiere identificadores de serie no vacíos")
    mean_a = fmean(values_a)
    mean_b = fmean(values_b)
    if mean_a == mean_b:
        return "empate"
    return series_id_a if mean_a > mean_b else series_id_b


@dataclass(frozen=True)
class TemporalQuestion:
    """Caso de QA temporal trazable: pregunta con respuesta calculada, sin causa."""

    question_id: str
    family: QAFamily
    series_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    window_start: datetime
    window_end_exclusive: datetime
    prompt: str
    answer: str

    def __post_init__(self) -> None:
        if not self.question_id.strip():
            raise ValueError("La pregunta requiere identificador no vacío")
        if self.family not in QA_FAMILIES:
            raise ValueError("Familia de pregunta no admitida")
        if not self.series_ids or any(not series_id.strip() for series_id in self.series_ids):
            raise ValueError("La pregunta requiere identificadores de serie no vacíos")
        if len(set(self.series_ids)) != len(self.series_ids):
            raise ValueError("Los identificadores de serie deben ser únicos por pregunta")
        if not self.observation_ids or any(not oid.strip() for oid in self.observation_ids):
            raise ValueError("La pregunta requiere identificadores de observación no vacíos")
        if len(set(self.observation_ids)) != len(self.observation_ids):
            raise ValueError("Los identificadores de observación deben ser únicos por pregunta")
        _check_aligned(self.window_start)
        _check_aligned(self.window_end_exclusive)
        if self.window_start.astimezone(UTC) >= self.window_end_exclusive.astimezone(UTC):
            raise ValueError("La ventana de la pregunta debe avanzar en el tiempo")
        if not self.prompt.strip() or not self.answer.strip():
            raise ValueError("La pregunta requiere texto de pregunta y respuesta no vacíos")


def _window_range(
    series: HourlySeries, start: datetime, end_exclusive: datetime
) -> tuple[int, int]:
    """Índices [first, last) de una ventana alineada dentro de la serie."""
    _check_aligned(start)
    _check_aligned(end_exclusive)
    origin = series.start.astimezone(UTC)
    offset_start = start.astimezone(UTC) - origin
    offset_end = end_exclusive.astimezone(UTC) - origin
    if offset_start % HOUR or offset_end % HOUR:
        raise ValueError("La ventana debe alinearse con la hora de la serie")
    first = offset_start // HOUR
    last = offset_end // HOUR
    if first < 0 or first >= last or last > len(series.values):
        raise ValueError("La ventana queda fuera de la serie o está vacía")
    return first, last


def _window_values(
    series: HourlySeries, start: datetime, end_exclusive: datetime
) -> tuple[float, ...]:
    first, last = _window_range(series, start, end_exclusive)
    return series.values[first:last]


def _window_ids(series: HourlySeries, start: datetime, end_exclusive: datetime) -> tuple[str, ...]:
    first, last = _window_range(series, start, end_exclusive)
    return series.observation_ids[first:last]


def _window_text(start: datetime, end_exclusive: datetime) -> str:
    begin = start.astimezone(UTC)
    end = end_exclusive.astimezone(UTC)
    return f"del {begin:%Y-%m-%d %H:%M} al {end:%Y-%m-%d %H:%M} (UTC)"


def _require_series_count(question: TemporalQuestion, expected: int) -> None:
    if len(question.series_ids) != expected:
        raise ValueError(f"La familia {question.family} requiere {expected} serie(s)")


def recompute_answer(question: TemporalQuestion, series_by_id: Mapping[str, HourlySeries]) -> str:
    """Recalcular la respuesta desde las series y la ventana; función pura de ida y vuelta."""
    missing = [series_id for series_id in question.series_ids if series_id not in series_by_id]
    if missing:
        raise ValueError(f"La pregunta referencia series desconocidas: {', '.join(missing)}")
    values = []
    observation_ids = []
    for series_id in question.series_ids:
        series = series_by_id[series_id]
        first, last = _window_range(series, question.window_start, question.window_end_exclusive)
        if series.series_id != series_id:
            raise ValueError(f"El identificador de la serie no coincide con {series_id}")
        values.append(series.values[first:last])
        observation_ids.extend(series.observation_ids[first:last])
    if tuple(observation_ids) != question.observation_ids:
        raise ValueError("Las observaciones declaradas difieren de las de la ventana")
    if question.family == "trend":
        _require_series_count(question, 1)
        return answer_trend(values[0])
    if question.family == "maximum":
        _require_series_count(question, 1)
        return answer_maximum(values[0])
    if question.family == "moment":
        _require_series_count(question, 1)
        return answer_moment(values[0], start=question.window_start)
    _require_series_count(question, 2)
    return answer_comparison(
        values[0],
        values[1],
        series_id_a=question.series_ids[0],
        series_id_b=question.series_ids[1],
    )


def verify_answer(question: TemporalQuestion, series_by_id: Mapping[str, HourlySeries]) -> bool:
    """Verificación de ida y vuelta: la respuesta guardada coincide con la recalculada."""
    return recompute_answer(question, series_by_id) == question.answer


def generate_questions(
    series: HourlySeries, comparison_series: HourlySeries
) -> tuple[TemporalQuestion, ...]:
    """Generar las cuatro familias deterministas: tendencia, máximo, momento y comparación."""
    if series.series_id == comparison_series.series_id:
        raise ValueError("Las series comparadas deben tener identificadores distintos")
    if series.start.astimezone(UTC) != comparison_series.start.astimezone(UTC):
        raise ValueError("Las series comparadas deben compartir el origen horario")
    for candidate in (series, comparison_series):
        if len(candidate.values) < _MINIMUM_HOURS:
            raise ValueError(
                f"Las series requieren al menos {_MINIMUM_HOURS} horas para las cuatro familias"
            )
    origin = series.start.astimezone(UTC)
    windows: dict[QAFamily, tuple[datetime, datetime]] = {
        "trend": (
            origin + _TREND_START_HOUR * HOUR,
            origin + (_TREND_START_HOUR + _TREND_HOURS) * HOUR,
        ),
        "maximum": (
            origin + _MAXIMUM_START_HOUR * HOUR,
            origin + (_MAXIMUM_START_HOUR + _MAXIMUM_HOURS) * HOUR,
        ),
        "moment": (
            origin + _MOMENT_START_HOUR * HOUR,
            origin + (_MOMENT_START_HOUR + _MOMENT_HOURS) * HOUR,
        ),
        "comparison": (
            origin + _COMPARISON_START_HOUR * HOUR,
            origin + (_COMPARISON_START_HOUR + _COMPARISON_HOURS) * HOUR,
        ),
    }
    return generate_questions_for_windows(series, comparison_series, windows)


def generate_questions_for_windows(
    series: HourlySeries,
    comparison_series: HourlySeries,
    windows: Mapping[QAFamily, tuple[datetime, datetime]],
) -> tuple[TemporalQuestion, ...]:
    """Generar las familias indicadas sobre ventanas explícitas dentro de las series.

    Cada familia usa su ventana declarada; la familia de comparación exige la segunda serie.
    Las ventanas resultantes deben quedar disjuntas por serie. La vía sintética llama a
    `generate_questions` con el diseño canónico consecutivo; la vía observada pasa ventanas
    tomadas de tramos reales con datos completos.
    """
    if series.series_id == comparison_series.series_id:
        raise ValueError("Las series comparadas deben tener identificadores distintos")
    desconocidas = sorted(set(windows) - set(QA_FAMILIES))
    if desconocidas:
        raise ValueError(f"Familias no admitidas: {', '.join(desconocidas)}")
    if not windows:
        raise ValueError("Se requiere al menos una familia de preguntas")
    questions = [
        build_temporal_question(
            family,
            segments=_segments_for(series, comparison_series, family),
            window_start=start,
            window_end_exclusive=end,
        )
        for family, (start, end) in sorted(
            windows.items(), key=lambda item: QA_FAMILIES.index(item[0])
        )
    ]
    _ensure_disjoint_windows(questions)
    return tuple(questions)


def _segments_for(
    series: HourlySeries, comparison_series: HourlySeries, family: QAFamily
) -> dict[str, HourlySeries]:
    if family == "comparison":
        return {series.series_id: series, comparison_series.series_id: comparison_series}
    return {series.series_id: series}


def build_temporal_question(
    family: QAFamily,
    *,
    segments: Mapping[str, HourlySeries],
    window_start: datetime,
    window_end_exclusive: datetime,
) -> TemporalQuestion:
    """Construir una pregunta de QA temporal sobre segmentos de serie reales o sintéticos.

    Los segmentos deben cubrir la ventana declarada; las familias de una sola serie exigen
    un segmento y la comparación exactamente dos. La respuesta la calcula la función pura de
    la familia y los identificadores de observación salen de los segmentos en su orden.
    """
    if family not in QA_FAMILIES:
        raise ValueError("Familia de pregunta no admitida")
    esperados = 2 if family == "comparison" else 1
    if len(segments) != esperados:
        raise ValueError(f"La familia {family} requiere {esperados} serie(s)")
    for series_id, segment in segments.items():
        if segment.series_id != series_id:
            raise ValueError(f"El identificador de la serie no coincide con {series_id}")
    series_ids = tuple(segments)
    values = [
        _window_values(segments[series_id], window_start, window_end_exclusive)
        for series_id in series_ids
    ]
    observation_ids = tuple(
        oid
        for series_id in series_ids
        for oid in _window_ids(segments[series_id], window_start, window_end_exclusive)
    )
    if family == "comparison":
        first, second = values
        answer = answer_comparison(
            first, second, series_id_a=series_ids[0], series_id_b=series_ids[1]
        )
    elif family == "trend":
        answer = answer_trend(values[0])
    elif family == "maximum":
        answer = answer_maximum(values[0])
    else:
        answer = answer_moment(values[0], start=window_start)
    question = TemporalQuestion(
        question_id=_question_id(family, series_ids),
        family=family,
        series_ids=series_ids,
        observation_ids=observation_ids,
        window_start=window_start,
        window_end_exclusive=window_end_exclusive,
        prompt=_prompt(
            family,
            series_ids,
            [segments[series_id].pollutant for series_id in series_ids],
            window_start,
            window_end_exclusive,
        ),
        answer=answer,
    )
    return question


def _question_id(family: QAFamily, series_ids: tuple[str, ...]) -> str:
    if family == "comparison":
        return f"tqa-v1-comparison-{series_ids[0]}-vs-{series_ids[1]}"
    return f"tqa-v1-{series_ids[0]}-{family}"


def _prompt(
    family: QAFamily,
    series_ids: tuple[str, ...],
    pollutants: Sequence[str],
    window_start: datetime,
    window_end_exclusive: datetime,
) -> str:
    window = _window_text(window_start, window_end_exclusive)
    if family == "trend":
        return (
            f"Para la serie {series_ids[0]}, entre {window}, "
            f"¿cómo cambió la media de {pollutants[0]} de la primera mitad de la ventana a la "
            "segunda? Responde solo: aumento, disminución o sin cambio."
        )
    if family == "maximum":
        return (
            f"Para la serie {series_ids[0]}, ¿cuál es el valor máximo de {pollutants[0]} "
            f"entre {window}? Responde solo el valor con su unidad."
        )
    if family == "moment":
        return (
            f"Para la serie {series_ids[0]}, ¿en qué instante ocurre el primer máximo "
            f"de {pollutants[0]} entre {window}? "
            "Responde solo el instante en formato ISO 8601 con zona UTC."
        )
    if pollutants[0] == pollutants[1]:
        return (
            f"Entre {window}, ¿cuál de las dos series tiene la media de {pollutants[0]} mayor: "
            f"{series_ids[0]} o {series_ids[1]}? Responde solo el identificador de la serie "
            "o empate."
        )
    return (
        f"Entre {window}, ¿cuál de las dos series tiene la media mayor: {series_ids[0]} "
        f"({pollutants[0]}) o {series_ids[1]} ({pollutants[1]})? Responde solo el "
        "identificador de la serie o empate."
    )


def _ensure_disjoint_windows(questions: Sequence[TemporalQuestion]) -> None:
    per_series: dict[str, list[tuple[datetime, datetime, str]]] = {}
    for question in questions:
        for series_id in question.series_ids:
            per_series.setdefault(series_id, []).append(
                (
                    question.window_start.astimezone(UTC),
                    question.window_end_exclusive.astimezone(UTC),
                    question.question_id,
                )
            )
    for series_id, windows in per_series.items():
        ordered = sorted(windows)
        for (_start, previous_end, _id), (next_start, _end, _other) in zip(
            ordered, ordered[1:], strict=False
        ):
            if previous_end > next_start:
                raise ValueError(f"Las ventanas de QA de la serie {series_id} se solapan")


@dataclass(frozen=True)
class ForecastTargetInterval:
    """Intervalo objetivo de una ventana de pronóstico; solo para comprobar la separación."""

    series_id: str
    target_start: datetime
    target_end: datetime

    def __post_init__(self) -> None:
        if not self.series_id.strip():
            raise ValueError("El intervalo requiere identificador de serie no vacío")
        _check_aligned(self.target_start)
        _check_aligned(self.target_end)
        if self.target_start.astimezone(UTC) > self.target_end.astimezone(UTC):
            raise ValueError("El intervalo objetivo debe avanzar en el tiempo")


def validate_qa_separated(
    questions: Sequence[TemporalQuestion], forecast_intervals: Sequence[ForecastTargetInterval]
) -> None:
    """Comprobar que ningún caso de QA comparte campos ni ventanas con objetivos de pronóstico."""
    mixed = sorted({field.name for field in fields(TemporalQuestion)} & FORECAST_TARGET_FIELDS)
    if mixed:
        raise ValueError(
            "Los casos de QA comparten campos con el objetivo de pronóstico: " + ", ".join(mixed)
        )
    for question in questions:
        start = question.window_start.astimezone(UTC)
        end_exclusive = question.window_end_exclusive.astimezone(UTC)
        for interval in forecast_intervals:
            if interval.series_id not in question.series_ids:
                continue
            if (
                start <= interval.target_end.astimezone(UTC)
                and interval.target_start.astimezone(UTC) < end_exclusive
            ):
                raise ValueError(
                    f"La ventana de la pregunta {question.question_id} se solapa con el "
                    f"objetivo de pronóstico de la serie {interval.series_id}"
                )
