"""Cotejar la validación pareada y congelar los dos estados finales de #88."""

import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from export_senamhi import ROOT, sha256_file
from joint_windows import PARAMS, write_json
from paired_forecasts import ordered_ids

POLICY = ROOT / "configs/training/lima-pm25-pm10-ajuste-v1.json"
VIEWS = ("first", "both")


def read_predictions(data, ids, view, checkpoint, scaler):
    keys, order = ordered_ids(data["window_id"])
    prediction = data["predicted"]
    if (
        not np.array_equal(keys, ids)
        or tuple(data["channels"]) != PARAMS
        or not np.array_equal(data["forecast_hour"], np.arange(1, 7))
        or prediction.shape != (len(ids), 6, 2)
        or not np.isfinite(prediction).all()
        or str(data["view"]) != view
        or str(data["checkpoint_sha256"]) != checkpoint
        or str(data["scaler_sha256"]) != scaler
    ):
        raise ValueError(
            "Las predicciones difieren de los identificadores, canales o estado fijados"
        )
    return prediction[order]


def paired_table(data, first, both, thresholds):
    ids = data["window_id"]
    history, actual = data["history"], data["targets"]
    if (
        history.shape != (len(ids), 24, 2)
        or actual.shape != (len(ids), 6, 2)
        or not np.isfinite(actual).all()
        or not np.isfinite(history).all()
        or tuple(data["channels"]) != PARAMS
    ):
        raise ValueError("Matrices históricas incompatibles")
    stations = data["station_key"]
    threshold = np.array([thresholds[station] for station in stations], dtype=np.float64)
    horizons = np.arange(1, 7)
    target_hours = data["origin_hour"][:, None] + horizons
    return pa.table(
        {
            "window_id": np.repeat(ids, 12),
            "station_key": np.repeat(stations, 12),
            "origin_at": pa.array(
                np.repeat(data["origin_hour"] * 3600, 12), type=pa.timestamp("s", tz="UTC")
            ),
            "target_at": pa.array(
                np.repeat(target_hours.ravel() * 3600, 2), type=pa.timestamp("s", tz="UTC")
            ),
            "channel": np.tile(PARAMS, len(ids) * 6),
            "horizon": np.tile(horizons.repeat(2), len(ids)),
            "actual": actual.ravel(),
            "persistence": np.repeat(history[:, -1:, :], 6, axis=1).ravel(),
            "first": first.ravel(),
            "both": both.ravel(),
            "high": (actual >= threshold[:, None, :]).ravel(),
        }
    )


def summarize(db):
    rows, keys, station_hours = db.execute("""
        SELECT count(*),count(DISTINCT(window_id,channel,horizon)),
               count(DISTINCT(station_key,target_at)) FROM pairs""").fetchone()
    if keys != rows:
        raise ValueError("Se repite una clave de validación")
    metrics = """count(*) AS targets, count(DISTINCT(station_key,target_at)) AS station_hours,
          avg(abs(first-actual)) AS mae_a, avg(abs("both"-actual)) AS mae_b,
          avg(abs(persistence-actual)) AS mae_persistence,
          avg(abs("both"-actual)-abs(first-actual)) AS delta_b_a,
          avg(abs(first-actual)-abs(persistence-actual)) AS delta_a_persistence,
          avg(abs("both"-actual)-abs(persistence-actual)) AS delta_b_persistence"""
    groups = {}
    for name, columns, condition in [
        ("channel", "channel", ""),
        ("horizon", "channel,horizon", ""),
        ("station", "channel,station_key", ""),
        ("station_horizon", "channel,station_key,horizon", ""),
        ("high", "channel", "WHERE high"),
    ]:
        groups[name] = (
            db.sql(
                f"SELECT {columns},{metrics} FROM pairs {condition} "
                f"GROUP BY {columns} ORDER BY {columns}"
            )
            .to_arrow_table()
            .to_pylist()
        )
    return {"targets": rows, "station_target_hours": station_hours, "groups": groups}


def training_events(log, recovered_tails):
    """Registrar el relleno NUL sin salto de línea que dejó un apagado del nodo."""
    with log.open("rb") as stream:
        for number, line in enumerate(stream, start=1):
            if number > 1 and not line.strip(b"\x00"):
                recovered_tails[log.name] = {"nul_bytes": len(line), "sha256": sha256_file(log)}
                return
            yield json.loads(line)


def verify_fit(run, view, policy):
    train = policy["training"]
    scheduled = train["updates"]
    step = run / f"step-{scheduled:08d}"
    if (run / "best").read_text().strip() != step.name or (
        run / "latest"
    ).read_text().strip() != step.name:
        raise ValueError("El estado seleccionado debe ser el último paso programado")
    manifest = json.loads((step / "manifest.json").read_text())
    identity = manifest["identity"]
    wanted = dict(
        model=policy["base_revision"],
        weights=policy["weights_sha256"],
        trainer=policy["trainer_commit"],
        data=policy["train"]["npz_sha256"],
        validation=policy["validation"]["npz_sha256"],
        batch=train["batch"],
        schedule=scheduled,
        precision=train["precision"],
        world=1,
        mode="single",
        lora=True,
        seed=train["seed"],
        head=policy["head"],
        validate_at="final",
        initial_trainable_sha256=policy["pilot_train_only"][view]["initial_trainable_sha256"],
        joint=dict(
            view=view,
            channels=list(PARAMS),
            targets=list(PARAMS),
            horizon=6,
            version=policy["input_version"],
            scaler_sha256=policy["scaler_sha256"],
        ),
    )
    if manifest["step"] != scheduled or any(identity.get(k) != v for k, v in wanted.items()):
        raise ValueError("La identidad del estado no corresponde al protocolo pareado")
    actual_files = {
        str(p.relative_to(step)): {"size": p.stat().st_size, "sha256": sha256_file(p)}
        for p in step.rglob("*")
        if p.is_file() and p != step / "manifest.json"
    }
    if not actual_files or manifest["files"] != actual_files:
        raise ValueError("El estado guardado difiere de su manifiesto")
    # Una reanudación puede volver a ejecutar el tramo posterior a un guardado.
    # Admitirlo solo cuando conserva exactamente exposición y tasa programada.
    steps = {}
    recovered_tails = {}
    for log in sorted(run.glob("events-*.jsonl")):
        for event in training_events(log, recovered_tails):
            if "window_ids" not in event:
                continue
            record = (event["window_ids"], event["learning_rate_next"])
            i = event["step"]
            if i in steps and steps[i] != record:
                raise ValueError("Intentos con diferente exposición")
            steps[i] = record
    if set(steps) != set(range(1, scheduled + 1)):
        raise ValueError("Faltan pasos del ajuste")
    order = hashlib.sha256()
    seen = 0
    for i in range(1, scheduled + 1):
        ids, lr = steps[i]
        count = train["final_batch"] if i == scheduled else train["batch"]
        expected_lr = train["lr"] * (1 + np.cos(np.pi * i / scheduled)) / 2
        if len(ids) != count or not np.isclose(lr, expected_lr, rtol=1e-8, atol=1e-14):
            raise ValueError("Lote o tasa fuera del calendario")
        order.update((json.dumps(ids, separators=(",", ":")) + "\n").encode())
        seen += count
    if order.hexdigest() != train["order_sha256"] or seen != policy["train"]["windows"]:
        raise ValueError("La secuencia efectivamente entrenada difiere del plan")
    return {
        "checkpoint": step.name,
        "checkpoint_sha256": sha256_file(step / "manifest.json"),
        "initial_trainable_sha256": identity["initial_trainable_sha256"],
        "steps": scheduled,
        "windows_seen": seen,
        "order_sha256": order.hexdigest(),
        "recovered_log_tails": recovered_tails,
    }


def evaluate(bundle, runs, replays, output, config=POLICY):
    if output.exists():
        raise FileExistsError(output)
    policy = json.loads(config.read_text())
    if sha256_file(bundle / "manifest.json") != policy["inputs_manifest_sha256"]:
        raise ValueError("Cambió la identidad del conjunto de entrenamiento")
    if sha256_file(bundle / "scaler.json") != policy["scaler_sha256"]:
        raise ValueError("Cambió el escalador de entrenamiento")
    path = bundle / "validation.npz"
    if sha256_file(path) != policy["validation"]["npz_sha256"]:
        raise ValueError("La validación difiere de la versión congelada")
    freeze = {
        "version": policy["version"],
        "policy_sha256": sha256_file(config),
        "split": "validation",
        "base_revision": policy["base_revision"],
        "base_weights_sha256": policy["weights_sha256"],
        "trainer_commit": policy["trainer_commit"],
        "image": policy["image"],
        "inputs_manifest_sha256": policy["inputs_manifest_sha256"],
        "scaler_sha256": policy["scaler_sha256"],
        "channels": list(PARAMS),
        "models": {},
    }
    with np.load(path, allow_pickle=False) as data:
        ids = data["window_id"]
        pred = []
        for view, run, replay in zip(VIEWS, runs, replays, strict=True):
            fit = verify_fit(run, view, policy)
            primary = run / (fit["checkpoint"] + "-validation.npz")
            with (
                np.load(primary, allow_pickle=False) as original,
                np.load(replay, allow_pickle=False) as restored,
            ):
                key = (ids, view, fit["checkpoint_sha256"], policy["scaler_sha256"])
                values = read_predictions(original, *key)
                if not np.array_equal(values, read_predictions(restored, *key)):
                    raise ValueError("Los pronósticos cambiaron al restaurar el estado")
                pred.append(values)
            freeze["models"][view] = {
                **fit,
                "predictions_sha256": sha256_file(primary),
                "replay_sha256": sha256_file(replay),
            }
        table = paired_table(data, *pred, json.loads((bundle / "scaler.json").read_text())["p95"])
    with TemporaryDirectory(dir=output.parent) as temp, duckdb.connect() as db:
        db.register("pairs", table)
        stats = summarize(db)
        if stats["targets"] != 533496 or stats["station_target_hours"] != 44948:
            raise ValueError("Los denominadores de validación difieren del plan")
        stage = Path(temp) / "resultado"
        stage.mkdir()
        pq.write_table(table, stage / "paired.parquet", compression="zstd")
        write_json(stage / "metrics.json", stats)
        freeze.update(
            metrics_sha256=sha256_file(stage / "metrics.json"),
            paired_sha256=sha256_file(stage / "paired.parquet"),
        )
        write_json(stage / "freeze.json", freeze)
        stage.rename(output)
    return freeze


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "first_run", "both_run", "first_replay", "both_replay", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            evaluate(
                args.bundle,
                [args.first_run, args.both_run],
                [args.first_replay, args.both_replay],
                args.output,
            )
        )
    )
