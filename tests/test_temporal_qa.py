"""Pruebas de preguntas temporales sintéticas con respuestas calculables (issue #35)."""

import inspect
import re
from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta
from statistics import fmean
from zoneinfo import ZoneInfo

import pytest

import airaware.temporal_qa as temporal_qa_module
from airaware.temporal_qa import (
    FORECAST_TARGET_FIELDS,
    PM25_UNIT,
    QA_FAMILIES,
    ForecastTargetInterval,
    SyntheticSeries,
    TemporalQuestion,
    answer_comparison,
    answer_maximum,
    answer_moment,
    answer_trend,
    build_synthetic_series,
    generate_questions,
    recompute_answer,
    validate_qa_separated,
    verify_answer,
)

START = datetime(2026, 1, 1, tzinfo=UTC)
HOURS = 120
ANSWER_PATTERNS = {
    "maximum": rf"^\d+\.\d{{2}} {re.escape(PM25_UNIT)}$",
    "moment": r"^\d{4}-\d{2}-\d{2}T\d{2}:00:00\+00:00$",
    "trend": r"^(aumento|disminución|sin cambio)$",
    "comparison": r"^(sintetica-a|sintetica-b|empate)$",
}
QUESTION_FIELDS = {field.name for field in fields(TemporalQuestion)}


def build_pair() -> tuple[SyntheticSeries, SyntheticSeries]:
    a = build_synthetic_series(
        series_id="sintetica-a", seed=2026, hours=HOURS, block_hour=24, start=START
    )
    b = build_synthetic_series(
        series_id="sintetica-b", seed=2027, hours=HOURS, block_hour=96, start=START
    )
    return a, b


def build_all() -> tuple[SyntheticSeries, SyntheticSeries, tuple[TemporalQuestion, ...]]:
    a, b = build_pair()
    return a, b, generate_questions(a, b)


def mapping(a: SyntheticSeries, b: SyntheticSeries) -> dict[str, SyntheticSeries]:
    return {a.series_id: a, b.series_id: b}


def manual_series(values: tuple[float, ...]) -> SyntheticSeries:
    return SyntheticSeries(
        series_id="sintetica-prueba",
        start=START,
        values=values,
        block_hour=1,
        synthetic=True,
    )


def base_question() -> TemporalQuestion:
    a, _b = build_pair()
    return TemporalQuestion(
        question_id="tqa-v1-prueba-maximum",
        family="maximum",
        series_ids=(a.series_id,),
        observation_ids=a.observation_ids[:4],
        window_start=START,
        window_end_exclusive=START + timedelta(hours=4),
        prompt="¿Cuál es el valor máximo de PM2.5 de la ventana?",
        answer=answer_maximum(a.values[:4]),
    )


def offset_hours(question: TemporalQuestion, origin: datetime) -> int:
    return int((question.window_start - origin).total_seconds() // 3600)


def test_series_must_be_marked_synthetic():
    with pytest.raises(ValueError, match="sintética"):
        SyntheticSeries(
            series_id="sintetica-x",
            start=START,
            values=(1.0,),
            block_hour=1,
            synthetic=False,
        )


def test_series_rejects_non_finite_or_negative_values():
    with pytest.raises(ValueError, match="finitos"):
        manual_series((1.0, float("nan"), 2.0))
    with pytest.raises(ValueError, match="negativos"):
        manual_series((1.0, -0.5, 2.0))


def test_build_is_deterministic_and_traceable():
    first_a, first_b = build_pair()
    second_a, second_b = build_pair()
    assert first_a == second_a
    assert first_b == second_b
    changed = build_synthetic_series(
        series_id="sintetica-otra", seed=2027, hours=HOURS, block_hour=24, start=START
    )
    assert changed.values != first_a.values
    for series in (first_a, first_b):
        assert series.synthetic is True
        assert len(series.values) == HOURS
        assert all(value >= 0 for value in series.values)
        assert len(set(series.observation_ids)) == HOURS
        assert all(oid.startswith(f"obs:{series.series_id}:") for oid in series.observation_ids)


def test_builder_requires_enough_hours_inner_block_and_timezone():
    with pytest.raises(ValueError, match="120"):
        build_synthetic_series(series_id="s", seed=1, hours=48, block_hour=24, start=START)
    with pytest.raises(ValueError, match="bloque"):
        build_synthetic_series(series_id="s", seed=1, hours=HOURS, block_hour=HOURS, start=START)
    with pytest.raises(ValueError, match="zona horaria"):
        build_synthetic_series(
            series_id="s", seed=1, hours=HOURS, block_hour=24, start=START.replace(tzinfo=None)
        )


def test_generation_covers_four_families_deterministically():
    _a, _b, questions = build_all()
    assert questions == build_all()[2]
    assert len(questions) == 4
    assert {question.family for question in questions} == set(QA_FAMILIES)
    assert len({question.question_id for question in questions}) == 4


def test_questions_carry_traceable_fields():
    a, b, questions = build_all()
    for question in questions:
        assert question.series_ids
        assert set(question.series_ids) <= {a.series_id, b.series_id}
        assert question.observation_ids
        assert len(set(question.observation_ids)) == len(question.observation_ids)
        prefixes = tuple(f"obs:{sid}:" for sid in question.series_ids)
        assert all(oid.startswith(prefixes) for oid in question.observation_ids)
        assert question.window_start < question.window_end_exclusive
        assert (question.window_end_exclusive - question.window_start) % timedelta(hours=1) == (
            timedelta(0)
        )
        assert question.prompt and question.answer


def test_qa_windows_are_pairwise_disjoint_per_series():
    a, b, questions = build_all()
    for series in (a, b):
        windows = sorted(
            (question.window_start, question.window_end_exclusive, question.question_id)
            for question in questions
            if series.series_id in question.series_ids
        )
        for (_start, previous_end, _id), (next_start, _end, _id2) in zip(
            windows, windows[1:], strict=False
        ):
            assert previous_end <= next_start


def test_round_trip_recomputes_every_answer():
    a, b, questions = build_all()
    series_by_id = mapping(a, b)
    for question in questions:
        assert verify_answer(question, series_by_id) is True
        assert recompute_answer(question, series_by_id) == question.answer


def test_round_trip_rejects_tampered_answer():
    a, b, questions = build_all()
    series_by_id = mapping(a, b)
    for question in questions:
        assert verify_answer(replace(question, answer="valor alterado"), series_by_id) is False


def test_round_trip_rejects_unknown_series_and_out_of_range_window():
    a, _b, questions = build_all()
    question = questions[0]
    with pytest.raises(ValueError, match="desconocidas"):
        recompute_answer(question, {})
    shifted = replace(
        question,
        window_start=START + timedelta(hours=200),
        window_end_exclusive=START + timedelta(hours=224),
    )
    with pytest.raises(ValueError, match="fuera de la serie"):
        recompute_answer(shifted, {a.series_id: a})


def test_answer_maximum_returns_value_with_unit():
    assert answer_maximum((1.0, 5.0, 5.0, 2.0)) == f"5.00 {PM25_UNIT}"
    with pytest.raises(ValueError):
        answer_maximum(())


def test_answer_moment_returns_first_maximum_instant():
    values = (1.0, 5.0, 5.0, 2.0)
    assert answer_moment(values, start=START) == "2026-01-01T01:00:00+00:00"


def test_answer_trend_compares_halves_without_causes():
    assert answer_trend((1.0, 2.0, 3.0, 4.0)) == "aumento"
    assert answer_trend((4.0, 3.0, 2.0, 1.0)) == "disminución"
    assert answer_trend((1.0, 1.0, 1.0, 1.0)) == "sin cambio"
    with pytest.raises(ValueError):
        answer_trend((1.0, 2.0, 3.0))


def test_answer_comparison_prefers_greater_mean_and_marks_ties():
    assert (
        answer_comparison((2.0, 2.0), (1.0, 1.0), series_id_a="serie-a", series_id_b="serie-b")
        == "serie-a"
    )
    assert (
        answer_comparison((1.0, 1.0), (3.0, 3.0), series_id_a="serie-a", series_id_b="serie-b")
        == "serie-b"
    )
    assert (
        answer_comparison((1.0, 2.0), (2.0, 1.0), series_id_a="serie-a", series_id_b="serie-b")
        == "empate"
    )


def test_generated_maximum_and_moment_match_window_values():
    a, b, questions = build_all()
    maximum = next(question for question in questions if question.family == "maximum")
    first = offset_hours(maximum, START)
    values = a.values[first : first + 24]
    assert maximum.answer == f"{max(values):.2f} {PM25_UNIT}"
    moment = next(question for question in questions if question.family == "moment")
    start = offset_hours(moment, START)
    index = max(range(24), key=lambda i: a.values[start + i])
    assert moment.answer == (START + timedelta(hours=start + index)).isoformat()


def test_generated_trend_and_comparison_match_means():
    a, b, questions = build_all()
    trend = next(question for question in questions if question.family == "trend")
    first = offset_hours(trend, START)
    values = a.values[first : first + 48]
    first_mean = fmean(values[:24])
    second_mean = fmean(values[24:])
    expected = (
        "aumento"
        if second_mean > first_mean
        else "disminución"
        if second_mean < first_mean
        else "sin cambio"
    )
    assert trend.answer == expected
    comparison = next(question for question in questions if question.family == "comparison")
    start = offset_hours(comparison, START)
    a_mean = fmean(a.values[start : start + 24])
    b_mean = fmean(b.values[start : start + 24])
    if a_mean == b_mean:
        expected_id = "empate"
    else:
        expected_id = a.series_id if a_mean > b_mean else b.series_id
    assert comparison.answer == expected_id


@pytest.mark.parametrize(("family", "pattern"), sorted(ANSWER_PATTERNS.items()))
def test_answer_text_is_only_the_computed_value(family, pattern):
    _a, _b, questions = build_all()
    question = next(question for question in questions if question.family == family)
    assert re.fullmatch(pattern, question.answer)
    assert not re.search(r"porque|debido|causa", question.answer)


def test_maximum_and_moment_answers_do_not_leak_into_prompts():
    _a, _b, questions = build_all()
    for question in questions:
        if question.family in {"maximum", "moment"}:
            assert question.answer not in question.prompt


def test_question_validates_window_and_text():
    question = base_question()
    with pytest.raises(ValueError, match="hora exacta"):
        replace(question, window_start=question.window_start + timedelta(minutes=30))
    with pytest.raises(ValueError, match="zona horaria"):
        replace(question, window_start=question.window_start.replace(tzinfo=None))
    with pytest.raises(ValueError, match="ventana"):
        replace(question, window_end_exclusive=question.window_start)
    with pytest.raises(ValueError, match="Familia"):
        replace(question, family="forecast")
    with pytest.raises(ValueError, match="respuesta"):
        replace(question, answer=" ")


def test_generation_requires_two_distinct_aligned_series():
    a, b = build_pair()
    with pytest.raises(ValueError, match="distintos"):
        generate_questions(a, a)
    short = replace(a, values=a.values[:96])
    with pytest.raises(ValueError, match="120"):
        generate_questions(short, b)
    late = build_synthetic_series(
        series_id="sintetica-d",
        seed=9,
        hours=HOURS,
        block_hour=24,
        start=START + timedelta(hours=1),
    )
    with pytest.raises(ValueError, match="origen"):
        generate_questions(a, late)


def test_qa_fields_are_disjoint_from_forecast_target_columns():
    assert QUESTION_FIELDS == {
        "question_id",
        "family",
        "series_ids",
        "observation_ids",
        "window_start",
        "window_end_exclusive",
        "prompt",
        "answer",
    }
    assert QUESTION_FIELDS.isdisjoint(FORECAST_TARGET_FIELDS)
    assert FORECAST_TARGET_FIELDS.isdisjoint(QUESTION_FIELDS)


def test_qa_case_cannot_hold_forecast_target_values():
    question = base_question()
    with pytest.raises(TypeError):
        replace(question, target_values=(1.0, 2.0))
    with pytest.raises(TypeError):
        replace(question, target_mean=1.0)


def test_qa_fields_hold_identifiers_not_measured_sequences():
    _a, _b, questions = build_all()
    for question in questions:
        for field in fields(TemporalQuestion):
            value = getattr(question, field.name)
            if isinstance(value, (list, tuple)):
                assert all(isinstance(item, str) for item in value)


def test_validate_separation_accepts_disjoint_forecast_windows():
    a, b, questions = build_all()
    later = ForecastTargetInterval(
        series_id=a.series_id,
        target_start=START + timedelta(hours=130),
        target_end=START + timedelta(hours=135),
    )
    other = ForecastTargetInterval(
        series_id=b.series_id,
        target_start=START,
        target_end=START + timedelta(hours=5),
    )
    assert validate_qa_separated(questions, [later, other]) is None


def test_validate_separation_rejects_overlapping_and_equal_windows():
    _a, _b, questions = build_all()
    inside = ForecastTargetInterval(
        series_id="sintetica-a",
        target_start=START + timedelta(hours=50),
        target_end=START + timedelta(hours=55),
    )
    with pytest.raises(ValueError) as overlap:
        validate_qa_separated(questions, [inside])
    assert inside.series_id in str(overlap.value)
    equal = ForecastTargetInterval(
        series_id="sintetica-a",
        target_start=START + timedelta(hours=48),
        target_end=START + timedelta(hours=71),
    )
    with pytest.raises(ValueError, match="solapa"):
        validate_qa_separated(questions, [equal])


def test_qa_module_does_not_import_forecast_or_database_modules():
    source = inspect.getsource(temporal_qa_module)
    for forbidden in ("senamhi_windows", "senamhi_splits", "duckdb", "pyarrow"):
        assert not re.search(rf"^\s*(?:from|import)\s+\S*{forbidden}", source, re.MULTILINE)


def test_verificacion_exige_las_observaciones_de_ambas_series():
    a, b, questions = build_all()
    comparison = questions[-1]
    altered = replace(
        comparison, observation_ids=(*comparison.observation_ids[:-1], b.observation_ids[0])
    )
    with pytest.raises(ValueError, match="observaci"):
        verify_answer(altered, mapping(a, b))


def test_ventanas_y_momento_usan_horas_transcurridas_al_cambiar_el_reloj():
    a, b = build_pair()
    inicio = datetime(2026, 3, 7, tzinfo=ZoneInfo("America/New_York"))
    utc = inicio.astimezone(UTC)
    local_questions = generate_questions(replace(a, start=inicio), replace(b, start=inicio))
    assert local_questions == generate_questions(replace(a, start=utc), replace(b, start=utc))


def test_instante_del_maximo_cruza_la_hora_repetida():
    inicio = datetime(2026, 11, 1, 1, tzinfo=ZoneInfo("America/New_York"), fold=0)
    assert answer_moment((1, 2), start=inicio) == "2026-11-01T06:00:00+00:00"


def test_separacion_distingue_las_dos_horas_repetidas():
    primera = datetime(2026, 11, 1, 1, tzinfo=ZoneInfo("America/New_York"), fold=0)
    segunda = primera.replace(fold=1).astimezone(UTC)
    pregunta = replace(
        base_question(), window_start=segunda, window_end_exclusive=segunda + timedelta(hours=1)
    )
    objetivo = ForecastTargetInterval(pregunta.series_ids[0], primera, primera)
    validate_qa_separated([pregunta], [objetivo])
