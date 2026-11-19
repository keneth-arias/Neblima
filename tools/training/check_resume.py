"""Comparar una recuperación FSDP2 con el entrenamiento continuo."""

import argparse
import json
import re
from pathlib import Path

import torch
import torch.distributed.checkpoint as dcp


def events(path):
    for line in path.read_text().splitlines():
        match = re.search(r'(\{"(?:step|restored_step)".+\})$', line)
        if match:
            yield json.loads(match[1])


def weights(generation, name):
    reader = dcp.FileSystemReader(generation / "dcp")
    info = reader.read_metadata().state_dict_metadata[name]
    value = torch.empty(info.size, dtype=info.properties.dtype)
    dcp.load({name: value}, storage_reader=reader, no_dist=True)
    return value


def compare(continuous_log, resumed_log, continuous_final, resumed_final):
    continuous = list(events(continuous_log))
    resumed = list(events(resumed_log))
    restored = next(row["restored_step"] for row in resumed if "restored_step" in row)
    expected = {
        row["step"]: row for row in continuous if "window_ids" in row and row["step"] > restored
    }
    actual = {row["step"]: row for row in resumed if "window_ids" in row}
    if not expected or expected.keys() != actual.keys():
        raise ValueError("Los pasos posteriores a la reanudación difieren")
    for step in expected:
        a, b = expected[step], actual[step]
        if a["window_ids"] != b["window_ids"] or a["learning_rate_next"] != b["learning_rate_next"]:
            raise ValueError(
                f"El orden de ventanas o la tasa de aprendizaje difiere en el paso {step}"
            )
        torch.testing.assert_close(a["loss"], b["loss"], atol=1e-6, rtol=1e-6)
    differences = {}
    for name in ("model.head.weight", "model.decoder.layers.0.mlp.down_proj.weight"):
        a, b = (weights(path, name) for path in (continuous_final, resumed_final))
        torch.testing.assert_close(a, b, atol=1e-7, rtol=1e-6)
        differences[name] = (a - b).abs().max().item()
    mae = [
        next(row["mae"] for row in rows if row.get("step") == max(actual) and "mae" in row)
        for rows in (continuous, resumed)
    ]
    torch.testing.assert_close(*mae, atol=1e-6, rtol=1e-6)
    return {
        "restored_step": restored,
        "matched_steps": sorted(actual),
        "max_absolute_parameter_difference": differences,
        "continuous_validation_mae": mae[0],
        "resumed_validation_mae": mae[1],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("continuous_log", "resumed_log", "continuous_final", "resumed_final"):
        parser.add_argument(name, type=Path)
    print(json.dumps(compare(**vars(parser.parse_args())), indent=2))
