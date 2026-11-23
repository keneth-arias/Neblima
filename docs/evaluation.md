# Forecast evaluation

Neblima evaluates forecasts that take 24 consecutive hourly readings from a
station and predict the next six hourly concentrations. Each comparison below
uses paired targets within its own evaluation set. Reported mean absolute
error (MAE) is in micrograms per cubic meter (µg/m³). Lower is better.

## Historical Lima PM2.5 test

The seven-station dataset from Peru's National Meteorology and Hydrology
Service (SENAMHI) uses fixed chronological train, validation, and test splits. The models and scoring rules were fixed before exporting
the test targets. All five methods scored the same 50,789 windows and
304,734 window-hour pairs, representing 51,319 distinct station-hours.

| Method | Overall MAE | High-concentration MAE |
| --- | ---: | ---: |
| Qwen3.5-0.8B with low-rank adaptation (LoRA) | **4.994** | **18.371** |
| Temporal convolutional neural network (CNN) | 5.158 | 18.434 |
| Persistence (repeat the last reading) | 6.446 | 19.616 |
| Same hour of the previous day | 7.038 | 23.086 |
| Training mean by series and UTC hour | 8.269 | 34.144 |

Qwen's overall MAE was **22.52% lower** than persistence. For high
concentrations, defined by the 95th percentile fixed during training, the
reduction was **6.34%**, with an MAE of 18.371 µg/m³. The results describe
one held-out split and one training seed. [Held-out test report
(Spanish)](../reports/models/prueba-reservada-lima.md) ·
[Metrics JSON](../metadata/qwen-heldout-lima.json) ·
[Baseline methods (Spanish)](../reports/baselines/lima-pm25.md)

The demo illustrates two windows selected from validation before the test.
Qwen anticipated part of a drop in Carabayllo and reduced window MAE by
3.04 µg/m³. In San Juan de Lurigancho, Qwen missed a late rise and
persistence had 2.03 µg/m³ lower MAE. [Demo results](https://neblima.orbitly.lat/#landing)

## Gemma 3 1B and the CNN on external archives

The Gemma model uses OpenTSLM and a frozen correction for concentration
peaks. Each row compares it with the CNN on exactly the same source-specific
PM2.5 targets.

| Archive | Window-hour pairs | Overall MAE, Gemma / CNN | High-concentration MAE, Gemma / CNN |
| --- | ---: | ---: | ---: |
| Frozen OpenAQ | 513,228 | 6.041 / **6.001** | **15.855** / 16.008 |
| Archived hourly SENAMHI | 616,608 | 5.829 / **5.769** | **15.817** / 15.983 |

Gemma lowered error in high-concentration hours. The CNN had lower overall
error on both archives. Both archives met the prespecified retrospective
criteria, which allowed a small increase in overall MAE and required a
positive high-concentration improvement under paired block resampling.
A later SENAMHI replay contained 211 complete windows and only one weekly
block with high-concentration targets, below the required four. A later
OpenAQ pull produced no new complete windows. The replay did not qualify
Gemma for promotion under that protocol. [Gemma report
(Spanish)](../reports/models/validacion-gemma.md) ·
[Benchmark and per-horizon metrics](../metadata/resultados-gemma-1b-20261123/benchmark.json)

## What PM10 history adds

Both variants predicted PM2.5 and PM10. One received only PM2.5 history,
and the other received both histories. The comparison holds the set of
targets fixed across the two variants.

| Archive | PM10 MAE, PM2.5 history only | PM10 MAE, both histories | PM2.5 MAE reduction |
| --- | ---: | ---: | ---: |
| OpenAQ | 21.460 | 11.117 | 0.059 |
| Hourly SENAMHI | 20.979 | 10.922 | 0.045 |

Adding PM10 history nearly halved PM10 MAE. The average benefit for PM2.5
was much smaller and varied by station and horizon. Requiring complete
histories for both pollutants reduced coverage. [External PM2.5 and PM10
evaluation (Spanish)](../reports/models/prueba-externa-pm25-pm10.md)

## Scope of the results

The studies measure retrospective performance on complete windows. The
historical dataset uses provisional station identities and an inferred
concentration unit accepted by the project. Individual reading quality,
interval placement, and historical publication latency remain unconfirmed.
These limits matter for interpreting errors at high concentrations or
considering operational or regulatory uses. [Dataset
card](dataset-cards/lima-pm25-forecast.md) ·
[Episode-label evidence (Spanish)](methodology/event-labels.md)
