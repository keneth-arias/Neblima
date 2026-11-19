# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = ["matplotlib==3.10.7", "numpy==2.3.5", "pyyaml==6.0.3"]
# ///
"""Graficar el MAE reservado y las dos ventanas elegidas en validación."""

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml
from matplotlib.figure import Figure

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def draw(inputs, report, output):
    config = ROOT / "configs/training/lima-pm25-finalistas-v1.yaml"
    selected = yaml.safe_load(config.read_text())
    result = json.loads(report.read_text())
    scores = result["models"]
    if result["selection_sha256"] != digest(config):
        raise ValueError("La figura requiere el informe de los finalistas aprobados")
    validation = inputs / "validation.npz"
    predictions = inputs / "fits/direct-lora/validation.npz"
    policy = yaml.safe_load((ROOT / "configs/training.yaml").read_text())
    evidence = json.loads((ROOT / "metadata/qwen-validation-lora.json").read_text())
    if (
        digest(validation) != policy["npz_sha256"]["validation"]
        or digest(predictions) != evidence["predictions_sha256"]
    ):
        raise ValueError("Las ventanas o predicciones de validación difieren de la selección")
    stations = yaml.safe_load((ROOT / "configs/weather-alignment.yaml").read_text())["stations"]
    names = {row["station_key"]: row["name"].replace("_", " ").title() for row in stations}
    fig = Figure(figsize=(9, 9.5))
    axes = fig.subplots(3, 1)
    fig.subplots_adjust(left=0.10, right=0.97, top=0.95, bottom=0.10, hspace=0.69)
    hours = np.arange(1, 7)
    color = "#00776e"
    for model, label, shade, marker in [
        ("persistence", "Persistencia", "#a24a14", "s"),
        ("cnn", "Red convolucional", "#785f9a", "^"),
        (selected["qwen"]["model"], "Qwen con LoRA", color, "o"),
    ]:
        axes[0].plot(
            hours,
            [scores[model]["by_horizon"][str(h)]["mae"] for h in hours],
            label=label,
            color=shade,
            marker=marker,
        )
    axes[0].set(
        title="Prueba reservada · Error absoluto medio por hora de pronóstico",
        xlabel="Horas desde el origen",
        ylabel="MAE (µg/m³)",
        xticks=hours,
        ylim=(0, None),
    )
    axes[0].legend(frameon=False, ncol=3, fontsize=9)
    with (
        np.load(validation, allow_pickle=False) as windows,
        np.load(predictions, allow_pickle=False) as forecasts,
    ):
        for axis, (group, example) in zip(
            axes[1:], selected["validation_examples"].items(), strict=True
        ):
            (i,) = np.flatnonzero(windows["window_id"] == example["window_id"])
            (j,) = np.flatnonzero(forecasts["window_id"] == example["window_id"])
            history = windows["history"][i]
            kind = "menor error" if group == "improvement" else "mayor error"
            place = names[example["station_key"]].replace(" De ", " de ")
            date = datetime.fromisoformat(example["origin_at"]).strftime("%d/%m/%Y %H:%M")
            axis.set(
                title=f"Validación · {place} · {kind} que persistencia\nOrigen: {date} UTC",
                xlabel="Horas respecto al origen",
                ylabel="PM2.5 (µg/m³)",
                xlim=(-23.5, 6.5),
                xticks=[-23, -18, -12, -6, 0, 3, 6],
            )
            axis.axvline(0, linewidth=1, color="#888888", linestyle=":")
            axis.plot(np.arange(-23, 1), history, color="#425368", label="Historia")
            axis.plot(hours, windows["targets"][i], marker="o", color="#252525", label="Observado")
            axis.plot(
                hours,
                np.repeat(history[-1], 6),
                linestyle="--",
                color="#a24a14",
                label="Persistencia",
            )
            axis.plot(
                hours, forecasts["predicted"][j], marker="D", color=color, label="Qwen con LoRA"
            )
            axis.legend(frameon=False, ncol=4, fontsize=8)
    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="y", alpha=0.22)
    fig.text(
        0.10,
        0.024,
        "Fuente: SENAMHI, Monitoreo de los contaminantes del aire en Lima Metropolitana "
        "(ODC-BY-1.0).\n"
        "Pronósticos y evaluación retrospectiva: AirAware Perú, equipo Cuybernautas.",
        fontsize=8,
        color="#454545",
    )
    with output.open("xb") as stream:
        fig.savefig(stream, dpi=145, format="png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("inputs", "report", "output"):
        parser.add_argument(key, type=Path)
    draw(**vars(parser.parse_args()))
