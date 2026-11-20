"""Ejecución real del benchmark tabular de PM2.5 (#26) sobre objetivos congelados.

Ajusta el modelo tabular solo con entrenamiento, selecciona la configuración únicamente
por MAE de validación y evalúa una sola vez sobre las ventanas externas congeladas de la
prueba bivariada (#88), unidas por window_id/forecast_hour con las predicciones registradas
de persistencia y del modelo temporal A. Si un horizonte falta en cualquier lado, su ventana
completa sale de la comparación y la exclusión se cuenta en la evidencia. Las métricas de
episodios quedan pendientes de las etiquetas de #20 y no se calculan aquí.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import platform
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from airaware.benchmarks.features import DesignRow, Window, design_rows
from airaware.benchmarks.metrics import Prediction, error_table, mae, rmse
from airaware.benchmarks.model import FitSpec, fit_lightgbm
from airaware.benchmarks.predictions import paired_evaluation, paired_join, predictions_from

EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
SOURCES = ("openaq", "senamhi_horario")
REFERENCES = ("persistence", "first")
MODELS_FREEZE_SHA256 = "6727c884d5e180b257ff385ccdebe80853ea8ff79b5ce38420ad0c70ac43f31b"
MATCH_TOLERANCE = 1e-9
CANDIDATES: dict[str, FitSpec] = {
    "lgbm-base": FitSpec(),
    "lgbm-hojas-31": FitSpec(num_leaves=31, min_data_in_leaf=20),
    "lgbm-paso-005": FitSpec(
        learning_rate=0.05,
        num_leaves=31,
        min_data_in_leaf=20,
        max_boosting_rounds=600,
        early_stopping_rounds=30,
    ),
}


class Bloqueo(Exception):
    """Violación del protocolo o del manifiesto; la ejecución termina sin evaluar."""


def spec_dict(spec: FitSpec) -> dict[str, int | float]:
    return {
        "learning_rate": spec.learning_rate,
        "num_leaves": spec.num_leaves,
        "min_data_in_leaf": spec.min_data_in_leaf,
        "max_boosting_rounds": spec.max_boosting_rounds,
        "early_stopping_rounds": spec.early_stopping_rounds,
        "seed": spec.seed,
    }


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ids_digest(ids: Sequence[str]) -> str:
    return hashlib.sha256(json.dumps(list(ids), separators=(",", ":")).encode()).hexdigest()


def git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()


def verify_manifest(folder: Path, names: tuple[str, ...]) -> dict:
    manifest = json.loads((folder / "manifest.json").read_text())
    for name in names:
        if sha256_file(folder / name) != manifest["files"][name]:
            raise Bloqueo(f"{folder / name} no coincide con su manifiesto")
    return manifest


def verify_historico(folder: Path) -> dict:
    """Manifiesto de lima-pm25-pm10-v1: npz por partición y escalador con su propia suma."""
    manifest = json.loads((folder / "manifest.json").read_text())
    for split in ("train", "validation"):
        entry = manifest["inputs"][split]
        if sha256_file(folder / f"{split}.npz") != entry["npz_sha256"]:
            raise Bloqueo(f"{folder / split}.npz no coincide con su manifiesto")
    if sha256_file(folder / "scaler.json") != manifest["scaler_sha256"]:
        raise Bloqueo("scaler.json no coincide con su manifiesto")
    return manifest


def verify_ids(path: Path, expected: str, array: np.ndarray) -> None:
    if ids_digest(array.tolist()) != expected:
        raise Bloqueo(f"Los identificadores ordenados de {path} cambiaron")


def pm25_windows(
    ids: np.ndarray,
    stations: np.ndarray,
    origin_hours: np.ndarray,
    history: np.ndarray,
    targets: np.ndarray,
) -> list[Window]:
    return [
        Window(
            window_id=str(ids[i]),
            station=str(stations[i]),
            origin_at=EPOCH + timedelta(hours=int(origin_hours[i])),
            history=tuple(history[i, :, 0].tolist()),
            targets=tuple(targets[i, :, 0].tolist()),
        )
        for i in range(len(ids))
    ]


def rows_of(windows: list[Window]) -> list[DesignRow]:
    return [row for window in windows for row in design_rows(window)]


def persistence_predictions(rows: Sequence[DesignRow]) -> list[Prediction]:
    # La persistencia repite el valor del origen: la primera característica es lag_00.
    return [
        Prediction(
            window_id=row.window_id,
            station=row.station,
            forecast_hour=row.forecast_hour,
            target=row.target,
            prediction=row.features[0],
        )
        for row in rows
    ]


def pm25_table(path: Path):
    return pq.read_table(path, filters=[("channel", "=", "pm25")]).select(
        ["window_id", "station_key", "target_at", "horizon", "actual", *REFERENCES]
    )


def table_predictions(table, column: str) -> list[Prediction]:
    ids = table.column("window_id").to_pylist()
    stations = table.column("station_key").to_pylist()
    horizons = table.column("horizon").to_pylist()
    actual = table.column("actual").to_pylist()
    values = table.column(column).to_pylist()
    return [
        Prediction(
            window_id=ids[i],
            station=stations[i],
            forecast_hour=int(horizons[i]),
            target=actual[i],
            prediction=float(values[i]),
        )
        for i in range(len(ids))
    ]


def align_by_window(
    tabular: list[Prediction], reference: list[Prediction]
) -> tuple[list[Prediction], list[Prediction], int, int]:
    """Excluye ventanas completas con horizontes faltantes en cualquier lado y las cuenta."""
    tab_keys = {(p.window_id, p.forecast_hour) for p in tabular}
    ref_keys = {(p.window_id, p.forecast_hour) for p in reference}
    if tab_keys == ref_keys:
        return tabular, reference, 0, 0
    fuera = {w for w, _ in tab_keys ^ ref_keys}
    tab_sub = [p for p in tabular if p.window_id not in fuera]
    ref_sub = [p for p in reference if p.window_id not in fuera]
    if {(p.window_id, p.forecast_hour) for p in tab_sub} != {
        (p.window_id, p.forecast_hour) for p in ref_sub
    }:
        raise Bloqueo("La cobertura no coincide ni excluyendo ventanas completas")
    return tab_sub, ref_sub, len(fuera), len(tab_keys ^ ref_keys)


def marginal(preds: Sequence[Prediction], key: Callable[[Prediction], object]) -> list[dict]:
    groups: dict[object, list[Prediction]] = {}
    for row in preds:
        groups.setdefault(key(row), []).append(row)
    return [
        {"key": group_key, "targets": len(items), "mae": mae(items), "rmse": rmse(items)}
        for group_key, items in sorted(groups.items(), key=lambda item: str(item[0]))
    ]


def station_horizon_rows(preds: Sequence[Prediction]) -> list[dict]:
    return [
        {
            "station": row.station,
            "horizon": row.forecast_hour,
            "targets": row.n,
            "mae": row.mae,
            "rmse": row.rmse,
        }
        for row in error_table(preds)
    ]


def overall(preds: Sequence[Prediction]) -> dict:
    return {"targets": len(preds), "mae": mae(preds), "rmse": rmse(preds)}


def pm25_channel_row(metrics_path: Path) -> tuple[dict, dict]:
    body = json.loads(metrics_path.read_text())
    channel = next(row for row in body["groups"]["channel"] if row["channel"] == "pm25")
    return channel, body


def station_hours(table) -> int:
    stations = table.column("station_key").to_pylist()
    targets_at = table.column("target_at").to_pylist()
    return len(set(zip(stations, targets_at, strict=True)))


def assert_close(label: str, computed: float, registered: float) -> None:
    if abs(computed - registered) > MATCH_TOLERANCE:
        raise Bloqueo(f"{label}: calculado {computed} difiere del registrado {registered}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="Carpeta lima-pm25-pm10-v1")
    parser.add_argument(
        "--externa", type=Path, required=True, help="Carpeta lima-pm25-pm10-externa-v1"
    )
    parser.add_argument(
        "--ejecucion", type=Path, required=True, help="Carpeta con la congelación de validación"
    )
    parser.add_argument("--output", type=Path, required=True, help="Evidencia JSON a escribir")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(
            f"La evidencia ya existe; la evaluación solo se ejecuta una vez: {args.output}"
        )

    started = datetime.now(UTC)
    evidence: dict = {
        "version": "tabular-datos-reales-v1",
        "started_at_utc": started.isoformat(),
        "git_commit": git_commit(),
        "command": "uv run --locked --extra tabular python tools/training/eval_tabular_real.py",
        "episodios": {
            "estado": "pendiente-de-20",
            "positivos": None,
            "negativos": None,
            "precision": None,
            "exhaustividad": None,
            "f1": None,
            "pr_auc": None,
        },
    }

    v1 = verify_historico(args.data)
    evidence["insumos"] = {
        "data": str(args.data),
        "manifest_sha256": sha256_file(args.data / "manifest.json"),
        "scaler_sha256": v1["scaler_sha256"],
        "cut_utc": v1["cut_utc"],
        "channels": v1["channels"],
        "train": dict(v1["inputs"]["train"]),
        "validation": dict(v1["inputs"]["validation"]),
    }

    with (
        np.load(args.data / "train.npz", allow_pickle=False) as z,
        np.load(args.data / "validation.npz", allow_pickle=False) as v,
    ):
        verify_ids(
            args.data / "train.npz", v1["inputs"]["train"]["ordered_ids_sha256"], z["window_id"]
        )
        verify_ids(
            args.data / "validation.npz",
            v1["inputs"]["validation"]["ordered_ids_sha256"],
            v["window_id"],
        )
        train_windows = pm25_windows(
            z["window_id"], z["station_key"], z["origin_hour"], z["history"], z["targets"]
        )
        validation_windows = pm25_windows(
            v["window_id"], v["station_key"], v["origin_hour"], v["history"], v["targets"]
        )
    print(f"ventanas train={len(train_windows)} validacion={len(validation_windows)}", flush=True)

    candidates = []
    reports = []
    for name, spec in CANDIDATES.items():
        print(f"ajustando {name} {spec_dict(spec)}", flush=True)
        began = time.perf_counter()
        report = fit_lightgbm(train_windows, validation_windows, spec)
        candidates.append(
            {
                "name": name,
                "spec": spec_dict(spec),
                "validation_mae": report.validation_mae,
                "chosen_rounds": report.chosen_rounds,
                "fit_seconds": time.perf_counter() - began,
                "processing": report.processing.to_dict(),
            }
        )
        reports.append(report)
        print(
            f"  MAE validacion={report.validation_mae:.6f} rondas={report.chosen_rounds}",
            flush=True,
        )
    best = min(range(len(candidates)), key=lambda i: candidates[i]["validation_mae"])
    evidence["candidatos"] = candidates
    evidence["seleccion"] = {"name": candidates[best]["name"], "criterio": "mae_validacion"}
    predictor = reports[best].predictor
    del train_windows, reports
    gc.collect()

    validation_rows = rows_of(validation_windows)
    persistence_val = persistence_predictions(validation_rows)
    persistence_val_mae = mae(persistence_val)
    evidence["validacion"] = {
        "targets": len(validation_windows) * 6,
        "persistence_mae": persistence_val_mae,
        "freeze_sha256": sha256_file(args.ejecucion / "validacion" / "metrics.json"),
    }
    del validation_rows, persistence_val, validation_windows
    gc.collect()

    registered_val, _ = pm25_channel_row(args.ejecucion / "validacion" / "metrics.json")
    assert_close(
        "persistencia en validacion", persistence_val_mae, registered_val["mae_persistence"]
    )
    evidence["validacion"]["persistence_mae_registrado"] = registered_val["mae_persistence"]
    evidence["validacion"]["targets_registrados"] = registered_val["targets"]
    evidence["validacion"]["station_hours_registrados"] = registered_val["station_hours"]

    evidence["fuentes"] = {}
    for source in SOURCES:
        matrices = verify_manifest(args.externa / source, ("inputs.npz", "observed.npz"))
        result = args.externa / f"result-{source}"
        registered, body = pm25_channel_row(result / "metrics.json")
        if sha256_file(result / "paired.parquet") != body["paired_sha256"]:
            raise Bloqueo(f"paired.parquet de {source} no coincide con su metrics.json")
        if body["models_freeze_sha256"] != MODELS_FREEZE_SHA256:
            raise Bloqueo(f"La congelacion de modelos de {source} no es la registrada")

        with (
            np.load(args.externa / source / "inputs.npz", allow_pickle=False) as x,
            np.load(args.externa / source / "observed.npz", allow_pickle=False) as y,
        ):
            verify_ids(
                args.externa / source / "inputs.npz", matrices["ordered_ids_sha256"], x["window_id"]
            )
            test_windows = pm25_windows(
                x["window_id"], y["station_key"], y["origin_hour"], x["history"], y["targets"]
            )
        print(f"evaluando {source}: {len(test_windows)} ventanas", flush=True)
        test_rows = rows_of(test_windows)
        tabular_predictions = predictions_from(predictor, test_rows)
        del test_rows, test_windows
        gc.collect()

        table = pm25_table(result / "paired.parquet")
        references = {name: table_predictions(table, name) for name in REFERENCES}
        station_hours_total = station_hours(table)
        del table
        gc.collect()

        tab_sub, ref_sub, excluded_windows, excluded_pairs = align_by_window(
            tabular_predictions, references["persistence"]
        )
        joined = paired_join(tab_sub, ref_sub)
        tab_aligned = [first for first, _ in joined]
        ref_aligned = [second for _, second in joined]
        assert_close(
            f"persistencia en prueba externa {source}",
            mae(ref_aligned),
            registered["mae_persistence"],
        )
        source_evidence = {
            "windows": len(tabular_predictions) // 6,
            "targets": len(joined),
            "station_hours": station_hours_total,
            "excluded_windows": excluded_windows,
            "excluded_pairs": excluded_pairs,
            "registrado": {
                "mae_persistence": registered["mae_persistence"],
                "mae_temporal_first": registered["mae_a"],
                "targets": registered["targets"],
                "station_hours": registered["station_hours"],
                "clock": body["clock"],
                "paired_sha256": body["paired_sha256"],
                "models_freeze_sha256": body["models_freeze_sha256"],
            },
            "tabular": {
                "overall": overall(tab_aligned),
                "by_horizon": marginal(tab_aligned, lambda row: row.forecast_hour),
                "by_station": marginal(tab_aligned, lambda row: row.station),
                "station_horizon": station_horizon_rows(tab_aligned),
            },
            "persistence": {"overall": overall(ref_aligned)},
            "delta_tabular_menos_persistence": paired_evaluation(
                ref_aligned, tab_aligned
            ).difference,
        }
        del references["persistence"], tab_sub, ref_sub, joined, tab_aligned, ref_aligned
        gc.collect()

        first_sub, _, excluded_first_windows, excluded_first_pairs = align_by_window(
            tabular_predictions, references["first"]
        )
        joined_first = paired_join(first_sub, references["first"])
        tab_first = [first for first, _ in joined_first]
        ref_first = [second for _, second in joined_first]
        assert_close(
            f"modelo temporal A en prueba externa {source}", mae(ref_first), registered["mae_a"]
        )
        if (excluded_first_windows, excluded_first_pairs) != (0, 0):
            raise Bloqueo(f"La cobertura del modelo temporal A de {source} difiere de la tabular")
        source_evidence["first"] = {"overall": overall(ref_first)}
        source_evidence["delta_tabular_menos_temporal_first"] = paired_evaluation(
            ref_first, tab_first
        ).difference
        del references["first"], first_sub, joined_first, tab_first, ref_first
        gc.collect()

        evidence["fuentes"][source] = source_evidence
        print(
            f"  {source}: tabular MAE={source_evidence['tabular']['overall']['mae']:.4f} "
            f"persistencia={source_evidence['persistence']['overall']['mae']:.4f} "
            f"A={source_evidence['first']['overall']['mae']:.4f} "
            f"pares={source_evidence['targets']} excluidas={source_evidence['excluded_windows']}",
            flush=True,
        )
        del tabular_predictions
        gc.collect()

    finished = datetime.now(UTC)
    evidence["finished_at_utc"] = finished.isoformat()
    evidence["duracion_segundos"] = (finished - started).total_seconds()
    evidence["entorno"] = {"python": platform.python_version(), "numpy": np.__version__}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    )
    print(f"evidencia escrita en {args.output}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Bloqueo as bloqueo:
        print(f"BLOQUEO: {bloqueo}", file=sys.stderr)
        raise SystemExit(2) from bloqueo
