# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = ["matplotlib==3.10.7"]
# ///
"""Graficar el cambio del error por horizonte en las dos pruebas externas."""

import argparse
import json
from pathlib import Path

from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator


def draw(openaq, senamhi, path):
    figure = Figure(figsize=(8.0, 3.65), dpi=170, layout="constrained")
    axes = figure.subplots(1, 2, sharex=True)
    for axis, channel, title in zip(axes, ("pm25", "pm10"), ("PM2.5", "PM10"), strict=True):
        axis.set_title(title, loc="left", fontweight="bold")
        axis.axhline(0, color="#58616a", linewidth=1)
        for dataset, name, marker, color, line in [
            (openaq, "OpenAQ", "o", "#175e8b", "-"),
            (senamhi, "SENAMHI horario", "s", "#ae5411", "--"),
        ]:
            rows = sorted(
                (r for r in dataset["groups"]["horizon"] if r["channel"] == channel),
                key=lambda r: r["horizon"],
            )
            axis.plot(
                [r["horizon"] for r in rows],
                [r["delta_b_a"] for r in rows],
                marker=marker,
                linestyle=line,
                label=name,
                color=color,
                markersize=5,
                markerfacecolor="white",
            )
        axis.yaxis.set_major_locator(MaxNLocator(nbins=5))
        axis.grid(axis="y", alpha=0.2)
        axis.set_xticks(range(1, 7))
        axis.set_xlabel("Horas desde el origen")
        axis.spines[["right", "top"]].set_visible(False)
    axes[0].set_ylabel("Cambio del MAE, B − A (µg/m³)")
    figure.legend(*axes[0].get_legend_handles_labels(), loc="outside lower center", ncols=2)
    figure.savefig(path, facecolor="white")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("openaq", "senamhi_horario", "output"):
        parser.add_argument(key, type=Path)
    args = parser.parse_args()
    draw(
        json.loads(args.openaq.read_text()),
        json.loads(args.senamhi_horario.read_text()),
        args.output,
    )
