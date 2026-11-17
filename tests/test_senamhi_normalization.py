"""Pruebas sintéticas de la entrega 1 de #13: lectura streaming y conversión trazable."""

import csv
import hashlib
import io
from datetime import UTC, datetime
from pathlib import Path

import pytest

from airaware.normalization import Rejection, convert_row, iter_batches, stream_observations
from airaware.schemas import Observation
from airaware.senamhi_preparation import PreparationPolicy, load_policy, observation

HEADER = ["FECHA", "HORA", "PM10", "PM2_5", "NO2", "ESTACION"]
SENAL = ("PM10", "PM2_5", "NO2")


def fila(
    fecha: str = "20240531",
    hora: str = "153045",
    pm10: str = "12.5",
    pm25: str = "0",
    no2: str = "ND",
    estacion: str = "CAMPO_DE_MARTE",
) -> list[str]:
    return [fecha, hora, pm10, pm25, no2, estacion]


def write_csv(
    path: Path, rows: list[list[str]], *, bom: bool = False, header: list[str] | None = None
) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=",")
    writer.writerow(HEADER if header is None else header)
    writer.writerows(rows)
    data = buffer.getvalue().encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def synthetic_policy(sha256: str) -> PreparationPolicy:
    base = load_policy().model_dump()
    return PreparationPolicy.model_validate({**base, "input_sha256": sha256})


def resultados(path: Path, policy: PreparationPolicy) -> list:
    return [
        outcome
        for batch in stream_observations(path, policy, batch_size=2)
        for row in batch
        for outcome in row
    ]


def test_bom_coma_y_comillas_fluyen_como_observaciones_contractuales(tmp_path):
    source = tmp_path / "original.csv"
    sha = write_csv(source, [fila(estacion='VILLA "A", SATÉLITE')], bom=True)
    policy = synthetic_policy(sha)
    outcomes = resultados(source, policy)
    assert len(outcomes) == 3
    assert all(isinstance(o, Observation) for o in outcomes)
    assert outcomes[0].raw_fields["ESTACION"] == 'VILLA "A", SATÉLITE'
    assert outcomes[0].raw_fields["FECHA"] == "20240531"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == sha


@pytest.mark.parametrize(
    "header",
    [
        ["FECHA", "HORA", "PM10", "PM2_5", "ESTACION"],
        ["FECHA", "HORA", "PM10", "PM2_5", "NO2", "PM10", "ESTACION"],
    ],
)
def test_encabezado_invalido_se_rechaza_antes_de_convertir(tmp_path, header):
    source = tmp_path / "original.csv"
    sha = write_csv(source, [fila()], header=header)
    with pytest.raises(ValueError, match="Encabezado"):
        list(stream_observations(source, synthetic_policy(sha), batch_size=10))


def test_archivo_vacio_se_rechaza_por_encabezado_ausente(tmp_path):
    source = tmp_path / "vacio.csv"
    source.write_bytes(b"")
    sha = hashlib.sha256(b"").hexdigest()
    with pytest.raises(ValueError, match="Encabezado"):
        list(stream_observations(source, synthetic_policy(sha), batch_size=10))


def test_sha_distinto_detiene_antes_de_convertir(tmp_path):
    source = tmp_path / "original.csv"
    write_csv(source, [fila()])
    with pytest.raises(ValueError, match="SHA-256"):
        list(stream_observations(source, synthetic_policy("0" * 64), batch_size=2))


def test_numeracion_logica_encabezado_1_y_procedencia_trazable(tmp_path):
    source = tmp_path / "original.csv"
    sha = write_csv(source, [fila(), fila(pm10="3.5")])
    outcomes = resultados(source, synthetic_policy(sha))
    assert [o.provenance.record for o in outcomes] == [2, 2, 2, 3, 3, 3]
    first = outcomes[0]
    assert first.observation_id == f"{sha}:2:PM10"
    assert first.provenance.source_id == "senamhi-lima-csv"
    assert first.provenance.sha256 == sha
    assert first.provenance.sheet is None


def test_la_adaptacion_streaming_no_cambia_los_valores_del_contrato(tmp_path):
    source = tmp_path / "original.csv"
    sha = write_csv(source, [fila()])
    policy = synthetic_policy(sha)
    streamed = resultados(source, policy)
    direct = [observation(dict(zip(HEADER, fila(), strict=True)), s, 2, policy) for s in SENAL]
    assert [o.model_dump(mode="json") for o in streamed] == [
        d.model_dump(mode="json") for d in direct
    ]
    first = streamed[0]
    assert first.observed_at == datetime(2024, 5, 31, 15, 30, 45, tzinfo=UTC)
    assert first.time_raw == {"FECHA": "20240531", "HORA": "153045"}
    assert first.unit == "ug/m3" and first.unit_raw is None
    assert "units_inferred" in "|".join(first.semantic_evidence)
    assert first.quality == "unknown"
    assert first.start is None and first.end is None and first.available_at is None
    assert first.station_id is None and first.sensor_id is None
    assert first.value == 12.5 and first.value_raw == "12.5"
    assert first.raw_fields["ESTACION"] == "CAMPO_DE_MARTE"


@pytest.mark.parametrize(
    ("token", "status", "value"),
    [
        ("", "missing", None),
        ("-", "missing", None),
        ("NA", "missing", None),
        ("N/A", "missing", None),
        ("NULL", "missing", None),
        ("<1", "censored", None),
        ("ND", "unresolved", None),
        ("NaN", "nonfinite", None),
        ("0", "finite", 0.0),
        ("7.25", "finite", 7.25),
    ],
)
def test_clases_de_valor_distintas_con_token_original(tmp_path, token, status, value):
    source = tmp_path / "original.csv"
    sha = write_csv(source, [fila(pm25=token)])
    pm25 = resultados(source, synthetic_policy(sha))[1]
    assert pm25.parameter_raw == "PM2_5"
    assert pm25.value_status == status
    assert pm25.value == value
    assert pm25.value_raw == token


@pytest.mark.parametrize(
    ("fecha", "hora"),
    [("20240132", "0"), ("20240230", "153045"), ("20240531", "240000"), ("20240531", "126000")],
)
def test_fecha_u_hora_invalida_rechaza_las_tres_senales(tmp_path, fecha, hora):
    source = tmp_path / "original.csv"
    sha = write_csv(source, [fila(fecha=fecha, hora=hora)])
    outcomes = resultados(source, synthetic_policy(sha))
    assert [r.signal for r in outcomes] == list(SENAL)
    for rejection in outcomes:
        assert not isinstance(rejection, Observation)
        assert rejection.provenance.record == 2
        assert rejection.provenance.sha256 == sha
        assert "FECHA/HORA" in rejection.error
        assert rejection.raw_fields["FECHA"] == fecha
        assert rejection.raw_fields["HORA"] == hora
    assert [r.raw for r in outcomes] == ["12.5", "0", "ND"]


def test_filas_malformadas_se_rechazan_sin_perdida_silenciosa(tmp_path):
    source = tmp_path / "original.csv"
    sha = write_csv(source, [fila()[:4], fila(), fila() + ["extra"], []])
    outcomes = resultados(source, synthetic_policy(sha))
    assert len(outcomes) == 12
    corta, valida, larga, vacia = (outcomes[i : i + 3] for i in range(0, 12, 3))
    assert all(isinstance(o, Observation) for o in valida)
    for group, fragmento in ((corta, "incompleta"), (larga, "de más"), (vacia, "incompleta")):
        assert [r.signal for r in group] == list(SENAL)
        assert all(fragmento in r.error for r in group)
    assert all(r.provenance.record == 2 for r in corta)
    assert all(r.provenance.record == 4 for r in larga)
    assert all(r.provenance.record == 5 for r in vacia)
    assert corta[0].raw == "12.5" and corta[2].raw is None
    assert set(corta[0].raw_fields) == {"FECHA", "HORA", "PM10", "PM2_5"}
    assert larga[0].extra_fields == ["extra"]
    assert vacia[0].raw_fields == {}


def test_filas_repetidas_se_conservan_sin_resolucion_de_identidad(tmp_path):
    source = tmp_path / "original.csv"
    sha = write_csv(source, [fila(), fila()])
    outcomes = resultados(source, synthetic_policy(sha))
    assert len(outcomes) == 6
    assert all(isinstance(o, Observation) for o in outcomes)
    assert len({o.observation_id for o in outcomes}) == 6
    for signal_index in range(3):
        a, b = outcomes[signal_index], outcomes[signal_index + 3]
        assert a.observation_id != b.observation_id
        assert a.value == b.value
        assert a.raw_fields == b.raw_fields
        assert a.station_id is None and b.station_id is None
        assert a.provenance.record == 2 and b.provenance.record == 3


def test_lotes_configurables_perezosos_y_totales(tmp_path):
    pulls = 0

    def records():
        nonlocal pulls
        for _ in range(9):
            pulls += 1
            yield fila()

    policy = load_policy()
    batches = iter_batches(records(), list(HEADER), policy, batch_size=4)
    first = next(batches)
    assert len(first) == 4
    assert pulls == 4
    remaining = list(batches)
    assert [len(b) for b in remaining] == [4, 1]
    outcomes = [o for batch in [first, *remaining] for row in batch for o in row]
    assert len(outcomes) == 27
    assert all(isinstance(o, (Observation, Rejection)) for o in outcomes)
    with pytest.raises(ValueError):
        iter_batches(records(), list(HEADER), policy, batch_size=0)


def test_registro_ilegible_genera_rechazos_trazables(tmp_path):
    source = tmp_path / "original.csv"
    write_csv(source, [fila()])
    source.write_bytes(source.read_bytes() + b'20240601,50000,"sin cerrar\n')
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    outcomes = resultados(source, synthetic_policy(sha))
    assert len(outcomes) == 6
    assert all(isinstance(o, Observation) for o in outcomes[:3])
    assert all(isinstance(r, Rejection) for r in outcomes[3:])
    assert all("ilegible" in r.error for r in outcomes[3:])
    assert {r.provenance.record for r in outcomes[3:]} == {3}


def test_error_de_programacion_en_observacion_se_propaga_sin_enmascararse(monkeypatch):
    def observacion_rota(row, signal, record, policy):
        raise RuntimeError("defecto de programación inyectado")

    monkeypatch.setattr("airaware.normalization.convert.observation", observacion_rota)
    with pytest.raises(RuntimeError, match="defecto de programación"):
        convert_row(2, fila(), list(HEADER), synthetic_policy("0" * 64))
