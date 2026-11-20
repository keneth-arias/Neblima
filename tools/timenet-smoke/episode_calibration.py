"""Ajustar en calibración y aplicar a historias el intervalo y la probabilidad de episodio."""

import argparse
import json
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from episode_blocks import VERSION
from export_senamhi import sha256_file
from paired_forecasts import ordered_ids
from scipy.optimize import minimize
from scipy.special import expit

CALIBRATOR = "pm25-six-hour-calibration-v1"


def fit_residuals(predicted, observed):
    if (
        observed.shape != predicted.shape
        or predicted.ndim != 2
        or predicted.shape[1] != 6
        or not len(observed)
        or np.isinf(observed).any()
        or np.isnan(observed).all(axis=0).any()
        or not np.isfinite(predicted).all()
    ):
        raise ValueError("Se requieren seis pronósticos y seis mediciones finitas por ventana")
    return np.nanquantile(observed.astype(np.float64) - predicted, [0.1, 0.9], axis=0)


def fit_logistic(scores, labels):
    if (
        scores.ndim != 1
        or labels.shape != scores.shape
        or not len(scores)
        or not np.isfinite(scores).all()
        or not np.isin(labels, [0, 1]).all()
    ):
        raise ValueError("Puntajes o etiquetas de calibración inválidos")
    prevalence = float(np.mean(labels))
    if prevalence in (0, 1) or np.all(scores == scores[0]):
        return {
            "status": "single_class" if prevalence in (0, 1) else "constant_score",
            "frequency": prevalence,
        }
    center, scale = float(np.mean(scores)), float(np.std(scores))
    x = (scores - center) / scale

    def objective(params):
        intercept, slope = params
        z = intercept + slope * x
        diff = expit(z) - labels
        # Penalización L2 unitaria sobre la pendiente en escala estandarizada.
        loss = np.sum(np.logaddexp(0, z) - labels * z) + slope**2 / 2
        return loss, np.array([diff.sum(), np.dot(diff, x) + slope])

    result = minimize(
        objective,
        [np.log(prevalence / (1 - prevalence)), 0.0],
        jac=True,
        method="L-BFGS-B",
        bounds=[(None, None), (0, None)],
    )
    if not result.success:
        raise RuntimeError(f"El calibrador no convergió: {result.message}")
    return {
        "status": "fitted",
        "center": center,
        "scale": scale,
        "intercept": float(result.x[0]),
        "slope": float(result.x[1]),
        "l2": 1.0,
    }


def probability(scores, model):
    if not isinstance(model, dict) or not np.isfinite(scores).all():
        raise ValueError("Puntajes o modelo de probabilidad inválidos")
    status = model.get("status")
    if status in ("single_class", "constant_score"):
        freq = model.get("frequency")
        if (
            not isinstance(freq, (float, int))
            or not 0 <= freq <= 1
            or (status == "single_class" and freq not in (0, 1))
        ):
            raise ValueError("Frecuencia de calibración inválida")
        return np.full(scores.shape, freq, dtype=float)
    fields = ("center", "scale", "intercept", "slope")
    if (
        status != "fitted"
        or any(
            not isinstance(model.get(k), (int, float)) or not np.isfinite(model[k]) for k in fields
        )
        or model["scale"] <= 0
        or model["slope"] < 0
        or model.get("l2") != 1
    ):
        raise ValueError("Coeficientes de calibración inválidos")
    return expit(
        model["intercept"] + model["slope"] * ((scores - model["center"]) / model["scale"])
    )


def check_file(path, digest):
    if sha256_file(path) != digest:
        raise ValueError(f"La huella difiere para {path.name}")
    return path


def align(archive, ids, field):
    keys, order = ordered_ids(archive["window_id"])
    if not np.array_equal(keys, ids) or archive[field].shape[:1] != (len(ids),):
        raise ValueError(f"Los identificadores de {field} difieren del bloque")
    return archive[field][order]


def candidate_logits(path, digest, ids, threshold_digest, input_manifest_digest):
    with np.load(check_file(path, digest), allow_pickle=False) as archive:
        contract = {
            "task": "episode",
            "unit": "logit",
            "schema_version": 2,
            "thresholds_sha256": threshold_digest,
            "input_manifest_sha256": input_manifest_digest,
        }
        if any(archive[k].item() != v for k, v in contract.items()):
            raise ValueError("Exportación del clasificador incompatible")
        logits = align(archive, ids, "episode_logit")
        checkpoint = archive["checkpoint_sha256"].item()
        if (
            logits.shape != (len(ids),)
            or not np.isfinite(logits).all()
            or not isinstance(checkpoint, str)
            or not re.fullmatch("[0-9a-f]{64}", checkpoint)
        ):
            raise ValueError("Puntaje o punto de control inválidos")
        return logits, checkpoint


def run(args):
    fitting = args.command == "fit"
    phase = "calibration" if fitting else args.block
    if phase not in ("calibration", "selection"):
        raise ValueError("La repetición histórica solo permite calibración y selección")
    manifest = json.loads(
        check_file(args.blocks / "manifest.json", args.manifest_sha256).read_text()
    )
    if manifest["version"] != VERSION or manifest["unit"] != "ug/m3":
        raise ValueError("Versión de bloques o unidad incompatible")
    folder = args.blocks / phase
    files = manifest["blocks"][phase]["files"]
    with np.load(check_file(folder / "index.npz", files["index.npz"]), allow_pickle=False) as index:
        ids, order = ordered_ids(index["window_id"])
        stations = index["station_key"][order]
    threshold_hash = manifest["thresholds_sha256"]
    thresholds = json.loads(check_file(args.blocks / "thresholds.json", threshold_hash).read_text())
    limits = np.array([thresholds["stations"].get(s, np.nan) for s in stations])
    with np.load(args.forecasts, allow_pickle=False) as forecasts:
        predicted = align(forecasts, ids, "predicted")
        checkpoint = str(forecasts["checkpoint_sha256"].item())
        if (
            re.fullmatch("[0-9a-f]{64}", checkpoint) is None
            or predicted.dtype.kind not in "fiu"
            or predicted.shape != (len(ids), 6)
            or not np.array_equal(forecasts["forecast_hour"], np.arange(1, 7))
            or not np.isfinite(predicted).all()
        ):
            raise ValueError("Pronóstico horario incompatible")
    identity = {
        "version": CALIBRATOR,
        "unit": "ug/m3",
        "manifest_sha256": args.manifest_sha256,
        "thresholds_sha256": threshold_hash,
        "checkpoint_sha256": checkpoint,
    }
    scores = predicted.max(axis=1) - limits
    logits = getattr(args, "episode_logits", None)
    if logits:
        path, digest, input_digest = logits
        scores, episode_checkpoint = candidate_logits(
            Path(path), digest, ids, threshold_hash, input_digest
        )
        identity["episode_checkpoint_sha256"] = episode_checkpoint
        if fitting and args.eligible_labels is None:
            raise ValueError("El calibrador del clasificador requiere etiquetas elegibles")
    if fitting:
        with np.load(
            check_file(folder / "observed.npz", files["observed.npz"]), allow_pickle=False
        ) as observations:
            observed = align(observations, ids, "targets")
        artifact = {
            **identity,
            "calibration_forecasts_sha256": sha256_file(args.forecasts),
            "calibration_windows": len(ids),
            "residual_q10_q90": fit_residuals(predicted, observed).tolist(),
            "probability": None,
        }
        if logits:
            artifact["calibration_logits_sha256"] = logits[1]
        if args.eligible_labels is not None:
            with np.load(args.eligible_labels, allow_pickle=False) as labels:
                if (
                    str(labels["manifest_sha256"].item()) != args.manifest_sha256
                    or str(labels["thresholds_sha256"].item()) != threshold_hash
                ):
                    raise ValueError("Procedencia incompatible de las etiquetas")
                y = align(labels, ids, "event")
            if (
                y.shape != scores.shape
                or y.dtype.kind not in "biuf"
                or not np.isin(y, [-1, 0, 1]).all()
            ):
                raise ValueError("Etiquetas de episodio inválidas")
            if np.any((y != -1) & ~np.isfinite(observed).all(axis=1)):
                raise ValueError("La elegibilidad requiere seis objetivos medidos")
            valid = (y != -1) & np.isfinite(scores) & np.isfinite(limits)
            if not valid.any() or not np.array_equal(
                y[valid], observed[valid].max(axis=1) >= limits[valid]
            ):
                raise ValueError("Etiquetas elegibles incompatibles con el umbral")
            artifact.update(
                probability=fit_logistic(scores[valid], y[valid]),
                eligible=int(valid.sum()),
                labels_sha256=sha256_file(args.eligible_labels),
            )
        payload = (json.dumps(artifact, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    else:
        artifact = json.loads(check_file(args.calibrator, args.calibrator_sha256).read_text())
        if any(artifact.get(k) != v for k, v in identity.items()) or bool(logits) != (
            "episode_checkpoint_sha256" in artifact
        ):
            raise ValueError("El calibrador corresponde a otro modelo, bloque o umbral")
        q = np.asarray(artifact["residual_q10_q90"])
        if q.shape != (2, 6) or not np.isfinite(q).all() or (q[0] > q[1]).any():
            raise ValueError("Cuantiles incompatibles")
        values = {
            "window_id": ids,
            "forecast_hour": np.arange(1, 7),
            "predicted": predicted,
            "lower": np.maximum(0.0, predicted + q[0]),
            "upper": np.maximum(0.0, predicted + q[1]),
            "calibrator_sha256": args.calibrator_sha256,
            "manifest_sha256": args.manifest_sha256,
            "checkpoint_sha256": checkpoint,
            "block": phase,
        }
        if artifact["probability"] is not None:
            eligible = np.isfinite(scores) & np.isfinite(limits)
            probs = np.full(len(ids), np.nan)
            probs[eligible] = probability(scores[eligible], artifact["probability"])
            values.update(episode_probability=probs, threshold_available=eligible)
    with NamedTemporaryFile(dir=args.output.parent) as temp:
        if fitting:
            temp.write(payload)
        else:
            np.savez(temp, **values)
        temp.flush()
        os.link(temp.name, args.output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    fit = commands.add_parser("fit")
    fit.add_argument("--eligible-labels", type=Path)
    apply = commands.add_parser("apply")
    apply.add_argument("--block", choices=("selection",), required=True)
    apply.add_argument("--calibrator", type=Path, required=True)
    apply.add_argument("--calibrator-sha256", required=True)
    for command in (fit, apply):
        command.add_argument(
            "--episode-logits", nargs=3, metavar=("NPZ", "SHA256", "MANIFIESTO_SHA256")
        )
        command.add_argument("blocks", type=Path)
        command.add_argument("forecasts", type=Path)
        command.add_argument("output", type=Path)
        command.add_argument("--manifest-sha256", required=True)
    run(parser.parse_args())
