# Data attribution

Neblima's code uses AGPL-3.0-only. The observations and archived forecasts
below retain their own terms.

## SENAMHI air quality observations

The source is Peru's National Meteorology and Hydrology Service (Servicio
Nacional de Meteorología e Hidrología del Perú, SENAMHI). The original dataset
is **Monitoreo de los contaminantes del aire en Lima Metropolitana**.
[Catalog and license notice](https://www.datosabiertos.gob.pe/dataset/monitoreo-de-los-contaminantes-del-aire-en-lima-metropolitana-servicio-nacional-de) ·
[Open Data Commons Attribution License 1.0 (ODC-BY-1.0)](https://opendatacommons.org/licenses/by/1-0/)

The selected original has SHA-256
`896ae8a106fb128460e81b3f58096f6b9c4d582ef28fffa46e5394c5875c40d4`.
The receipt records the acquisition date and original file, and the
normalization decision records the policy approved on November 17, 2026.
[Acquisition receipt](metadata/senamhi-lima-download.json) ·
[Normalization decision](metadata/senamhi-normalization-decision.json)

Neblima preserves the original and derives data with Coordinated Universal
Time (UTC) labels, accepted unit inferences, token classification,
duplicate checks, and aggregations. For each normalized release, describe
the actual changes, policy version, and generation date. Keep this notice,
the license link, the source credit, and applicable original notices with
redistributed data and derived data. Include accessible notices in apps and
attribute Neblima's processing and forecasts to Neblima. SENAMHI does not
endorse the project's results. This statement covers the identified source.

## Open-Meteo archived forecasts

Open-Meteo provides the Previous Model Runs application programming
interface (API). The upstream model is the Global Forecast System (GFS)
from the US National Centers for Environmental Prediction, part of the
National Oceanic and Atmospheric Administration. The model retains its own
terms. Open-Meteo states that its free noncommercial API uses
[CC BY 4.0](https://open-meteo.com/en/licence), which requires attribution.
[Previous Model Runs API](https://open-meteo.com/en/docs/previous-runs-api)

Neblima's alignment experiment uses only `temperature_2m_previous_day1`
from the pinned sample. Open-Meteo does not endorse the resulting analysis.
Neblima records redistribution status as `unknown` and keeps the values in
local storage. [Acquisition plan](configs/acquisition/weather-lima-sample-plan.json) ·
[Source receipts](metadata/weather-acquisition.json) ·
[Alignment evidence (Spanish)](reports/alignment/weather-gfs-previous-day1.md)

## Map and screenshots

The standalone Leaflet map and the dashboard use different map assets. Keep
the attribution visible in the map you reuse. The [demo guide](docs/demo.md#image-credits)
lists the public dashboard credits and the mark's source.
