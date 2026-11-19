"""Comprobar que la red convolucional conserva el orden y la escala al restaurarla."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from compare_cnn import predict_from_checkpoint


def test_checkpoint_predictions_match_validation_rows_and_targets_are_optional(tmp_path):
    rng = np.random.default_rng(12)
    for name, n in [("train", 12), ("validation", 5)]:
        history = rng.normal(size=(n, 24)).astype("float32")
        history[0] = 0
        np.savez(
            tmp_path / f"{name}.npz",
            window_id=[f"{name}-{i}" for i in range(n)],
            history=history,
            targets=rng.normal(size=(n, 6)).astype("float32"),
        )
    train, valid = (tmp_path / f"{s}.npz" for s in ("train", "validation"))
    result = tmp_path / "resultado"
    command = [
        sys.executable,
        str(Path(__file__).with_name("compare_cnn.py")),
        str(train),
        str(valid),
        "--steps",
        "3",
        "--batch",
        "4",
        "--seed",
        "27",
        "--output",
        str(result),
    ]
    metrics = json.loads(subprocess.check_output(command, text=True).splitlines()[-1])
    with np.load(valid) as windows, np.load(result / "validation.npz") as rows:
        np.testing.assert_array_equal(rows["window_id"], windows["window_id"])
        np.testing.assert_array_equal(rows["forecast_hour"], np.arange(1, 7))
        np.testing.assert_allclose(
            np.abs(rows["predicted"] - windows["targets"]).mean(), metrics["mae"]
        )
        np.savez(
            tmp_path / "history.npz", window_id=windows["window_id"], history=windows["history"]
        )
        expected = rows["predicted"].copy()
    out = tmp_path / "predictions.npz"
    predict_from_checkpoint(result / "model.pt", tmp_path / "history.npz", out, 4)
    with np.load(out) as restored:
        np.testing.assert_allclose(restored["predicted"], expected, rtol=1e-6, atol=1e-6)
    with pytest.raises(FileExistsError):
        predict_from_checkpoint(result / "model.pt", valid, out, 4)
