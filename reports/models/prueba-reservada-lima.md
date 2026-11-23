# Six-hour PM2.5 forecasts for Lima

Given 24 hours of PM2.5 history, Qwen3.5-0.8B with low-rank adaptation (LoRA) achieved a **mean absolute error (MAE) of 4.994 µg/m³** on the chronological held-out test. Repeating the last reading yielded 6.446 µg/m³, and the convolutional neural network yielded 5.158 µg/m³. The reduction relative to persistence was **1.452 µg/m³ (22.52%)**. This comparison measures retrospective forecasts at SENAMHI monitoring stations in Lima. [Results by model, station, and horizon](../../metadata/qwen-heldout-lima.json).

## Chronological held-out test

The [November 19, 2026 selection](https://github.com/keneth-arias/Neblima/pull/95) fixed the models, baselines, and evaluation rule before the test windows were exported. We verified the TimeF manifest and checked that the test identifiers were disjoint from the training and validation identifiers. The 50,789 forecast origins span February 26, 2023 at 17:00 UTC through May 29, 2024 at 20:00 UTC, with gaps in the station records. Qwen and the convolutional network received the same 24 hourly values per window. We evaluated all five methods on the same six targets per origin.

| Model | Overall MAE (µg/m³) | Difference from persistence | High-concentration MAE (µg/m³) |
| --- | ---: | ---: | ---: |
| Direct Qwen with LoRA | **4.994** | **−1.452** | **18.371** |
| Temporal convolutional network | 5.158 | −1.288 | 18.434 |
| Persistence | 6.446 | 0.000 | 19.616 |
| Same hour on the previous day | 7.038 | +0.592 | 23.086 |
| Training mean by series and UTC hour | 8.269 | +1.823 | 34.144 |

All five models were evaluated on 304,734 window–hour pairs. Because the windows overlap, these pairs represent **51,319 distinct station-hours**. A target repeats when successive origins forecast the same reading. The differences are descriptive for this split and one training seed. The three baselines reproduced the test MAEs from [#25](../baselines/lima-pm25.md). A second evaluation using the same inference files reproduced the report and the hashes of all five paired files exactly.

Qwen reduced MAE relative to persistence at all seven provisional stations and at each of the six horizons. The reduction was 0.272 µg/m³ at one hour and 2.542 µg/m³ at six hours. By station, it ranged from 0.768 µg/m³ in San Borja to 2.603 µg/m³ in Carabayllo. The 95th percentile fixed during training identifies 10,574 high-concentration targets corresponding to 1,772 distinct station-hours. For those targets, the reduction was 1.244 µg/m³ (6.34%). Qwen's MAE remained high at 18.371 µg/m³.

## Team presentation material

![Test MAE by forecast hour and two validation examples with 24 hours of history, six observed readings, a persistence forecast, and a Qwen forecast.](lima-pm25-prueba.png)

In the **Carabayllo** example, both models start from the same history. Qwen anticipates part of the decline and lowers the window's MAE by 3.04 µg/m³. In **San Juan de Lurigancho**, Qwen forecasts a decline and misses the rise in the final hours. Persistence has a lower MAE by 2.03 µg/m³. Both examples were selected on validation data using a median-based rule before the held-out test. [Identifiers, forecast origins, and selection rule](validacion-cabezales-qwen.md).

The use case is to anticipate hourly changes at these stations when 24 consecutive readings are available. The evaluation includes only complete windows. We retained the accepted inferred unit. The placement of readings within their reporting intervals, individual reading quality, and historical real-time availability still await institutional confirmation. Using these results for live alerts would require checking that availability and evaluating subsequent readings. Data come from Peru's National Meteorology and Hydrology Service (SENAMHI) under ODC-BY-1.0. The Cuybernautas team produced the derived data and forecasts. [Attribution and license](../../DATA_ATTRIBUTION.md) · [Source policy](../../docs/decisions/005-senamhi-operating-policy.md).

## Resources and traceability

Qwen inference for the held-out test ran once on an RTX 5070 Ti in FP32 with a batch size of 16. SkyPilot recorded 221.71 seconds from job start to completion. The convolutional network ran on CPU. Each forecast file preserves the SHA-256 of its checkpoint. In the final LoRA state, we verified finite, nonzero B weights and optimizer second moments for all 24 adapted full-attention projections and all 90 recurrent projections. This check confirms that both projection families received updates. The run used the PyTorch reference kernel. An [optional accelerated-kernel benchmark](https://github.com/keneth-arias/Neblima/issues/96) remains a separate experiment.

## Reproduce the evaluation

The evaluation used the TimeF manifest from [#22](../../tasks/issue-22-plan.md), the [frozen selection](../../configs/training/lima-pm25-finalistas-v1.yaml), and the files from [#25](../baselines/lima-pm25.md). After preparing the local data and weights, create a new directory. The export retains the targets for scoring. The inference input contains only the identifier and 24-hour history.

```bash
inputs=data/benchmarks/qwen-pm25-v1
out="$inputs/holdout-reproduccion"
mkdir "$out"
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python \
  tools/timenet-smoke/export_qwen_windows.py data/timef/airaware/lima-pm25-forecast/0.1.0 \
  "$out/test.npz" --split test > "$out/export.json"
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python - "$out" <<'PY'
from pathlib import Path
import sys
import numpy as np

out = Path(sys.argv[1])
with np.load(out / "test.npz", allow_pickle=False) as data, (out / "history.npz").open("xb") as f:
    np.savez(f, window_id=data["window_id"], history=data["history"])
PY
```

In the convolutional network environment, run `python tools/training/predict_cnn.py "$inputs/fits/cnn/model.pt" "$out/history.npz" "$out/cnn.npz" --batch 16`. For Qwen, use the image and weights from the finalists manifest, mount the weights at `/inputs/qwen/weights`, and mount the retained volume at `/checkpoints`. From the directory containing `history.npz`, run the following command and copy the output to `$out/qwen.npz`.

```bash
HF_HUB_OFFLINE=1 PYTHONPATH=/opt/forecast/src /opt/conda/bin/python -m opentslm.forecast_inference \
  --weights /inputs/qwen/weights --checkpoint /checkpoints/lima-fit-v1-direct-lora/step-00014837 \
  --data history.npz --output qwen.npz --batch 16
```

The comparison checks the revision embedded in each prediction file against the selection, verifies the manifest from #25, and joins records by identifier and hour. It also verifies the station, UTC origin, observed value, and last value in the history. The paired files for each model stay in local storage. The figure uses the aggregate report and the two validation windows fixed before the test.

```bash
UV_OFFLINE=true uv run --project tools/timenet-smoke --locked python \
  tools/timenet-smoke/evaluate_finalists.py "$out" data/benchmarks/lima-pm25-h24-f6-baselines \
  configs/training/lima-pm25-finalistas-v1.yaml "$out/resultado"
uv run --script tools/training/plot_forecast_results.py "$inputs" "$out/resultado/report.json" "$out/figura.png"
```

The first installation of the plotting environment may require network access. The Qwen base weights use revision `2fc06364715b967f1860aea9cf38778875588b17`. Restoring LoRA requires the base weights and the final state pinned in the selection. See the [training procedure](../../docs/qwen-cluster-runbook.md) and [validation checksums](../../metadata/qwen-validation-lora.json).
