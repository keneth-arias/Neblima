"""Conciliar el diagnóstico retrospectivo publicado con las observaciones y predicciones de bm."""

import argparse
import hashlib
import json
from pathlib import Path

import duckdb
import numpy as np
from episode_calibration import check_file
from episode_score import block_difference
from holdout_station_windows import cohort
from station_receipts import audit

METADATA = Path(__file__).resolve().parents[2] / "metadata"
RESULTS = METADATA / "campo-marte-inmediato-v1"


def read(path):
    return json.loads(path.read_bytes())


def compare(expected, actual):
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


def compare_intervals(row, values, lo, hi, mask):
    compare(row["pairs"], mask.sum())
    for i, name in enumerate(("original", "candidate")):
        compare(row[name]["coverage"], ((lo[i] <= values) & (values <= hi[i]))[mask].mean())
        compare(row[name]["width"], (hi[i] - lo[i])[mask].mean())


def calibration(ids, hours, y, pred, lows, highs, threshold):
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
    lo, hi = np.empty_like(p), np.empty_like(p)
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
        lo[:, i], hi[:, i] = np.maximum(0, p[:, i, None] + offsets[ix]).T
    values = y[evaluation]
    for label, mask in (("overall", np.isfinite(values)), ("observed_high", values >= threshold)):
        row = report[label]
        compare_intervals(row, values, [lows[evaluation], lo], [highs[evaluation], hi], mask)
        cover = ((lo <= values) & (values <= hi)).astype(float)
        cover -= (lows[evaluation] <= values) & (values <= highs[evaluation])
        origins = np.broadcast_to(hours[evaluation, None], values.shape)
        ci = block_difference(origins[mask], cover[mask], 168)
        compare(row["paired_coverage"]["ci95"], ci["ci95"])
    pooled, high = report["overall"], report["observed_high"]
    gates = {
        "pooled_coverage": 0.75 <= pooled["candidate"]["coverage"] <= 0.85,
        "smaller_mean_width": pooled["candidate"]["width"] < pooled["original"]["width"],
        "retains_high_coverage": high["candidate"]["coverage"] >= high["original"]["coverage"],
    }
    if gates != report["gates"] or report["decision"] != (
        "qualifies_for_independent_shadow" if all(gates.values()) else "reject_candidate"
    ):
        raise ValueError("La decisión difiere de las tres condiciones registradas")


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


def verify(data):
    root = data / "processed/evaluacion-inmediata-campo-marte-20261120"
    seal = read(METADATA / "seleccion-concentracion-lima-v1/sello.json")
    cal = read(
        check_file(
            METADATA / "seleccion-concentracion-lima-v1/calibrador-directo.json",
            seal["direct_calibrator_sha256"],
        )
    )
    threshold = read(RESULTS / "recalibracion/protocolo.json")["threshold_ug_m3"]
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
        with np.load(check_file(path, report["output_sha256"]), allow_pickle=False) as matrix:
            if not (
                str(matrix["checkpoint_sha256"])
                == seal["checkpoint_sha256"]
                == report["checkpoint_sha256"]
                and np.array_equal(ids, matrix["window_id"])
                and np.array_equal(np.arange(1, 7), matrix["forecast_hour"])
            ):
                raise ValueError("La identidad de las predicciones difiere")
            p = matrix["predicted"]
        if p.shape != y.shape or not np.isfinite(p).all():
            raise ValueError("Forma o valores inválidos en las predicciones")
        compare(report["windows"], len(ids))
        lo, hi = np.maximum(0, p[None, :, :] + np.array(cal["residual_q10_q90"])[:, None, :])
        hours = np.array([np.datetime64(s.split("/")[1], "h").astype(int) for s in ids])
        target = hours[:, None] + np.arange(1, 7)
        for key, mask in (("all", np.isfinite(y)), ("high", y >= threshold)):
            row = report[key]
            compare(
                [row["targets"], row["distinct_station_hours"]],
                [mask.sum(), len(np.unique(target[mask]))],
            )
            if mask.any():
                compare(
                    [row["mae"], row["mae_persistence"], row["coverage"], row["width"]],
                    [
                        np.abs(y - p)[mask].mean(),
                        np.abs(y - last[:, None])[mask].mean(),
                        ((lo <= y) & (y <= hi))[mask].mean(),
                        (hi - lo)[mask].mean(),
                    ],
                )
            elif any(row[k] is not None for k in ("mae", "mae_persistence", "coverage", "width")):
                raise ValueError("Un estrato vacío tiene métricas definidas")
            if name == "archivo":
                origins_matrix = np.broadcast_to(hours[:, None], y.shape)
                delta = np.abs(y - p) - np.abs(y - last[:, None])
                computed = block_difference(origins_matrix[mask], delta[mask], 168)
                expected = row["paired_mae_difference"]
                for field in ("blocks", "ci95", "difference"):
                    compare(expected[field], computed[field])
        if name == "archivo":
            calibration(ids, hours, y, p, lo, hi, threshold)
    first = read(RESULTS / "primera-emision.json")
    key = np.datetime64(first["origin"], "h")
    local = root / "en-vivo/issuances" / (str(key).replace("-", "").replace("T", "") + ".json")
    issued = read(check_file(local, first["issue_sha256"]))
    if any(issued[k] != v for k, v in first.items() if k != "issue_sha256"):
        raise ValueError("El recibo de la primera emisión difiere")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("datos", type=Path)
    verify(cli.parse_args().datos)
    print("Diagnósticos y primera emisión conciliados")
