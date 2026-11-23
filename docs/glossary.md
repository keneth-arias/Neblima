# Glossary

These terms describe Neblima's data and forecasting workflow.

| Term | Meaning |
| --- | --- |
| PM2.5 | Fine particulate matter with an aerodynamic diameter of 2.5 micrometers or less. |
| Time series | Values ordered by time for a station, pollutant, or other signal. |
| Sampling frequency | How often a measurement is recorded. The averaging period describes the interval that a reading summarizes. |
| History | The input readings available through a forecast origin. Neblima's main benchmark uses 24 hourly values. |
| Forecast origin | The last hour in the input history. |
| Horizon | The lead time to a predicted value. Neblima's main benchmark scores +1 h through +6 h. |
| Target | The observed value used to score a prediction. |
| Persistence | A baseline that predicts the last observed reading at every horizon. |
| Mean absolute error (MAE) | The average absolute difference between predictions and observations, in the same unit as the target. |
| Train, validation, and test | Separate data used to fit a model, select a configuration, and score the final result, respectively. |
| Leakage | Using information that would be unavailable at forecast time or exposing reserved test information during fitting or selection. |
| Purge | Excluding windows whose full history and targets cross a split boundary. |
| Provenance | The evidence connecting an output to its source files, records, and transformations. |
| Missing-value mask | An indicator of which values are present. A measured zero is present. |
| TimeF | TimeNet's time-series dataset format. |
| Coordinate reference system (CRS) | The system that gives coordinates their geographic meaning. |

A weather observation recorded after a forecast origin leaks future
information if used as input. A weather forecast issued before that
origin can be eligible when its availability is documented.
[Architecture](../ARCHITECTURE.md)
