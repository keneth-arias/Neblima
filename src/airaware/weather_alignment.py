"""Alineación determinista de pronóstico archivado GFS con ventanas de PM2.5 (#17).

Convierte los originales Open-Meteo `previous_day1` ya adquiridos en filas horarias con
`issued_at` derivado del adelanto nominal documentado y `available_at` nulo (no documentado
por el proveedor; el `acquired_at` local nunca lo sustituye). La unión consume ventanas y
particiones congeladas por sus manifiestos, evalúa la admisión temporal contra el origen de
cada ventana y publica máscaras explícitas sin descartar ventanas ni reescribir objetivos.

Experimento retrospectivo por tiempo de emisión: no prueba disponibilidad operativa estricta.
"""

import json
import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import parse_qs, urlsplit

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import typer
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from airaware.acquisition.batch import BatchPlan
from airaware.acquisition.models import AcquisitionError
from airaware.acquisition.store import verify_bundle
from airaware.comparison.models import Policy
from airaware.derived_artifacts import new_bundle, sha256_file
from airaware.senamhi_splits import SPLITS_FILE, SPLITS_VERSION
from airaware.senamhi_timeline import HOURS_FILE, TIMELINE_VERSION
from airaware.senamhi_windows import WINDOWS_FILE, WINDOWS_VERSION

WEATHER_ALIGNMENT_VERSION = "weather-alignment-gfs-previous-day1-v1"
WEATHER_ROWS_FILE = "weather_rows.parquet"
WINDOW_WEATHER_FILE = "window_weather.parquet"
WINDOW_SUMMARY_FILE = "windows_weather_summary.parquet"

SPATIAL_METHOD = "open_meteo_grid_cell_lookup"
DISTANCE_NOTE = (
    "Distancia haversine aproximada entre las coordenadas solicitadas y la celda devuelta; "
    "el CRS de las coordenadas SENAMHI no está declarado."
)
LIMITATIONS = (
    "Experimento retrospectivo por tiempo de emisión: issued_at se deriva del adelanto nominal "
    "previous_day1 (24 horas) y no prueba disponibilidad operativa estricta.",
    "available_at del proveedor por hora no está documentado; permanece nulo y acquired_at "
    "(procedencia local de AirAware) nunca se sustituye por available_at.",
    "Las coordenadas de las estaciones SENAMHI tienen CRS sin declarar; las distancias "
    "haversine son aproximaciones geográficas.",
    "Las celdas de grilla GFS compartidas no son observaciones independientes ni mediciones "
    "en la estación de aire.",
    "ERA5, NOAA ISD, OEFA y SENAMHI GBON quedan excluidos de esta variante inicial.",
)
ATTRIBUTION = {
    "provider": "Open-Meteo (CC-BY-4.0; atribución requerida; uso no comercial)",
    "upstream_model": "GFS — NOAA NCEP",
    "documentation": "https://open-meteo.com/en/docs/previous-runs-api",
}
WEATHER_ROWS_SCHEMA = pa.schema(
    [
        ("station_key", pa.string()),
        ("station_name", pa.string()),
        ("requested_latitude", pa.float64()),
        ("requested_longitude", pa.float64()),
        ("returned_cell_latitude", pa.float64()),
        ("returned_cell_longitude", pa.float64()),
        ("returned_cell_elevation_m", pa.float64()),
        ("distance_km_haversine", pa.float64()),
        ("spatial_method", pa.string()),
        ("distance_note", pa.string()),
        ("valid_at", pa.timestamp("us", tz="UTC")),
        ("issued_at", pa.timestamp("us", tz="UTC")),
        ("available_at", pa.timestamp("us", tz="UTC")),
        ("lead_hours", pa.int64()),
        ("variable", pa.string()),
        ("unit", pa.string()),
        ("product_class", pa.string()),
        ("value", pa.float64()),
        ("value_status", pa.string()),
        ("source_id", pa.string()),
        ("original_sha256", pa.string()),
        ("acquired_at", pa.timestamp("us", tz="UTC")),
        ("issued_at_rule", pa.string()),
        ("experiment_class", pa.string()),
    ]
)

JOIN_QUERY = """
SELECT span.window_id, span.series_id, span.station_key, span.origin_at, span.split,
       span.purge_reason, span.valid_at, span.hour_role, rows.variable, rows.unit,
       rows.value, rows.value_status, rows.issued_at, rows.available_at, rows.lead_hours,
       rows.original_sha256,
       CASE
           WHEN rows.station_key IS NULL THEN 'missing_weather'
           WHEN rows.issued_at > span.origin_at THEN 'rejected_issue_after_origin'
           WHEN rows.available_at > span.origin_at THEN 'rejected_available_after_origin'
           ELSE 'admissible'
       END AS alignment_status
FROM (
    SELECT w.window_id, w.series_id, w.station_key, w.origin_at, w.split, w.purge_reason,
           hour AS valid_at,
           CASE WHEN hour <= w.origin_at THEN 'history_input' ELSE 'target_forecast' END
               AS hour_role
    FROM read_parquet(?) AS w
    CROSS JOIN LATERAL generate_series(w.history_start, w.target_end, INTERVAL '1 hour')
        AS grid(hour)
    WHERE w.station_key IN (SELECT station_key FROM station_map)
) AS span
LEFT JOIN read_parquet(?) AS rows
    ON rows.station_key = span.station_key AND rows.valid_at = span.valid_at
"""

SUMMARY_QUERY = """
SELECT window_id, series_id, station_key, origin_at, split, purge_reason,
       count(*) AS span_hours,
       count(*) FILTER (WHERE alignment_status = 'admissible') AS weather_hours_admissible,
       count(*) FILTER (WHERE alignment_status = 'missing_weather') AS weather_hours_missing,
       count(*) FILTER (WHERE alignment_status LIKE 'rejected%') AS weather_hours_rejected,
       min(valid_at) FILTER (WHERE alignment_status = 'admissible') AS first_admissible_valid_at,
       max(valid_at) FILTER (WHERE alignment_status = 'admissible') AS last_admissible_valid_at,
       CASE
           WHEN count(*) FILTER (WHERE alignment_status = 'admissible') = 0 THEN 'missing'
           WHEN count(*) FILTER (WHERE alignment_status = 'admissible') = count(*)
               THEN 'complete'
           ELSE 'partial'
       END AS weather_status
FROM joined
GROUP BY window_id, series_id, station_key, origin_at, split, purge_reason
"""


class WeatherStation(BaseModel):
    """Identidad de estación de aire y coordenadas solicitadas, con CRS explícito."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    station_key: str = Field(pattern=r"^[a-f0-9]{64}$")
    name: str = Field(min_length=1)
    latitude: float
    longitude: float
    altitude_m: float
    coordinate_reference: Literal["undeclared"]


class WeatherVariant(BaseModel):
    """Variante meteorológica inicial: solo previous_day1 de GFS vía Open-Meteo."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    name: Literal["pm25_gfs_previous_day1"]
    source_id: Literal["open-meteo-previous-model-runs"]
    variable: Literal["temperature_2m_previous_day1"]
    excluded_realized_variables: tuple[Literal["temperature_2m"], ...] = ("temperature_2m",)
    unit: Literal["°C"]
    nominal_lead_hours: Literal[24]
    issued_at_rule: Literal["previous_day1_nominal_lead"]
    available_at_policy: Literal["undocumented_null"]
    product_class: Literal["archived_forecast"]
    experiment_class: Literal["retrospective_issue_time"]
    acquisition_plan: str = Field(min_length=1)
    coverage_utc: str = Field(min_length=1)

    @model_validator(mode="after")
    def explicit_exclusions(self):
        if self.excluded_realized_variables != ("temperature_2m",):
            raise ValueError("La exclusión de la variable realizada debe quedar explícita")
        return self


class AlignmentConfig(BaseModel):
    """Dos configuraciones explícitas: referencia solo contaminación y variante con clima."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal[1] = 1
    comparison_policy: str = Field(min_length=1)
    weather_variant: WeatherVariant
    stations: tuple[WeatherStation, ...] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def unique_stations(self):
        keys = [station.station_key for station in self.stations]
        coordinates = [(station.latitude, station.longitude) for station in self.stations]
        if len(set(keys)) != len(keys) or len(set(coordinates)) != len(coordinates):
            raise ValueError("Estaciones con clave o coordenadas solicitadas repetidas")
        return self


def load_config(path: Path) -> AlignmentConfig:
    """Leer y validar la configuración YAML sin servicios externos."""
    with path.open("rb") as stream:
        body = stream.read(65537)
    if len(body) > 65536:
        raise ValueError("Configuración excesiva")
    try:
        document = yaml.safe_load(body)
    except yaml.YAMLError as error:
        raise ValueError("La configuración de alineación no es YAML válido") from error
    return AlignmentConfig.model_validate(document)


def _requested_coordinates(url: str) -> tuple[Decimal, Decimal]:
    query = parse_qs(urlsplit(url).query)
    try:
        return Decimal(query["latitude"][0]), Decimal(query["longitude"][0])
    except (KeyError, IndexError) as error:
        raise ValueError("La URL del plan no declara coordenadas solicitadas") from error


def _haversine_km(first: tuple[float, float], second: tuple[float, float]) -> float:
    radius = 6371.0088
    lat1, lon1 = math.radians(first[0]), math.radians(first[1])
    lat2, lon2 = math.radians(second[0]), math.radians(second[1])
    a = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def _hourly_records(payload: dict, variant: WeatherVariant) -> list[tuple[datetime, float | None]]:
    """Extraer el eje horario UTC y la variable configurada; rechaza desvíos del contrato."""
    expected = (
        "latitude",
        "longitude",
        "elevation",
        "hourly",
        "hourly_units",
        "utc_offset_seconds",
    )
    if any(key not in payload for key in expected):
        raise ValueError("La respuesta del proveedor no tiene la estructura esperada")
    if payload["utc_offset_seconds"] != 0:
        raise ValueError("El eje del recurso no está en UTC")
    hourly = payload["hourly"]
    times = hourly.get("time")
    values = hourly.get(variant.variable)
    if not isinstance(times, list) or not isinstance(values, list) or len(times) != len(values):
        raise ValueError("El eje horario y la variable configurada no concilian")
    if payload["hourly_units"].get(variant.variable) != variant.unit:
        raise ValueError("La unidad declarada por el proveedor no coincide con la configuración")
    records: list[tuple[datetime, float | None]] = []
    for stamp, value in zip(times, values, strict=True):
        parsed = datetime.fromisoformat(str(stamp))
        if parsed.tzinfo is not None and parsed.utcoffset() != timedelta(0):
            raise ValueError("La marca del proveedor declara una zona horaria distinta de UTC")
        valid_at = parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
        number = None if value is None else float(value)
        if number is not None and not math.isfinite(number):
            number = None
        records.append((valid_at, number))
    return records


def _station_rows(
    config: AlignmentConfig,
    payload: dict,
    station: WeatherStation,
    original_sha256: str,
    acquired_at: datetime | None,
) -> list[dict]:
    variant = config.weather_variant
    cell = (
        float(payload["latitude"]),
        float(payload["longitude"]),
        float(payload["elevation"]),
    )
    distance = _haversine_km((station.latitude, station.longitude), (cell[0], cell[1]))
    rows = []
    for valid_at, value in _hourly_records(payload, variant):
        rows.append(
            {
                "station_key": station.station_key,
                "station_name": station.name,
                "requested_latitude": station.latitude,
                "requested_longitude": station.longitude,
                "returned_cell_latitude": cell[0],
                "returned_cell_longitude": cell[1],
                "returned_cell_elevation_m": cell[2],
                "distance_km_haversine": distance,
                "spatial_method": SPATIAL_METHOD,
                "distance_note": DISTANCE_NOTE,
                "valid_at": valid_at,
                "issued_at": valid_at - timedelta(hours=variant.nominal_lead_hours),
                "available_at": None,
                "lead_hours": variant.nominal_lead_hours,
                "variable": variant.variable,
                "unit": variant.unit,
                "product_class": variant.product_class,
                "value": value,
                "value_status": "missing" if value is None else "present",
                "source_id": variant.source_id,
                "original_sha256": original_sha256,
                "acquired_at": acquired_at,
                "issued_at_rule": variant.issued_at_rule,
                "experiment_class": variant.experiment_class,
            }
        )
    return rows


def _read_manifest(path: Path) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("El manifiesto del paquete no es JSON válido") from error
    if not isinstance(document, dict):
        raise ValueError("El manifiesto del paquete no es un objeto JSON")
    return document


def _convert_rows(
    config: AlignmentConfig, plan: BatchPlan, data_dir: Path, destination: Path
) -> dict:
    """Verificar cada paquete fijado y convertirlo en filas horarias con procedencia."""
    variant = config.weather_variant
    raw = (data_dir / "raw").resolve()
    by_coordinate = {
        (Decimal(str(station.latitude)), Decimal(str(station.longitude))): station
        for station in config.stations
    }
    jobs = [job for job in plan.jobs if job.spec.source_id == variant.source_id]
    if not jobs:
        raise ValueError("El plan no contiene recursos del pronóstico archivado configurado")
    rows: list[dict] = []
    timestamps: dict[str, int] = {}
    cells: dict[tuple[float, float], set[str]] = {}
    resources: list[dict] = []
    matched: set[str] = set()
    for job in jobs:
        spec = job.spec
        digest = spec.expected_sha256
        if digest is None:
            raise ValueError("Falta el SHA-256 fijado para un recurso del plan")
        directory = raw / spec.source_id / digest
        try:
            verify_bundle(spec, raw, directory)
        except (AcquisitionError, OSError) as error:
            raise ValueError("El paquete local no verifica contra el plan fijado") from error
        original = directory / f"original.{spec.format}"
        before = sha256_file(original)
        station = by_coordinate.get(_requested_coordinates(str(spec.resource_url)))
        if station is None:
            raise ValueError("Un recurso del plan no corresponde a ninguna estación configurada")
        if station.station_key in matched:
            raise ValueError("Dos recursos del plan corresponden a la misma estación")
        payload = json.loads(original.read_text(encoding="utf-8"))
        manifest = _read_manifest(directory / "manifest.json")
        acquired = manifest.get("spec", {}).get("acquired_at")
        station_rows = _station_rows(
            config,
            payload,
            station,
            digest,
            None if acquired is None else datetime.fromisoformat(str(acquired)),
        )
        rows.extend(station_rows)
        matched.add(station.station_key)
        timestamps[station.station_key] = len(station_rows)
        cell = (float(payload["latitude"]), float(payload["longitude"]))
        cells.setdefault(cell, set()).add(station.station_key)
        resources.append(
            {
                "station_key": station.station_key,
                "sha256": digest,
                "size_bytes": original.stat().st_size,
                "acquired_at": acquired,
                "rows": len(station_rows),
            }
        )
        if sha256_file(original) != before:
            raise ValueError("El original cambió durante la conversión")
    if matched != {station.station_key for station in config.stations}:
        raise ValueError("Hay estaciones configuradas sin recurso verificado en el plan")
    table = pa.Table.from_pylist(rows, schema=WEATHER_ROWS_SCHEMA).sort_by(
        [("station_key", "ascending"), ("valid_at", "ascending")]
    )
    pq.write_table(table, destination)
    lats = sorted({lat for lat, _ in cells})
    lons = sorted({lon for _, lon in cells})
    spacing = {
        "latitude": min(b - a for a, b in zip(lats, lats[1:], strict=False))
        if len(lats) > 1
        else None,
        "longitude": min(b - a for a, b in zip(lons, lons[1:], strict=False))
        if len(lons) > 1
        else None,
    }
    return {
        "stations_requested": len(config.stations),
        "stations_matched": len(matched),
        "resources_verified": len(resources),
        "rows": len(rows),
        "rows_value_missing": sum(1 for row in rows if row["value_status"] == "missing"),
        "timestamps_per_station": dict(sorted(timestamps.items())),
        "distinct_returned_cells": [
            {
                "latitude": cell[0],
                "longitude": cell[1],
                "stations": sorted(keys),
                "elevations_m": sorted(
                    {
                        row["returned_cell_elevation_m"]
                        for row in rows
                        if (row["returned_cell_latitude"], row["returned_cell_longitude"])
                        == (cell[0], cell[1])
                    }
                ),
            }
            for cell, keys in sorted(cells.items())
        ],
        "declared_grid_resolution": None,
        "observed_grid_spacing_deg": spacing,
        "units": {variant.variable: variant.unit},
        "resources": resources,
    }


def _read_limited(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        body = stream.read(limit + 1)
    if len(body) > limit:
        raise ValueError("El archivo excede el límite permitido")
    return body


def _comparison_policy(config: AlignmentConfig) -> dict:
    path = Path(config.comparison_policy)
    policy = Policy.model_validate(yaml.safe_load(_read_limited(path, 65536)))
    return {
        "path": config.comparison_policy,
        "sha256": sha256_file(path),
        "version": policy.version,
    }


def _validate_chain(windows_dir: Path, timeline_dir: Path, splits_dir: Path) -> dict:
    """Verificar versiones y vínculos de grilla, ventanas y particiones congeladas."""
    hours = timeline_dir / HOURS_FILE
    windows = windows_dir / WINDOWS_FILE
    splits = splits_dir / SPLITS_FILE
    timeline_manifest = _read_manifest(timeline_dir / "manifest.json")
    windows_manifest = _read_manifest(windows_dir / "manifest.json")
    splits_manifest = _read_manifest(splits_dir / "manifest.json")
    timeline_sha = sha256_file(hours)
    windows_sha = sha256_file(windows)
    splits_sha = sha256_file(splits)
    if (
        timeline_manifest.get("version") != TIMELINE_VERSION
        or windows_manifest.get("version") != WINDOWS_VERSION
        or splits_manifest.get("version") != SPLITS_VERSION
        or timeline_manifest.get("output_sha256") != timeline_sha
        or windows_manifest.get("output_sha256") != windows_sha
        or splits_manifest.get("output_sha256") != splits_sha
        or windows_manifest.get("input_sha256") != timeline_sha
        or splits_manifest.get("input_sha256") != windows_sha
        or splits_manifest.get("timeline_sha256") != timeline_sha
    ):
        raise ValueError("Versión, vínculo o SHA-256 distinto del manifiesto congelado")
    history = windows_manifest.get("history_hours")
    horizon = windows_manifest.get("horizon_hours")
    if (
        type(history) is not int
        or not 1 <= history <= 168
        or type(horizon) is not int
        or horizon < 1
    ):
        raise ValueError("Historia u horizonte fuera del contrato congelado")
    return {
        "timeline_sha256": timeline_sha,
        "windows_sha256": windows_sha,
        "splits_sha256": splits_sha,
        "history_hours": history,
        "horizon_hours": horizon,
        "validation_start": splits_manifest.get("validation_start"),
        "test_start": splits_manifest.get("test_start"),
    }


def _window_hash(db: duckdb.DuckDBPyConnection, splits: str, eligible_only: bool) -> str:
    clause = "WHERE split <> 'purged'" if eligible_only else ""
    row = db.execute(
        f"SELECT sha256(to_json(list(window_id ORDER BY window_id))) FROM read_parquet(?) {clause}",
        [splits],
    ).fetchone()
    if row is None:
        raise ValueError("Las particiones congeladas están vacías")
    return str(row[0])


def _join_rows(
    config: AlignmentConfig,
    rows_path: Path,
    windows_dir: Path,
    timeline_dir: Path,
    splits_dir: Path,
    weather_destination: Path,
    summary_destination: Path,
) -> dict:
    """Unir por window_id con admisión temporal explícita; nunca descarta ventanas."""
    chain = _validate_chain(windows_dir, timeline_dir, splits_dir)
    splits = str(splits_dir / SPLITS_FILE)
    station_keys = [station.station_key for station in config.stations]
    with duckdb.connect(config={"threads": 2}) as db:
        db.execute("SET TimeZone = 'UTC'")
        db.register(
            "station_map",
            pa.table({"station_key": pa.array(station_keys, pa.string())}),
        )
        uncovered = db.execute(
            "SELECT count(*) FROM read_parquet(?) "
            "WHERE station_key NOT IN (SELECT station_key FROM station_map)",
            [splits],
        ).fetchone()
        assert uncovered is not None
        if uncovered[0]:
            raise ValueError("La configuración no cubre todas las estaciones de las ventanas")
        absent = db.execute(
            "SELECT count(*) FROM station_map WHERE station_key NOT IN "
            "(SELECT DISTINCT station_key FROM read_parquet(?))",
            [splits],
        ).fetchone()
        assert absent is not None
        if absent[0]:
            raise ValueError("Estaciones configuradas sin ventanas congeladas")
        db.execute("CREATE TEMP TABLE joined AS " + JOIN_QUERY, [splits, str(rows_path)])
        db.execute(
            "COPY (SELECT * FROM joined ORDER BY window_id, valid_at) TO ? (FORMAT PARQUET)",
            [str(weather_destination)],
        )
        db.execute(
            f"COPY ({SUMMARY_QUERY} ORDER BY window_id) TO ? (FORMAT PARQUET)",
            [str(summary_destination)],
        )
        summary = str(summary_destination)
        spans = db.execute("SELECT DISTINCT span_hours FROM read_parquet(?)", [summary]).fetchall()
        expected_span = chain["history_hours"] + chain["horizon_hours"]
        if len(spans) != 1 or spans[0][0] != expected_span:
            raise ValueError("La unión no concilia con la historia y el horizonte congelados")
        totals = db.execute(
            "SELECT count(*), count(*) FILTER (WHERE split <> 'purged') FROM read_parquet(?)",
            [splits],
        ).fetchone()
        summary_totals = db.execute(
            "SELECT count(*), count(*) FILTER (WHERE split <> 'purged') FROM read_parquet(?)",
            [summary],
        ).fetchone()
        statuses = db.execute(
            "SELECT alignment_status, count(*) FROM read_parquet(?) GROUP BY alignment_status "
            "ORDER BY alignment_status",
            [str(weather_destination)],
        ).fetchall()
        assert totals is not None and summary_totals is not None
        windows_total, windows_eligible = int(totals[0]), int(totals[1])
        summary_total, summary_eligible = int(summary_totals[0]), int(summary_totals[1])
        targets = db.execute(
            "SELECT sha256(to_json(list(struct_pack(window_id := window_id, "
            "target_values := target_values) ORDER BY window_id))) "
            "FROM read_parquet(?) WHERE split <> 'purged'",
            [splits],
        ).fetchone()
        assert targets is not None
        parity = {
            "windows_total": windows_total,
            "windows_eligible": windows_eligible,
            "summary_windows_total": summary_total,
            "summary_eligible_windows": summary_eligible,
            "window_id_set_sha256_splits_all": _window_hash(db, splits, False),
            "window_id_set_sha256_summary_all": _window_hash(db, summary, False),
            "window_id_set_sha256_splits_eligible": _window_hash(db, splits, True),
            "window_id_set_sha256_summary_eligible": _window_hash(db, summary, True),
            "identical_window_id_set": (windows_total, windows_eligible)
            == (summary_total, summary_eligible)
            and _window_hash(db, splits, False) == _window_hash(db, summary, False)
            and _window_hash(db, splits, True) == _window_hash(db, summary, True),
            "eligible_targets_sha256": str(targets[0]),
        }
        if not parity["identical_window_id_set"]:
            raise ValueError("La unión no conserva el conjunto de ventanas congeladas")
    return {
        "inputs": chain | {"weather_rows_sha256": sha256_file(rows_path)},
        "counts": {
            "windows_total": windows_total,
            "windows_eligible": windows_eligible,
            "aligned_rows": sum(count for _, count in statuses),
            "alignment_status": {status: count for status, count in statuses},
        },
        "parity": parity,
    }


def _manifest(
    config: AlignmentConfig,
    reconciliation: dict,
    outputs: dict,
    inputs: dict,
    extras: dict,
) -> dict:
    variant = config.weather_variant
    return {
        "version": WEATHER_ALIGNMENT_VERSION,
        "experiment": {
            "reference_configuration": "pm25_only",
            "weather_configuration": variant.name,
            "experiment_class": variant.experiment_class,
            "note": (
                "Experimento retrospectivo por tiempo de emisión; no prueba disponibilidad "
                "operativa estricta."
            ),
            "coverage_utc": variant.coverage_utc,
        },
        "weather": {
            "source_id": variant.source_id,
            "variable": variant.variable,
            "unit": variant.unit,
            "excluded_realized_variables": list(variant.excluded_realized_variables),
            "product_class": variant.product_class,
            "nominal_lead_hours": variant.nominal_lead_hours,
            "issued_at_rule": (
                "valid_at es la marca horaria del proveedor; issued_at = valid_at menos el "
                "adelanto nominal previous_day1"
            ),
            "available_at": None,
            "available_at_policy": variant.available_at_policy
            + " (acquired_at es procedencia local y nunca se usa como available_at)",
        },
        "spatial": {
            "method": SPATIAL_METHOD,
            "coordinate_reference": "undeclared",
            "distance_note": DISTANCE_NOTE,
        },
        "attribution": ATTRIBUTION,
        "limitations": list(LIMITATIONS),
        "comparison_policy": extras.get("policy"),
        "inputs": inputs,
        "outputs": outputs,
        "reconciliation": reconciliation,
        "counts": extras.get("counts"),
        "parity": extras.get("parity"),
    }


def _write_manifest(staging: Path, manifest: dict) -> None:
    (staging / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_alignment(
    config: AlignmentConfig,
    plan: BatchPlan,
    data_dir: Path,
    output: Path,
    *,
    windows_dir: Path | None = None,
    timeline_dir: Path | None = None,
    splits_dir: Path | None = None,
) -> None:
    """Convertir y, opcionalmente, unir en un paquete atómico que rechaza salidas existentes."""
    if (windows_dir is None) != (timeline_dir is None) or (windows_dir is None) != (
        splits_dir is None
    ):
        raise ValueError("La unión requiere ventanas, grilla y particiones juntas")
    with new_bundle(output) as staging:
        weather_rows = staging / WEATHER_ROWS_FILE
        reconciliation = _convert_rows(config, plan, data_dir, weather_rows)
        outputs = {"weather_rows_sha256": sha256_file(weather_rows)}
        inputs: dict = {"acquisition_plan": config.weather_variant.acquisition_plan}
        extras: dict = {}
        if windows_dir is not None and timeline_dir is not None and splits_dir is not None:
            weather = staging / WINDOW_WEATHER_FILE
            summary = staging / WINDOW_SUMMARY_FILE
            joined = _join_rows(
                config, weather_rows, windows_dir, timeline_dir, splits_dir, weather, summary
            )
            outputs["window_weather_sha256"] = sha256_file(weather)
            outputs["windows_weather_summary_sha256"] = sha256_file(summary)
            extras["policy"] = _comparison_policy(config)
            extras["counts"] = joined["counts"]
            extras["parity"] = joined["parity"]
            inputs.update(joined["inputs"])
        manifest = _manifest(config, reconciliation, outputs, inputs, extras)
        manifest["output_sha256"] = outputs["weather_rows_sha256"]
        _write_manifest(staging, manifest)


def join_weather(
    config: AlignmentConfig,
    weather_bundle: Path,
    windows_dir: Path,
    timeline_dir: Path,
    splits_dir: Path,
    output: Path,
) -> None:
    """Unir un paquete de conversión existente con las ventanas congeladas."""
    rows = weather_bundle / WEATHER_ROWS_FILE
    source = _read_manifest(weather_bundle / "manifest.json")
    if source.get("version") != WEATHER_ALIGNMENT_VERSION or source.get(
        "output_sha256"
    ) != sha256_file(rows):
        raise ValueError("Versión o SHA-256 del paquete meteorológico distinto del manifiesto")
    with new_bundle(output) as staging:
        weather = staging / WINDOW_WEATHER_FILE
        summary = staging / WINDOW_SUMMARY_FILE
        joined = _join_rows(config, rows, windows_dir, timeline_dir, splits_dir, weather, summary)
        extras = {
            "policy": _comparison_policy(config),
            "counts": joined["counts"],
            "parity": joined["parity"],
        }
        inputs = dict(joined["inputs"])
        inputs["weather_bundle_manifest_sha256"] = sha256_file(weather_bundle / "manifest.json")
        reconciliation = source.get("reconciliation")
        if not isinstance(reconciliation, dict):
            reconciliation = {}
        manifest = _manifest(
            config,
            reconciliation,
            {
                "window_weather_sha256": sha256_file(weather),
                "windows_weather_summary_sha256": sha256_file(summary),
            },
            inputs,
            extras,
        )
        manifest["output_sha256"] = None
        _write_manifest(staging, manifest)


def weather(
    output: Annotated[Path, typer.Option(help="Carpeta nueva para el paquete de alineación.")],
    config: Annotated[
        Path, typer.Option(help="Configuración YAML de la alineación meteorológica.")
    ] = Path("configs/weather-alignment.yaml"),
    plan: Annotated[
        Path | None,
        typer.Option(help="Plan de adquisición fijado; por omisión el de la configuración."),
    ] = None,
    data_dir: Annotated[
        Path,
        typer.Option(envvar="AIRAWARE_DATA_DIR", help="Carpeta de datos con originales en raw/."),
    ] = Path("data"),
    windows: Annotated[Path | None, typer.Option(help="Carpeta de ventanas congeladas.")] = None,
    timeline: Annotated[Path | None, typer.Option(help="Carpeta de la grilla horaria.")] = None,
    splits: Annotated[Path | None, typer.Option(help="Carpeta de particiones congeladas.")] = None,
) -> None:
    """Convertir el pronóstico archivado fijado y unirlo a las ventanas sin información futura."""
    try:
        configuration = load_config(config)
        plan_path = (
            plan if plan is not None else Path(configuration.weather_variant.acquisition_plan)
        )
        batch = BatchPlan.model_validate_json(_read_limited(plan_path, 1048576))
        build_alignment(
            configuration,
            batch,
            data_dir,
            output,
            windows_dir=windows,
            timeline_dir=timeline,
            splits_dir=splits,
        )
    except (OSError, ValueError, KeyError, duckdb.Error) as error:
        typer.echo(f"No se pudo alinear la meteorología: {error}", err=True)
        raise typer.Exit(1) from None
    typer.echo(f"Alineación meteorológica: {output}")
