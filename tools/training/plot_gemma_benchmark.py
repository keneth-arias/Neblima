# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = ["matplotlib==3.10.7"]
# ///
"""Comparar los errores de Gemma 1B y la CNN en los dos archivos publicados."""

import json
from pathlib import Path

from matplotlib.figure import Figure

ROOT = Path(__file__).resolve().parents[2]


def main():
    report = json.loads((ROOT / "metadata/resultados-gemma-1b-20261123/benchmark.json").read_text())
    figure = Figure(figsize=(8, 3.8), layout="constrained")
    axes = figure.subplots(1, 2, sharey=True)
    for ax, source, title in zip(axes, ("openaq", "senamhi"), ("OpenAQ", "SENAMHI"), strict=True):
        archive = report["archives"][source]
        for model, label, color, marker in (
            ("gemma", "Gemma 3 1B", "#2043a6", "o"),
            ("cnn", "CNN", "#a04e20", "x"),
        ):
            points = archive[model]["by_horizon"]
            ax.plot(
                range(1, 7),
                [points[str(h)]["mae"] for h in range(1, 7)],
                color=color,
                marker=marker,
                label=label,
            )
        ax.set(
            title=f"{title} · {archive['windows']:,} ventanas",
            xlabel="Horizonte (horas)",
            xticks=range(1, 7),
            ylim=(0, 8),
        )
        ax.grid(axis="y", alpha=0.22)
    axes[0].set_ylabel("Error absoluto medio (µg/m³)")
    axes[0].legend()
    figure.suptitle("PM2.5 en Lima · Gemma 3 1B frente a la CNN")
    figure.savefig(ROOT / "reports/models/gemma-1b-archivos.png", dpi=160)


if __name__ == "__main__":
    main()
