"""Evaluar una exportación sellada contra observaciones separadas por ID de ventana."""

import argparse
import json
import os
import random
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from episode_blocks import VERSION
from episode_calibration import align, check_file
from paired_forecasts import ordered_ids


def scores(
    y,
    predicted,
    lower,
    upper,
    limits,
    last=None,
    probabilities=None,
    labels=None,
    frequencies=None,
    hours=None,
):
    if (
        y.shape != predicted.shape
        or y.shape != lower.shape
        or y.shape != upper.shape
        or y.ndim != 2
        or y.shape[1] != 6
        or np.isinf(y).any()
        or not all(np.isfinite(a).all() for a in (predicted, lower, upper))
        or (lower > upper).any()
    ):
        raise ValueError("Mediciones, pronósticos o intervalos incompatibles")
    valid = np.isfinite(y)
    high = valid & (y >= limits[:, None])
    error = np.abs(y - predicted)
    covered = (lower <= y) & (y <= upper)
    width = upper - lower

    def summary(mask):
        return {
            "targets": int(mask.sum()),
            **{
                key: float(values[mask].mean()) if mask.any() else None
                for key, values in (("mae", error), ("coverage", covered), ("width", width))
            },
        }

    horizon = np.arange(1, 7)
    table = {
        "windows": len(y),
        "all": summary(valid),
        "high": summary(high),
        "by_horizon": [summary(valid & (horizon == h)) for h in horizon],
        "high_by_horizon": [summary(high & (horizon == h)) for h in horizon],
    }
    if probabilities is not None and labels is not None:
        if (
            last is None
            or last.shape != limits.shape
            or labels.shape != limits.shape
            or probabilities.shape != limits.shape
            or not np.isin(labels, [-1, 0, 1]).all()
            or np.any((labels != -1) & (~valid.all(axis=1) | ~np.isfinite(limits)))
        ):
            raise ValueError("Elegibilidad de episodio incompatible")
        eligible = labels != -1
        if (
            not np.array_equal(labels[eligible], high[eligible].any(axis=1))
            or not np.isfinite(probabilities[eligible]).all()
            or np.any((probabilities[eligible] < 0) | (probabilities[eligible] > 1))
        ):
            raise ValueError("Probabilidades o etiquetas incompatibles")
        table["event"] = {"ineligible": int((~eligible).sum())}
        for name, mask in (
            ("all", np.ones(len(labels), bool)),
            ("below", last < limits),
            ("active", last >= limits),
        ):
            take = eligible & mask
            table["event"][name] = {
                "windows": int(take.sum()),
                "prevalence": float(labels[take].mean()) if take.any() else None,
                "brier": float(np.mean((probabilities[take] - labels[take]) ** 2))
                if take.any()
                else None,
            }
            group = table["event"][name]
            group["persistence_brier"] = (
                float(np.mean(((last[take] >= limits[take]).astype(float) - labels[take]) ** 2))
                if take.any()
                else None
            )
            bins = np.zeros(len(probabilities), dtype=int)
            bins[eligible] = np.minimum(9, np.floor(probabilities[eligible] * 10).astype(int))
            group["reliability"] = []
            for i in range(10):
                members = take & (bins == i)
                group["reliability"].append(
                    {
                        "lower": i / 10,
                        "windows": int(members.sum()),
                        "forecast_mean": float(probabilities[members].mean())
                        if members.any()
                        else None,
                        "observed_rate": float(labels[members].mean()) if members.any() else None,
                    }
                )
            if frequencies is not None:
                paired = take & np.isfinite(frequencies)
                base = (frequencies[paired] - labels[paired]) ** 2
                candidate = (probabilities[paired] - labels[paired]) ** 2
                group["training_frequency_windows"] = int(paired.sum())
                group["training_frequency_brier"] = float(base.mean()) if paired.any() else None
                group["brier_difference"] = (
                    block_difference(hours[paired], candidate - base, 168)
                    if hours is not None
                    else None
                )
    return table


def block_difference(hours, values, size):
    if not len(values):
        return {"blocks": 0, "difference": None, "ci95": None}
    keys, groups = np.unique(hours // size, return_inverse=True)
    sums = np.bincount(groups, weights=values)
    counts = np.bincount(groups)
    result = {"blocks": len(keys), "difference": float(sums.sum() / counts.sum()), "ci95": None}
    if len(keys) > 1:
        rng = random.Random(27)
        draws = np.array([rng.choices(range(len(keys)), k=len(keys)) for _ in range(1000)])
        boot = sums[draws].sum(1) / counts[draws].sum(1)
        result["ci95"] = np.quantile(boot, [0.025, 0.975]).tolist()
    return result


def training_frequencies(blocks, manifest, manifest_sha, archive_spec, thresholds):
    files = manifest["blocks"]["train"]["files"]
    with np.load(
        check_file(blocks / "train/index.npz", files["index.npz"]), allow_pickle=False
    ) as index:
        ids, order = ordered_ids(index["window_id"])
        stations = index["station_key"][order]
    with np.load(check_file(Path(archive_spec[0]), archive_spec[1]), allow_pickle=False) as archive:
        if (
            archive["manifest_sha256"].item() != manifest_sha
            or archive["thresholds_sha256"].item() != manifest["thresholds_sha256"]
        ):
            raise ValueError("Etiquetas de entrenamiento incompatibles")
        labels = align(archive, ids, "event")
    with np.load(
        check_file(blocks / "train/observed.npz", files["observed.npz"]), allow_pickle=False
    ) as archive:
        y = align(archive, ids, "targets")
    valid = labels != -1
    limits = np.array([thresholds["stations"].get(s, np.nan) for s in stations])
    if (
        labels.shape != (len(ids),)
        or not np.isin(labels, [-1, 0, 1]).all()
        or np.any(valid & (~np.isfinite(y).all(1) | ~np.isfinite(limits)))
        or not np.array_equal(labels[valid], (y[valid] >= limits[valid, None]).any(1))
    ):
        raise ValueError("Etiqueta histórica incompatible con el seguimiento admisible")
    return {s: float(labels[valid & (stations == s)].mean()) for s in np.unique(stations[valid])}


def evaluate(
    blocks, manifest_sha, forecast, forecast_sha, label_archive=None, training_labels=None
):
    manifest = json.loads(check_file(blocks / "manifest.json", manifest_sha).read_text())
    if manifest["version"] != VERSION or manifest["unit"] != "ug/m3":
        raise ValueError("Versión o unidades incompatibles")
    folder = blocks / "selection"

    def open_input(name):
        return np.load(
            check_file(folder / name, manifest["blocks"]["selection"]["files"][name]),
            allow_pickle=False,
        )

    with open_input("index.npz") as index:
        ids, order = ordered_ids(index["window_id"])
        stations = index["station_key"][order]
        hours = index["origin_hour"][order]
    with open_input("observed.npz") as observed, open_input("history.npz") as histories:
        y = align(observed, ids, "targets")
        last = align(histories, ids, "history")[:, -1]
    thresholds = json.loads(
        check_file(blocks / "thresholds.json", manifest["thresholds_sha256"]).read_text()
    )
    limits = np.array([thresholds["stations"].get(s, np.nan) for s in stations])
    with np.load(check_file(forecast, forecast_sha), allow_pickle=False) as archive:
        if (
            archive["manifest_sha256"].item() != manifest_sha
            or archive["block"].item() != "selection"
            or not np.array_equal(archive["forecast_hour"], np.arange(1, 7))
        ):
            raise ValueError("La predicción corresponde a otro bloque")
        values = [align(archive, ids, k) for k in ("predicted", "lower", "upper")]
        probabilities = (
            align(archive, ids, "episode_probability") if "episode_probability" in archive else None
        )
    labels = None
    if label_archive:
        path, digest = label_archive
        with np.load(check_file(Path(path), digest), allow_pickle=False) as archive:
            if (
                probabilities is None
                or archive["manifest_sha256"].item() != manifest_sha
                or archive["thresholds_sha256"].item() != manifest["thresholds_sha256"]
            ):
                raise ValueError("Procedencia incompatible de las etiquetas")
            labels = align(archive, ids, "event")

    frequencies = None
    if training_labels is not None:
        if labels is None:
            raise ValueError("Falta la elegibilidad de selección")
        rates = training_frequencies(blocks, manifest, manifest_sha, training_labels, thresholds)
        frequencies = np.array([rates.get(s, np.nan) for s in stations])

    def group(mask):
        return scores(
            y[mask],
            *(v[mask] for v in values),
            limits[mask],
            last[mask],
            probabilities[mask] if probabilities is not None else None,
            labels[mask] if labels is not None else None,
            frequencies[mask] if frequencies is not None else None,
            hours[mask],
        )

    return {
        "version": "pm25-episode-score-v1",
        "purpose": "retrospective_replay",
        "manifest_sha256": manifest_sha,
        "forecast_sha256": forecast_sha,
        "training_labels_sha256": training_labels[1] if training_labels else None,
        "labels_sha256": label_archive[1] if label_archive else None,
        "overall": group(np.ones(len(ids), bool)),
        "stations": {s: group(stations == s) for s in np.unique(stations)},
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("blocks", type=Path)
    p.add_argument("forecast", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--manifest-sha256", required=True)
    p.add_argument("--forecast-sha256", required=True)
    p.add_argument("--eligible-labels", nargs=2, metavar=("NPZ", "SHA256"))
    p.add_argument("--training-labels", nargs=2, metavar=("NPZ", "SHA256"))
    a = p.parse_args()
    result = evaluate(
        a.blocks,
        a.manifest_sha256,
        a.forecast,
        a.forecast_sha256,
        a.eligible_labels,
        a.training_labels,
    )
    with NamedTemporaryFile(dir=a.output.parent) as tmp:
        tmp.write((json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())
        tmp.flush()
        os.link(tmp.name, a.output)
