"""Pruebas sintéticas de la entrega 2 de #13: Parquet determinista, particionado y atómico."""

import csv
import hashlib
import io
import json
from importlib.metadata import version
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from airaware.normalization import (
    SIGNALS,
    Manifest,
    Rejection,
    iter_observations,
    stream_observations,
    write_parquet_output,
)
from airaware.schemas import Observation
from airaware.senamhi_preparation import PreparationPolicy, load_policy

HEADER = ["FECHA", "HORA", "PM10", "PM2_5", "NO2", "ESTACION"]
VALUE_STATUSES = ("finite", "censored", "missing", "unresolved", "nonfinite")


def fila(
    fecha: str = "20240531",
    hora: str = "153045",
    pm10: str = "12.5",
    pm25: str = "0",
    no2: str = "ND",
    estacion: str = "CAMPO_DE_MARTE",
) -> list[str]:
    return [fecha, hora, pm10, pm25, no2, estacion]


def write_csv(path: Path, rows: list[list[str]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=",")
    writer.writerow(HEADER)
    writer.writerows(rows)
    data = buffer.getvalue().encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def synthetic_policy(sha256: str) -> PreparationPolicy:
    base = load_policy().model_dump()
    return PreparationPolicy.model_validate({**base, "input_sha256": sha256})


def stream(path: Path, policy: PreparationPolicy, batch_size: int = 2):
    from airaware.normalization import stream_observations

    return stream_observations(path, policy, batch_size=batch_size)


def tree(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())


def digest_files(root: Path) -> dict[str, str]:
    return {
        relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
        for relative in tree(root)
    }


def test_particiones_fuente_anio_mes_utc_con_limites_de_mes_y_anio(tmp_path):
    source = tmp_path / "original.csv"
    sha = write_csv(
        source,
        [
            fila(fecha="20240531", hora="233059"),
            fila(fecha="20240601", hora="000005"),
            fila(fecha="20241231", hora="235959"),
            fila(fecha="20250101", hora="000100"),
        ],
    )
    policy = synthetic_policy(sha)
    manifest = write_parquet_output(
        stream(source, policy, batch_size=2), policy, tmp_path / "salida"
    )
    partitions = {
        str(p.relative_to(tmp_path / "salida")) for p in (tmp_path / "salida").glob("*/year=*/*")
    }
    assert partitions == {
        "source_id=senamhi-lima-csv/year=2024/month=05",
        "source_id=senamhi-lima-csv/year=2024/month=06",
        "source_id=senamhi-lima-csv/year=2024/month=12",
        "source_id=senamhi-lima-csv/year=2025/month=01",
    }
    for partition in partitions:
        assert (tmp_path / "salida" / partition / "part-00000.parquet").is_file()
    assert [o.provenance.record for o in iter_observations(tmp_path / "salida")] == [
        2,
        2,
        2,
        3,
        3,
        3,
        4,
        4,
        4,
        5,
        5,
        5,
    ]
    assert manifest.counts.input_rows == 4


def test_limite_mes_y_anio_no_se_reparte_por_hora_local(tmp_path):
    source = tmp_path / "original.csv"
    sha = write_csv(
        source,
        [fila(fecha="20240601", hora="000005"), fila(fecha="20250101", hora="000100")],
    )
    policy = synthetic_policy(sha)
    write_parquet_output(stream(source, policy), policy, tmp_path / "salida")
    # En America/Lima ambos instantes caen el mes/año anterior (UTC-5); la partición debe ser UTC.
    partitions = {
        str(p.relative_to(tmp_path / "salida")) for p in (tmp_path / "salida").glob("*/year=*/*")
    }
    assert partitions == {
        "source_id=senamhi-lima-csv/year=2024/month=06",
        "source_id=senamhi-lima-csv/year=2025/month=01",
    }
    assert not (
        tmp_path / "salida" / "source_id=senamhi-lima-csv" / "year=2024" / "month=05"
    ).exists()
    assert not (
        tmp_path / "salida" / "source_id=senamhi-lima-csv" / "year=2024" / "month=12"
    ).exists()


def test_lotes_varios_escriben_row_groups_incrementales(tmp_path):
    source = tmp_path / "original.csv"
    sha = write_csv(
        source,
        [
            fila(fecha="20240531", hora="233059"),
            fila(fecha="20240531", hora="234500"),
            fila(fecha="20240531", hora="235959"),
            fila(fecha="20240601", hora="000005"),
        ],
    )
    policy = synthetic_policy(sha)
    salida = tmp_path / "salida"
    write_parquet_output(stream(source, policy, batch_size=2), policy, salida)
    archivo = (
        salida / "source_id=senamhi-lima-csv" / "year=2024" / "month=05" / "part-00000.parquet"
    )
    parquet = pq.ParquetFile(archivo)
    # Dos lotes tocan la partición 2024-05; cada lote se anexa como su propio row group.
    assert parquet.metadata.num_row_groups == 2
    assert parquet.metadata.num_rows == 9
    groups = [
        parquet.metadata.row_group(i).num_rows for i in range(parquet.metadata.num_row_groups)
    ]
    assert groups == [6, 3]


def test_ida_y_vuelta_conserva_el_contrato_anidado(tmp_path):
    source = tmp_path / "original.csv"
    sha = write_csv(
        source,
        [
            fila(pm10="0", pm25="<1", no2="NA", estacion='VILLA "A", SATÉLITE'),
            fila(pm10="ND", pm25="NaN", no2="7.25"),
        ],
    )
    policy = synthetic_policy(sha)
    salida = tmp_path / "salida"
    manifest = write_parquet_output(stream(source, policy, batch_size=2), policy, salida)
    assert manifest.counts.observations.by_class == {
        "finite": 2,
        "censored": 1,
        "missing": 1,
        "unresolved": 1,
        "nonfinite": 1,
    }
    esperados = [
        outcome.model_dump(mode="json")
        for batch in stream(source, policy, batch_size=2)
        for row in batch
        for outcome in row
        if isinstance(outcome, Observation)
    ]
    leidos = [o.model_dump(mode="json") for o in iter_observations(salida)]
    assert leidos == esperados
    primero = iter_observations(salida).__next__()
    assert primero.value == 0.0 and primero.value_raw == "0"
    assert primero.raw_fields["ESTACION"] == 'VILLA "A", SATÉLITE'
    assert primero.time_raw == {"FECHA": "20240531", "HORA": "153045"}
    assert primero.semantic_evidence and primero.parent_ids == []
    assert primero.provenance.sheet is None
    assert primero.observed_at is not None and primero.observed_at.utcoffset() is not None
    parquet = pq.ParquetFile(
        salida / "source_id=senamhi-lima-csv" / "year=2024" / "month=05" / "part-00000.parquet"
    )
    schema = parquet.schema_arrow
    assert schema.field("observed_at").type == pa.timestamp("us", tz="UTC")
    assert schema.field("raw_fields").type == pa.map_(pa.string(), pa.string())
    assert schema.field("time_raw").type == pa.map_(pa.string(), pa.string())
    assert schema.field("semantic_evidence").type == pa.list_(
        pa.field("item", pa.string(), nullable=False)
    )
    assert schema.field("observation_id").nullable is False
    assert schema.field("value").type == pa.float64()


def test_repeticiones_se_conservan_con_orden_de_entrada(tmp_path):
    source = tmp_path / "original.csv"
    sha = write_csv(source, [fila(), fila()])
    policy = synthetic_policy(sha)
    salida = tmp_path / "salida"
    manifest = write_parquet_output(stream(source, policy, batch_size=2), policy, salida)
    leidos = list(iter_observations(salida))
    assert len(leidos) == 6
    assert len({o.observation_id for o in leidos}) == 6
    assert [o.provenance.record for o in leidos] == [2, 2, 2, 3, 3, 3]
    assert manifest.counts.observations.total == 6
    assert manifest.counts.rejections.total == 0


def test_dos_ejecuciones_iguales_producen_parquet_jsonl_y_manifiesto_byte_a_byte(tmp_path):
    filas = [
        fila(fecha="20240531", hora="233059"),
        fila(pm25="7.25", fecha="20240601", hora="126000"),
        fila(pm25="3.5", fecha="20240601", hora="000005", estacion="VILLA_EL_SALVADOR"),
    ]
    shas = []
    for indice in ("a", "b"):
        source = tmp_path / f"original_{indice}.csv"
        shas.append(write_csv(source, filas))
    assert shas[0] == shas[1]
    policy_a = synthetic_policy(shas[0])
    policy_b = synthetic_policy(shas[1])
    salida_a = tmp_path / "salida_a"
    salida_b = tmp_path / "salida_b"
    manifest = write_parquet_output(
        stream(tmp_path / "original_a.csv", policy_a, batch_size=3), policy_a, salida_a
    )
    write_parquet_output(
        stream(tmp_path / "original_b.csv", policy_b, batch_size=3), policy_b, salida_b
    )
    assert tree(salida_a) == tree(salida_b)
    assert digest_files(salida_a) == digest_files(salida_b)
    jsonl = [p for p in tree(salida_a) if p.endswith("rejections.jsonl")][0]
    assert len((salida_a / jsonl).read_text(encoding="utf-8").splitlines()) == 3
    bytes_a = (salida_a / "manifest.json").read_bytes()
    assert bytes_a == (salida_b / "manifest.json").read_bytes()
    assert "salida_a" not in bytes_a.decode("utf-8")
    cargado = Manifest.model_validate(json.loads(bytes_a.decode("utf-8")))
    assert cargado == manifest


def test_manifiesto_reconcilia_conteos_y_procedencia(tmp_path):
    source = tmp_path / "original.csv"
    filas = [fila(), fila(pm10="NA", fecha="20240601", hora="153045"), fila()[:4]]
    sha = write_csv(source, filas)
    policy = synthetic_policy(sha)
    salida = tmp_path / "salida"
    manifest = write_parquet_output(stream(source, policy, batch_size=2), policy, salida)
    assert manifest.policy_id == policy.policy_id
    assert manifest.source_id == policy.source_id
    assert manifest.input_sha256 == sha
    assert (
        manifest.policy_sha256
        == hashlib.sha256(policy.model_dump_json().encode("utf-8")).hexdigest()
    )
    assert manifest.library == "pyarrow"
    assert manifest.library_version == version("pyarrow")
    assert manifest.counts.input_rows == 3
    total_observaciones = 6
    total_rechazos = 3
    assert manifest.counts.observations.total == total_observaciones
    assert manifest.counts.rejections.total == total_rechazos
    assert manifest.counts.observations.total + manifest.counts.rejections.total == 3 * 3
    assert set(manifest.counts.observations.by_signal) == set(SIGNALS)
    assert set(manifest.counts.rejections.by_signal) == set(SIGNALS)
    for senal in SIGNALS:
        assert (
            manifest.counts.observations.by_signal[senal]
            + manifest.counts.rejections.by_signal[senal]
            == 3
        )
    assert sum(manifest.counts.observations.by_signal.values()) == total_observaciones
    assert sum(manifest.counts.rejections.by_signal.values()) == total_rechazos
    assert set(manifest.counts.observations.by_class) == set(VALUE_STATUSES)
    assert sum(manifest.counts.observations.by_class.values()) == total_observaciones
    assert sum(entry.rows for entry in manifest.files) == total_observaciones
    assert manifest.rejection_trace.rows == total_rechazos
    for entry in manifest.files:
        contenido = (salida / entry.path).read_bytes()
        assert hashlib.sha256(contenido).hexdigest() == entry.sha256
    traza = (salida / manifest.rejection_trace.path).read_bytes()
    assert hashlib.sha256(traza).hexdigest() == manifest.rejection_trace.sha256


def test_rechazos_jsonl_trazables_en_orden_de_entrada(tmp_path):
    source = tmp_path / "original.csv"
    sha = write_csv(source, [fila(fecha="20240230"), fila()[:4]])
    policy = synthetic_policy(sha)
    salida = tmp_path / "salida"
    manifest = write_parquet_output(stream(source, policy, batch_size=2), policy, salida)
    lineas = (salida / "rejections.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 6 == manifest.counts.rejections.total
    rechazos = [Rejection.model_validate(json.loads(linea)) for linea in lineas]
    assert [r.provenance.record for r in rechazos] == [2, 2, 2, 3, 3, 3]
    assert [r.signal for r in rechazos] == list(SIGNALS) * 2
    assert all("FECHA/HORA" in rechazos[i].error for i in range(3))
    assert all("incompleta" in rechazos[i].error for i in range(3, 6))
    assert rechazos[0].raw == "12.5" and rechazos[5].raw is None
    assert rechazos[0].raw_fields["FECHA"] == "20240230"
    assert set(rechazos[5].raw_fields) == {"FECHA", "HORA", "PM10", "PM2_5"}


def test_entrada_vacia_publica_carpeta_coherente(tmp_path):
    source = tmp_path / "original.csv"
    sha = write_csv(source, [])
    policy = synthetic_policy(sha)
    salida = tmp_path / "salida"
    manifest = write_parquet_output(stream(source, policy), policy, salida)
    assert manifest.counts.input_rows == 0
    assert manifest.files == []
    assert manifest.counts.observations.total == 0 and manifest.counts.rejections.total == 0
    assert (salida / "rejections.jsonl").read_bytes() == b""
    assert list(iter_observations(salida)) == []


def test_salida_existente_no_se_sobrescribe(tmp_path):
    source = tmp_path / "original.csv"
    sha = write_csv(source, [fila()])
    policy = synthetic_policy(sha)
    salida = tmp_path / "salida"
    write_parquet_output(stream(source, policy), policy, salida)
    antes = digest_files(salida)
    entrada_antes = source.read_bytes()
    with pytest.raises(ValueError, match="existe"):
        write_parquet_output(stream(source, policy), policy, salida)
    assert digest_files(salida) == antes
    assert source.read_bytes() == entrada_antes
    assert not [p.name for p in tmp_path.iterdir() if p.name.startswith(".salida.tmp-")]


def test_fallo_inyectado_no_publica_ni_altera_salida_existente_o_entrada(tmp_path):
    source = tmp_path / "original.csv"
    filas = [fila(), fila(fecha="20240601", hora="000005"), fila()[:4]]
    sha = write_csv(source, filas)
    policy = synthetic_policy(sha)
    salida_ok = tmp_path / "salida_ok"
    write_parquet_output(stream(source, policy, batch_size=2), policy, salida_ok)
    antes = digest_files(salida_ok)
    entrada_antes = source.read_bytes()

    lotes = stream(source, policy, batch_size=2)

    def falla_a_medio_camino():
        yield next(lotes)
        raise RuntimeError("fallo inyectado")

    salida_nueva = tmp_path / "salida_nueva"
    with pytest.raises(RuntimeError, match="fallo inyectado"):
        write_parquet_output(falla_a_medio_camino(), policy, salida_nueva)
    assert not salida_nueva.exists()
    assert digest_files(salida_ok) == antes
    assert source.read_bytes() == entrada_antes
    assert not [p.name for p in tmp_path.iterdir() if p.name.startswith(".salida_nueva.tmp-")]


def test_manifiesto_rechaza_conteos_que_no_reconcilian(tmp_path):
    base = {
        "schema_version": 1,
        "policy_id": "p",
        "source_id": "senamhi-lima-csv",
        "policy_sha256": "a" * 64,
        "input_sha256": "b" * 64,
        "library": "pyarrow",
        "library_version": "25.0.1",
        "counts": {
            "input_rows": 2,
            "observations": {
                "total": 1,
                "by_signal": {s: 0 for s in SIGNALS},
                "by_class": {s: 0 for s in VALUE_STATUSES},
            },
            "rejections": {"total": 2, "by_signal": {s: 0 for s in SIGNALS}},
        },
        "files": [],
        "rejection_trace": {"path": "rejections.jsonl", "sha256": "c" * 64, "rows": 2},
    }
    with pytest.raises(ValueError):
        Manifest.model_validate(base)


def test_reemplazo_del_csv_despues_de_verificar_impide_publicar(tmp_path):
    source = tmp_path / "input.csv"
    policy = synthetic_policy(write_csv(source, [fila()]))
    batches = stream_observations(source, policy)
    source.write_bytes(source.read_bytes() + source.read_bytes().splitlines(keepends=True)[-1])
    target = tmp_path / "output"

    with pytest.raises(ValueError, match="SHA-256"):
        write_parquet_output(batches, policy, target)
    assert not target.exists()


@pytest.mark.parametrize("damage", ["missing", "modified", "trace"])
def test_lector_rechaza_artefactos_que_no_coinciden_con_manifiesto(tmp_path, damage):
    source = tmp_path / "input.csv"
    policy = synthetic_policy(write_csv(source, [fila()]))
    target = tmp_path / "output"
    manifest = write_parquet_output(stream_observations(source, policy), policy, target)
    partition = target / manifest.files[0].path
    if damage == "missing":
        partition.unlink()
    elif damage == "modified":
        partition.write_bytes(b"contenido alterado")
    else:
        (target / manifest.rejection_trace.path).write_bytes(b"{}\n")

    with pytest.raises(ValueError, match="manifiesto"):
        next(iter_observations(target))


def test_validacion_de_rechazos_no_carga_la_traza_completa(tmp_path, monkeypatch):
    source = tmp_path / "input.csv"
    policy = synthetic_policy(write_csv(source, [fila(hora="999999")]))
    original = Path.read_bytes

    def forbid_trace_read(path):
        if path.name == "rejections.jsonl":
            pytest.fail("La traza de rechazos debe verificarse por bloques")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", forbid_trace_read)
    manifest = write_parquet_output(stream_observations(source, policy), policy, tmp_path / "out")
    assert manifest.rejection_trace.rows == 3
