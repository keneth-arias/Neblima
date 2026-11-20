"""Construir ventanas H24/F6 por fuente y fijar un corte histórico global 85/15."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from fractions import Fraction
from itertools import groupby
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
import numpy as np
import pyarrow as pa
from export_senamhi import sha256_file
from timenet.dataset import Record, Signal, Source, TimeFDataset
from timenet.dataset.axis import RegularAxis
from timenet.reader import TimeFReader
from timenet.types import (
    DatasetMetadata,
    ForecastingTask,
    License,
    TimeOrigin,
    TimeSeriesSpec,
    ureg,
)

HOUR = 3_600_000_000
PARAMS = ("pm25", "pm10")
SPECS = tuple(
    TimeSeriesSpec(
        spec_type=p,
        name=n,
        unit_value=ureg.microgram / ureg.meter**3,
        dtype="float64",
        missing=None,
    )
    for p, n in zip(PARAMS, ("PM2.5", "PM10"), strict=True)
)
GRID = """
WITH raw AS (
    SELECT sitio, id_estacion, id_sensor, parametro, valor,
           CASE WHEN fuente = 'senamhi_horario' THEN hora_nativa
                ELSE observado_utc::timestamp END AS hora
    FROM read_parquet(?) WHERE fuente = ? AND grupo = 'benchmark' AND unidad = 'µg/m³'
      AND parametro IN ('pm25','pm10')
), cells AS (
    SELECT sitio, id_estacion, hora, parametro, min(id_sensor) AS sensor,
           CASE WHEN count(DISTINCT id_sensor)<=1
                  AND count(DISTINCT valor) FILTER (WHERE isfinite(valor))=1
                  AND count(*) FILTER (WHERE valor IS NOT NULL AND NOT isfinite(valor))=0
                THEN min(valor) END AS valor
    FROM raw WHERE date_trunc('hour',hora)=hora AND hora >= ? AND hora < ?
    GROUP BY sitio,id_estacion,hora,parametro
)
SELECT sitio,id_estacion,epoch(hora)::BIGINT//3600 AS h,
       max(sensor) FILTER (WHERE parametro='pm25') AS sensor25,
       max(sensor) FILTER (WHERE parametro='pm10') AS sensor10,
       max(valor) FILTER (WHERE parametro='pm25') AS pm25,
       max(valor) FILTER (WHERE parametro='pm10') AS pm10
FROM cells GROUP BY sitio,id_estacion,hora HAVING pm25 IS NOT NULL AND pm10 IS NOT NULL
ORDER BY id_estacion,sensor25,sensor10,h
"""


def valid_starts(hours, values):
    if len(hours) < 30:
        return np.array([], dtype=np.int64)
    if np.any(np.diff(hours) <= 0):
        raise ValueError("Se requieren horas únicas y ordenadas por serie")
    complete = np.lib.stride_tricks.sliding_window_view(np.isfinite(values).all(axis=1), 30)
    return np.flatnonzero((hours[29:] - hours[:-29] == 29) & complete.all(axis=1))


def choose_cut(starts):
    ordered = np.sort(starts)
    if not len(ordered):
        raise ValueError("No hay ventanas históricas")
    cuts = np.arange(ordered.min(), ordered.max() + 1)
    train = ordered.searchsorted(cuts - 29)
    val = len(ordered) - ordered.searchsorted(cuts)
    ok = (train > 0) & (val > 0)
    if not ok.any():
        raise ValueError("El intervalo no admite dos particiones disjuntas")
    # Desempatar por el corte más temprano. Solo intervienen horas y disponibilidad.
    return int(cuts[ok][np.argmin(abs(train[ok] / (train[ok] + val[ok]) - 0.85))])


def label(hour, utc):
    value = datetime.fromtimestamp(int(hour) * 3600, UTC)
    return (value if utc else value.replace(tzinfo=None)).isoformat()


def digest_key(fields):
    return hashlib.sha256(json.dumps(fields, separators=(",", ":")).encode()).hexdigest()


def series_key(code, raw_name, name):
    return digest_key([code, None, raw_name, name, "ug/m3"])


def historical_window_id(pm25_series_id, start):
    # Misma serialización UTC de senamhi_windows.build_windows (DuckDB TIMESTAMPTZ).
    bounds = [
        datetime.fromtimestamp((start + k) * 3600, UTC).strftime("%Y-%m-%d %H:%M:%S+00")
        for k in (23, 0, 29)
    ]
    return digest_key([pm25_series_id, *bounds])


def groups(db, source, paths, begin, end):
    db.execute("SET TimeZone='UTC'")
    table = db.execute(GRID, [paths, source, begin, end]).to_arrow_table()
    stations = table.select(["sitio", "id_estacion", "sensor25", "sensor10"])
    keys = list(zip(*(column.to_pylist() for column in stations.columns), strict=True))
    hours = table["h"].to_numpy()
    values = np.column_stack([table[p].to_numpy() for p in PARAMS])
    for key, seq in groupby(enumerate(keys), key=lambda x: x[1]):
        indices = [i for i, _ in seq]
        block = slice(indices[0], indices[-1] + 1)
        h, v = hours[block], values[block]
        yield key, h, v, valid_starts(h, v)


def add_group(ds, key, hours, values, starts, source, cut):
    site, code, s25, s10 = key
    known = source != "senamhi_horario"
    history = source == "historico"
    series = (
        [series_key(code, "PM2_5", "PM2.5"), series_key(code, "PM10", "PM10")]
        if history
        else [
            digest_key([source, code, sensor, p])
            for sensor, p in zip((s25, s10), PARAMS, strict=True)
        ]
    )
    provenance = {
        "source": source,
        "station_key": code,
        "site": site,
        "sensor_ids": [s25, s10],
        "series_ids": series,
        "unit_status": "inferred" if history else "published",
        "quality": "unknown",
        "available_at": None,
    }
    counts = {"train": 0, "validation": 0, "test": 0, "purged": 0}
    arrays = [pa.array(values[:, j]) for j in range(2)]
    axes = [
        RegularAxis(period_us=Fraction(HOUR), offset_us=(0 if known else k) * HOUR) for k in (0, 24)
    ]
    for i in starts.tolist():
        h = int(hours[i])
        split = (
            "test"
            if cut is None
            else ("train" if h + 29 < cut else "validation" if h >= cut else "purged")
        )
        counts[split] += 1
        if split == "purged":
            continue
        clock = TimeOrigin(h * HOUR if known else None)
        records = []
        for (offset, size), axis in zip(((0, 24), (24, 6)), axes, strict=True):
            signals = tuple(
                Signal(name=p, spec=spec, time_axis=axis, data=a.slice(i + offset, size))
                for p, spec, a in zip(PARAMS, SPECS, arrays, strict=True)
            )
            records.append(
                ds.add_record(
                    record=Record(
                        start_time=TimeOrigin((h + offset) * HOUR) if known else clock,
                        sources=(Source(name=code, signals=signals),),
                        metadata={**provenance, "first_label": label(h + offset, known)},
                    )
                )
            )
        origin = label(h + 23, known)
        window_id = (
            historical_window_id(series[0], h)
            if history
            else digest_key([source, code, s25, s10, origin])
        )
        ds.add_task(
            task=ForecastingTask(
                inputs=(records[0],),
                targets=(records[1],),
                split=split,
                metadata={
                    "window_id": window_id,
                    "origin_at": origin,
                    "clock": "UTC" if known else "provider_wall_clock",
                },
            )
        )
    return counts


def build(source, paths, output, begin, end):
    boundary = datetime(2024, 6, 1)
    if (
        end <= begin
        or (source == "historico" and end > boundary)
        or (source != "historico" and begin < boundary)
    ):
        raise ValueError("Intervalo incompatible con el corte del 1 de junio de 2024")
    hashes = {str(p): sha256_file(p) for p in paths}
    with duckdb.connect() as db:
        series = list(groups(db, source, [str(p) for p in paths], begin, end))
    if hashes != {str(p): sha256_file(p) for p in paths}:
        raise ValueError("Cambió un insumo durante la lectura")
    starts = [h[ix] for _, h, _, ix in series if len(ix)]
    if not starts:
        raise ValueError("Sin ventanas completas para la fuente")
    hist = source == "historico"
    cut = choose_cut(np.concatenate(starts)) if hist else None
    suffix = "forecast" if hist else source.replace("_", "-")
    metadata = DatasetMetadata(
        dataset_id=f"airaware/lima-pm25-pm10-{suffix}",
        dataset_version="0.1.0",
        name=f"PM2.5 y PM10 de Lima · {source}",
        description=(
            "Ventanas retrospectivas con 24 horas de historia y "
            "seis objetivos por señal. Uso local."
        ),
        license=License.ODC_BY_1_0 if hist else License.NONE,
        access="open" if hist else "restricted",
        access_url=None if hist else "https://github.com/keneth-arias/airaware/issues/88",
        citation=(
            "SENAMHI, Lima. Para el archivo OpenAQ, "
            "atribuir también a OpenAQ y al proveedor original."
        ),
        source_revision=hashlib.sha256(json.dumps(sorted(hashes.values())).encode()).hexdigest(),
    )
    ds = TimeFDataset(metadata=metadata)
    stats = []
    for key, h, v, ix in series:
        counts = add_group(ds, key, h, v, ix, source, cut)
        stats.append(
            {
                "site": key[0],
                "code": key[1],
                "sensors": list(key[2:]),
                **counts,
                "first_history": label(h[ix[0]], source != "senamhi_horario") if len(ix) else None,
                "last_target": label(h[ix[-1]] + 29, source != "senamhi_horario")
                if len(ix)
                else None,
            }
        )
    release = ds.write(path=output)
    del ds
    with TimeFReader.open(release) as reader:
        reader.verify()
        table = reader.read_task_table()
        counts = table["split"].to_pylist()
        for split in ("train", "validation", "test"):
            expected = sum(row[split] for row in stats)
            if counts.count(split) != expected:
                raise ValueError("Conteo de tareas incorrecto")
            if expected:
                task = next(reader.iter_tasks(split=split, batch_size=1))
                for record, size in zip((task.inputs[0], task.targets[0]), (24, 6), strict=True):
                    if {s.name: len(s.to_arrow()) for s in record.signals} != {
                        p: size for p in PARAMS
                    }:
                        raise ValueError("Se perdió una señal o cambió su longitud")
    return {
        "source": source,
        "dataset_id": metadata.dataset_id,
        "dataset_version": str(metadata.dataset_version),
        "begin": begin.isoformat(),
        "end_exclusive": end.isoformat(),
        "cut_utc": label(cut, True) if hist else None,
        "stations": stats,
        "inputs": hashes,
        "manifest_sha256": sha256_file(release / "manifest.json"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", choices=("historico", "openaq", "senamhi_horario"))
    parser.add_argument("output", type=Path)
    parser.add_argument("observations", type=Path, nargs="+")
    parser.add_argument("--begin", type=datetime.fromisoformat, required=True)
    parser.add_argument("--end", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    with TemporaryDirectory(dir=args.output.parent) as tmp:
        stage = Path(tmp) / "registro"
        stats = build(args.source, args.observations, stage, args.begin, args.end)
        (stage / "resumen.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n")
        stage.rename(args.output)
