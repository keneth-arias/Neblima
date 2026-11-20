"""Conciliar el diagnóstico retrospectivo publicado con las observaciones y predicciones de bm."""

import argparse
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import numpy as np
from episode_calibration import check_file
from episode_score import block_difference, scores
from holdout_station_windows import cohort
from station_receipts import audit

METADATA = Path(__file__).resolve().parents[2] / "metadata"
RESULTS = METADATA / "campo-marte-inmediato-v1"


def read(path):
    return json.loads(path.read_bytes())


def compare(expected, actual):
    if expected is None or actual is None:
        if expected is not actual:
            raise ValueError("El resultado publicado difiere en la ausencia de mediciones")
        return
    a, b = np.asarray(expected), np.asarray(actual)
    if a.shape != b.shape or not np.allclose(a, b, rtol=1e-7, atol=1e-9):
        raise ValueError(
            f"El resultado calculado difiere del publicado: {actual} frente a {expected}"
        )


def partitions(hours, cut):
    return hours + 6 < cut, hours - 23 >= cut


def identities(ids):
    raw = json.dumps(ids.tolist(), sort_keys=True, indent=2) + "\n"
    return hashlib.sha256(raw.encode()).hexdigest()


def archive(path):
    query = """
        SELECT hora_nativa, min(valor) FROM read_parquet(?)
        WHERE fuente = 'senamhi_horario' AND grupo = 'benchmark' AND id_estacion = '112194'
          AND unidad = 'µg/m³' AND parametro = 'pm25'
          AND hora_nativa >= TIMESTAMP '2024-06-01' AND hora_nativa < TIMESTAMP '2026-11-12'
        GROUP BY hora_nativa
        HAVING count(DISTINCT id_sensor) <= 1
          AND count(DISTINCT valor) FILTER (WHERE isfinite(valor)) = 1
          AND count(*) FILTER (WHERE valor IS NOT NULL AND NOT isfinite(valor)) = 0
        ORDER BY hora_nativa
    """
    with duckdb.connect() as db:
        rows = db.execute(query, [str(path)]).fetchall()
    times = np.array([stamp for stamp, _ in rows], dtype="datetime64[h]")
    windows = np.lib.stride_tricks.sliding_window_view(np.array([v for _, v in rows]), 30)
    complete = times[29:] - times[:-29] == np.timedelta64(29, "h")
    ids = np.array(["112194/" + str(x) for x in times[23:-6][complete].astype("datetime64[s]")])
    values = windows[complete]
    return ids, values[:, 23].astype("f4"), values[:, 24:]


def check_paired(row, hours, delta):
    for key, value in block_difference(hours, delta, 168).items():
        compare(row[key], value)


def compare_calibration(report, hours, values, original, candidate, groups, threshold):
    periods = np.broadcast_to(hours[:, None], values.shape)
    horizons = np.arange(1, 7)
    targets = periods + horizons
    valid = np.isfinite(values)
    high = valid & (values >= threshold)
    covered = [(lo <= values) & (values <= hi) for lo, hi in (original, candidate)]
    widths = [hi - lo for lo, hi in (original, candidate)]

    def check_row(row, mask, paired=False):
        compare(row["pairs"], mask.sum())
        compare(row["station_hours"], len(np.unique(targets[mask])))
        for name, cover, width in zip(("original", "candidate"), covered, widths, strict=True):
            compare(row[name]["coverage"], cover[mask].mean() if mask.any() else None)
            compare(row[name]["width"], width[mask].mean() if mask.any() else None)
        if paired:
            check_paired(
                row["paired_coverage"],
                periods[mask],
                covered[1][mask].astype(float) - covered[0][mask],
            )
            check_paired(row["paired_width"], periods[mask], (widths[1] - widths[0])[mask])

    check_row(report["overall"], valid, paired=True)
    check_row(report["observed_high"], high, paired=True)
    for key, mask in (("by_horizon", valid), ("high_by_horizon", high)):
        for h, row in zip(horizons, report[key], strict=True):
            check_row(row, mask & (horizons == h))
    for group, row in zip(range(4), report["by_forecast_quartile"], strict=True):
        check_row(row, valid & (groups == group))
    pooled = report["overall"]
    gates = {
        "pooled_coverage": 0.75 <= pooled["candidate"]["coverage"] <= 0.85,
        "smaller_mean_width": pooled["candidate"]["width"] < pooled["original"]["width"],
        "retains_high_coverage": bool(covered[1][high].sum() >= covered[0][high].sum())
        if high.any()
        else None,
    }
    decision = "inconclusive"
    if high.any():
        decision = "qualifies_for_independent_shadow" if all(gates.values()) else "reject_candidate"
    if gates != report["gates"] or report["decision"] != decision:
        raise ValueError("La decisión difiere de las tres condiciones registradas")


def calibration(ids, hours, last, y, pred, lows, highs, threshold):
    folder = RESULTS / "recalibracion"
    report = read(folder / "comparacion.json")
    protocol = read(check_file(folder / "protocolo.json", report["protocol_sha256"]))
    check_file(RESULTS / "archivo.json", protocol["archive_report_sha256"])
    model = read(check_file(folder / "candidato.json", report["candidate_sha256"]))
    train, evaluation = partitions(hours, np.datetime64(protocol["cut"], "h").astype(int))
    if (
        model["protocol_sha256"] != report["protocol_sha256"]
        or identities(ids[train]) != model["calibration_ids_sha256"]
        or identities(ids[evaluation]) != report["eval_ids_sha256"]
        or hashlib.sha256(y[train].astype("<f8").tobytes()).hexdigest()
        != model["calibration_targets_sha256"]
    ):
        raise ValueError("Los bloques difieren de los del candidato registrado")
    compare(
        [report["n_calibration"], report["n_comparison"], report["n_purged"]],
        [train.sum(), evaluation.sum(), (~(train | evaluation)).sum()],
    )
    p = pred[evaluation].astype("f8")
    for name, mask in (("calibration", train), ("comparison", evaluation)):
        if (ids[mask][0], ids[mask][-1]) != (report["first_" + name], report["last_" + name]):
            raise ValueError("Los límites publicados difieren de los orígenes del bloque")
    lo, hi = np.empty_like(p), np.empty_like(p)
    quartiles = np.empty(p.shape, dtype=int)
    for i, horizon in zip(range(6), model["horizons"], strict=True):
        cuts = np.quantile(pred[train, i].astype("f8"), [0.25, 0.5, 0.75])
        compare(horizon["cuts"], cuts)
        groups = np.searchsorted(cuts, pred[train, i], side="right")
        errors = y[train, i] - pred[train, i]
        for group, params in zip(range(4), horizon["bins"], strict=True):
            selected = groups == group
            compare([params["n"], params["pooled"]], [selected.sum(), selected.sum() < 200])
            compare(
                params["q"],
                np.quantile(errors if params["pooled"] else errors[selected], [0.1, 0.9]),
            )
        offsets = np.array([b["q"] for b in horizon["bins"]])
        ix = np.searchsorted(cuts, p[:, i], side="right")
        quartiles[:, i] = ix
        lo[:, i], hi[:, i] = np.maximum(0, p[:, i, None] + offsets[ix]).T
    values = y[evaluation]
    compare_calibration(
        report,
        hours[evaluation],
        values,
        (lows[evaluation], highs[evaluation]),
        (lo, hi),
        quartiles,
        threshold,
    )
    audit_report = read(folder / "verificacion.json")
    offsets = np.arange(-23, 7)
    shared = np.intersect1d(hours[train, None] + offsets, hours[evaluation, None] + offsets)
    if shared.size or audit_report["shared_station_hours"] != 0:
        raise ValueError("Los bloques de calibración y comparación comparten horas")
    high = values >= threshold
    high_origin = last[evaluation, None] >= threshold
    for key, mask in (
        ("observed_high", high),
        ("observed_high_from_high_origin", high & high_origin),
        ("observed_high_from_origin_below_threshold", high & ~high_origin),
    ):
        expected = {
            "pairs": int(mask.sum()),
            "upper_below_target": int((mask & (hi < values)).sum()),
            "lower_above_target": int((mask & (lo > values)).sum()),
        }
        if audit_report[key] != expected:
            raise ValueError("El conteo de errores en horas altas difiere de la verificación")


def previous_origins(data):
    root = data / "processed/pm-bivariado-20261120/timef/senamhi_horario"
    control = root / "airaware/lima-pm25-pm10-senamhi-horario/0.1.0/control.duckdb"
    query = """
        SELECT DISTINCT json_extract_string(t.metadata, '$.origin_at')
        FROM tasks t JOIN task_record_refs USING (task_id) JOIN records r USING (record_id)
        WHERE json_extract_string(r.metadata, '$.station_key') = '112194' AND t.split = 'test'
    """
    with duckdb.connect(str(control), read_only=True) as db:
        return {row[0] for row in db.execute(query).fetchall()}


def predictions(path, digest, ids, checkpoint):
    with np.load(check_file(path, digest), allow_pickle=False) as matrix:
        if not (
            str(matrix["checkpoint_sha256"]) == checkpoint
            and np.array_equal(ids, matrix["window_id"])
            and np.array_equal(np.arange(1, 7), matrix["forecast_hour"])
        ):
            raise ValueError("La identidad de las predicciones difiere")
        p = matrix["predicted"]
    if p.shape != (len(ids), 6) or not np.isfinite(p).all():
        raise ValueError("Forma o valores inválidos en las predicciones")
    return p


def verify_live_predictions(work, issued, residuals):
    record = read(work / "inferencia.json")
    for key in ("checkpoint_sha256", "bundle_sha256", "output_sha256", "run_id", "image"):
        if record[key] != issued[key]:
            raise ValueError("La emisión difiere del recibo de inferencia")
    origin = datetime.fromisoformat(issued["origin"])
    ids = ["112194/" + origin.isoformat()]
    p = predictions(
        work / "predicciones.npz", record["output_sha256"], ids, record["checkpoint_sha256"]
    )[0]
    lo, hi = np.maximum(0, p + np.asarray(residuals))
    for h, row in zip(range(6), issued["hours"], strict=True):
        label = (origin + timedelta(hours=h + 1)).isoformat()
        if row["station_label"] != label or (row["qwen"], row["lower80"], row["upper80"]) != (
            p[h],
            lo[h],
            hi[h],
        ):
            raise ValueError("Los valores o las horas de la emisión difieren de la salida privada")


def frozen_threshold(seal, diagnostic):
    config = METADATA.parent / "configs/training/lima-prueba-futura-campo-marte-v1.json"
    station = read(check_file(config, seal["protocol_sha256"]))
    table = read(check_file(RESULTS / "umbrales-entrenamiento.json", seal["thresholds_sha256"]))
    if station["thresholds_sha256"] != seal["thresholds_sha256"]:
        raise ValueError("La huella de umbrales difiere de la registrada en el sello")
    if station["station_code"] != diagnostic["station"] or diagnostic["station"] != "112194":
        raise ValueError("La estación del diagnóstico difiere de la registrada")
    threshold = table["stations"][station["historical_station_key"]]
    if (
        table["unit"] != diagnostic["unit"]
        or table["method"] != "linear_p95_unique_training_station_hours"
        or threshold != diagnostic["threshold_ug_m3"]
    ):
        raise ValueError("El umbral del diagnóstico difiere de la tabla de entrenamiento")
    return threshold


def verify(data):
    root = data / "processed/evaluacion-inmediata-campo-marte-20261120"
    seal = read(METADATA / "seleccion-concentracion-lima-v1/sello.json")
    cal = read(
        check_file(
            METADATA / "seleccion-concentracion-lima-v1/calibrador-directo.json",
            seal["direct_calibrator_sha256"],
        )
    )
    threshold = frozen_threshold(seal, read(RESULTS / "recalibracion/protocolo.json"))
    previous = previous_origins(data)
    overlap = read(RESULTS / "interseccion-88.json")
    compare(overlap["cohort_88_station_origins"], len(previous))
    for name in ("reciente", "archivo"):
        report = read(RESULTS / (name + ".json"))
        if name == "reciente":
            spec = read(
                check_file(root / "disponibilidad.json", report["evidence"]["availability_sha256"])
            )
            raw = audit(
                data / "raw/evaluacion-inmediata-campo-marte-20261120",
                through=spec["as_of_utc"],
                include_receipts=True,
            )
            if raw["receipts"] != spec["receipts"]:
                raise ValueError("Los recibos recientes difieren del inventario")
            _, ids, x, y = cohort(spec, raw["changes"])
            last = x[:, -1]
        else:
            parquet = data / "processed/lima-postcorte-20261118/observaciones.parquet"
            ids, last, y = archive(check_file(parquet, report["evidence"]["parquet_sha256"]))
        origins = {s.split("/")[1] for s in ids}
        shared = overlap["shared_station_origins"][name]
        compare(
            [shared["in_replay"], shared["also_in_88"]], [len(origins), len(previous & origins)]
        )
        path = root / "corridas" / f"campo-pm25-{name}-20261120" / "predicciones.npz"
        if report["checkpoint_sha256"] != seal["checkpoint_sha256"]:
            raise ValueError("El modelo difiere del sello")
        p = predictions(path, report["output_sha256"], ids, seal["checkpoint_sha256"])
        compare(report["windows"], len(ids))
        lo, hi = np.maximum(0, p[None, :, :] + np.array(cal["residual_q10_q90"])[:, None, :])
        hours = np.array([np.datetime64(s.split("/")[1], "h").astype(int) for s in ids])
        target = hours[:, None] + np.arange(1, 7)
        metrics = scores(y, p, lo, hi, np.full(len(ids), threshold))
        base_error = np.abs(y - last[:, None])
        delta = np.abs(y - p) - base_error
        periods = np.broadcast_to(hours[:, None], y.shape)
        for key, table, mask in (
            ("all", "by_horizon", np.isfinite(y)),
            ("high", "high_by_horizon", y >= threshold),
        ):
            row = report[key]
            for field, value in metrics[key].items():
                compare(row[field], value)
            compare(row["distinct_station_hours"], len(np.unique(target[mask])))
            compare(row["mae_persistence"], base_error[mask].mean() if mask.any() else None)
            for i, (actual, published) in enumerate(
                zip(metrics[table], report[table], strict=True)
            ):
                selected = mask[:, i]
                actual["mae_persistence"] = (
                    base_error[selected, i].mean() if selected.any() else None
                )
                for field, value in actual.items():
                    compare(published[field], value)
            if name == "archivo":
                check_paired(row["paired_mae_difference"], periods[mask], delta[mask])
        if name == "archivo":
            calibration(ids, hours, last, y, p, lo, hi, threshold)
    first = read(RESULTS / "primera-emision.json")
    key = datetime.fromisoformat(first["origin"]).strftime("%Y%m%d%H")
    local = root / "en-vivo/issuances" / (key + ".json")
    issued = read(check_file(local, first["issue_sha256"]))
    if any(issued[k] != v for k, v in first.items() if k != "issue_sha256"):
        raise ValueError("El recibo de la primera emisión difiere")
    if issued["checkpoint_sha256"] != seal["checkpoint_sha256"] or issued["image"] != seal["image"]:
        raise ValueError("La emisión difiere del modelo reservado")
    verify_live_predictions(
        root / "corridas" / ("campo-live-" + key), issued, cal["residual_q10_q90"]
    )
    cutoff = first["input_cutoff_utc"]
    raw = audit(data / "raw/campo-marte-operativo-20261120", through=cutoff, include_receipts=True)
    latest = raw["receipts"][-1]
    if (latest["receipt_sha256"], latest["seen_utc"]) != (first["receipt_sha256"], cutoff):
        raise ValueError("La fuente difiere del recibo usado al emitir")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("datos", type=Path)
    verify(cli.parse_args().datos)
    print("Diagnósticos y primera emisión conciliados")
