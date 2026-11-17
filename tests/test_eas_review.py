import csv
import json

import duckdb
import pytest

from airaware.eas_review import CONTEXT, review


def test_long_eas_keeps_conflicts_censoring_and_campaigns_separate(tmp_path):
    (tmp_path / "raw").mkdir()
    path = tmp_path / "raw" / "input.csv"
    fields = [
        "Número.de.informe",
        "Nombre.del.punto",
        "Este",
        "Norte",
        "Zona",
        "Datum",
        "Nombre.de.la.Evaluación",
        "Descripción.de.ubicación",
        "Periodo",
        "Fecha.inicio",
        "Hora.inicio",
        "Fecha.fin",
        "Hora.fin",
        "Valor",
        "Parámetro",
        "Unidad.de.medida",
        "Etapa",
        "Tipo.de.muestra",
        "Tipo.de.análisis",
        "Procedencia.de.la.Muestra",
        "Procedencia.Especifica.de.la.Muestra",
        "Altitud",
    ]
    rows = []
    for i in range(32):
        row = dict.fromkeys(fields, "-")
        row.update(
            {
                "Número.de.informe": "report1",
                "Nombre.del.punto": "CA-01",
                "Nombre.de.la.Evaluación": "Lima",
                "Periodo": "1 hora",
                "Fecha.inicio": str(44927 + i // 24),
                "Hora.inicio": f"{i % 24:02}:00:00",
                "Valor": "10",
                "Parámetro": "Material particulado PM2,5",
                "Unidad.de.medida": "µg/m³",
            }
        )
        rows.append(row)
    rows += [
        rows[0].copy(),
        rows[5] | {"Valor": "20"},
        rows[6] | {"Valor": "<1"},
        rows[7] | {"Número.de.informe": "report2"},
        rows[8] | {"Valor": "ND"},
        rows[9] | {"Parámetro": "PM2,5 (25 micras)"},
    ]
    with path.open("w") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    output = tmp_path / "result"
    review(path, output)
    summary = json.loads((output / "summary.json").read_text())
    assert summary["rows"] == 38
    assert summary["scientific_valid_windows"] is None
    assert summary["date_hypothesis"] == "excel-1900-unconfirmed"
    assert summary["value_counts"]["censored"] == 1
    assert summary["value_counts"]["unresolved"] == 1
    assert summary["conflict_slots"] == 1
    assert summary["windows"][0]["complete"] == 0  # conflicts/censoring break the 30-hour run
    assert summary["inputs_unchanged"]
    assert all(r["candidate_lima"] for r in summary["coverage"])
    with duckdb.connect() as c:
        result = c.execute(
            "SELECT count(*) FROM read_parquet(?) WHERE ts=TIMESTAMP '2023-01-01 05:00:00'",
            [str(output / "points.parquet")],
        ).fetchone()
        assert result == (0,)
    with pytest.raises(ValueError):
        review(path, output)


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "ND", "<L.C.", "-"])
def test_nonfinite_unknown_and_censored_cannot_form_windows(tmp_path, bad):
    raw = tmp_path / "raw"
    raw.mkdir()
    path = raw / "input.csv"
    columns = list(
        dict.fromkeys(
            [
                *CONTEXT,
                "Descripción.de.ubicación",
                "Fecha.inicio",
                "Hora.inicio",
                "Fecha.fin",
                "Hora.fin",
                "Valor",
            ]
        )
    )
    with path.open("w") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for i in range(30):
            row = dict.fromkeys(columns, "-")
            row.update(
                {
                    "Número.de.informe": "r",
                    "Nombre.del.punto": "p",
                    "Periodo": "1 hora",
                    "Parámetro": "Material particulado PM2,5",
                    "Unidad.de.medida": "µg/m³",
                    "Fecha.inicio": str(44927 + i // 24),
                    "Hora.inicio": f"{i % 24:02}:00:00",
                    "Valor": bad if i == 15 else "10",
                }
            )
            writer.writerow(row)
    review(path, tmp_path / "result")
    summary = json.loads((tmp_path / "result" / "summary.json").read_text())
    assert sum(r["complete"] for r in summary["windows"]) == 0
    assert sum(summary["value_counts"].values()) == 30
