"""Validar el intercambio sintético antes de usar lecturas de estaciones reales."""

import json
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / "docs/methodology/episodios-v1"


def test_ventanas_y_soluciones_coinciden_por_id():
    inputs = json.loads((FIXTURE / "inferencia/ventanas.json").read_text())
    answers = json.loads((FIXTURE / "evaluacion/objetivos.json").read_text())
    assert inputs["version"] == answers["version"] == "lima-episode-fixture-v1"
    assert set(inputs) == {
        "version",
        "unit",
        "window_id",
        "station_key",
        "origin_at",
        "threshold_ug_m3",
        "history",
    }
    ids = inputs["window_id"]
    rows = {row["window_id"]: row for row in answers["rows"]}
    assert len(set(ids)) == len(ids) == len(rows) == len(answers["rows"])
    assert set(ids) == set(rows) and ids != list(rows)
    for key, history, limit in zip(ids, inputs["history"], inputs["threshold_ug_m3"], strict=True):
        row = rows[key]
        future = row["targets"]
        assert len(history) == 24 and len(future) == 6
        assert row["ongoing_at_origin"] == (history[-1] >= limit)
        if None in future:
            assert row["event"] is None and row["first_onset_hour"] is None
            continue
        assert row["event"] == any(value >= limit for value in future)
        pairs = zip([history[-1], *future[:-1]], future, strict=True)
        onset = next(
            (hour for hour, (prev, value) in enumerate(pairs, 1) if prev < limit <= value), None
        )
        assert row["first_onset_hour"] == onset
