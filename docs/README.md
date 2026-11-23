# Neblima documentation

Neblima is an air quality research project for Lima, Peru. Start with the demo
to inspect a forecast, or use the local tools to follow a station reading
from its original source file to a scored prediction. TimeF is TimeNet's
time-series dataset format.

| If you want to… | Start here |
| --- | --- |
| Explore station readings and replay six-hour forecasts | [Demo guide](demo.md) |
| Install the tools, run checks, and replay the pipeline offline | [Getting started](getting-started.md) |
| Understand what each pipeline stage preserves and writes | [Architecture](../ARCHITECTURE.md) |
| Inspect coverage, split boundaries, and the expected units | [Lima PM2.5 dataset card](dataset-cards/lima-pm25-forecast.md) |
| Compare Qwen, Gemma, the convolutional model, and simple baselines | [Evaluation](evaluation.md) |
| Confirm source types, access, and rights | [Source catalog](sources.md) and [data attribution](../DATA_ATTRIBUTION.md) |
| Work on code or documentation | [Contributing](../CONTRIBUTING.md) |

## Technical reference

Use these guides when you need to run a stage or audit a decision.

- Data intake and preparation. [Web access](web-access.md),
  [acquisition reference](acquisition.md),
  [observation contract](methodology/observation-contract.md),
  [profiling methods](profiling.md), [source comparison](comparison.md),
  [dataset design](dataset-plan.md), and
  [normalization report (Spanish)](../reports/senamhi-normalization.md).
- TimeF exports. [TimeNet guide](timef.md), [pinned API review
  (Spanish)](timenet-integration.md), and [export scripts and
  examples](../tools/timenet-smoke/README.md).
- Forecast experiments. [Synthetic temporal questions](dataset-cards/temporal-qa-sintetico.md),
  [training probe](model-readiness.md),
  [historical model selection
  (Spanish)](../reports/models/seleccion-concentracion-lima.md), [episode labels
  (Spanish)](methodology/event-labels.md), and [station holdout protocol
  (Spanish)](../reports/baselines/holdout-method.md).
- Demo operations. [Refresh pipeline](../tools/web-refresh/README.md),
  [presentation materials (Spanish)](showcase/README.md), and [challenge
  evidence (Spanish)](hackathon.md).
- Team operations. [Onboarding (Spanish)](team-onboarding.md), [responsibilities
  (Spanish)](team-work-allocation.md), [decision records (Spanish)](decisions/),
  and [work plan (Spanish)](../tasks/plan.md).

[Entrada en español](../README.es.md)
