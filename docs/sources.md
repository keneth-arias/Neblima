# Source catalog

[`configs/sources.yaml`](../configs/sources.yaml) is the current inventory.
[`airaware.catalog.Source`](../src/airaware/catalog.py) defines the schema.
Entries can represent datasets, dictionaries, or metadata. The legacy
`metadata/sources.csv` is a column template.

```bash
uv run --locked airaware catalog validate
```

The validator prints the current entry count and status breakdown. Keep
unknown fields null, empty, or `unknown` according to the schema. Record the
starting page in `catalog_url` and add `resource_urls` once a specific file
or application programming interface (API) is resolved. Keep credentials
out of URLs.

## Source review

Priorities run from official measurements (0), other observations or
aggregations (1), and meteorology (2), to atmospheric or satellite products
(3) and contextual data (4). Track coverage, resolution, units, methodology,
access, license, attribution, and redistribution per resource.

| Status | Evidence |
| --- | --- |
| `discovered` | Identified for review. |
| `verified` | Information confirmed and documented. |
| `downloaded` | File acquired and inspected. |
| `profiled` | Quality and coverage analyzed. |
| `integrated` | Included with documented measurement type and redistribution rights. |
| `blocked` | Blocker documented. |
| `duplicate` | Matching resource documented. |
| `excluded` | Exclusion rationale documented. |

Advanced statuses require an evidence timestamp with a time zone and notes.
The validator checks that evidence is recorded. A reviewer confirms what
it establishes. [Dated access checks](../metadata/source-access.json) ·
[Web access protocol](web-access.md)

## Where the sources fit

The initial dataset uses historical Lima readings from Peru's National
Meteorology and Hydrology Service (SENAMHI). Later experiments use archived
OpenAQ and hourly SENAMHI targets. Peru's Agency for Environmental Assessment
and Enforcement (OEFA) provides candidate measurements whose rights and
compatibility vary by product. Weather, atmospheric reanalysis, and satellite
context each have their own availability and rights review.

| Source | Evidence |
| --- | --- |
| SENAMHI Lima historical monitoring | [Dataset card](dataset-cards/lima-pm25-forecast.md) and [source review (Spanish)](sources/senamhi.md). |
| OEFA measurement candidates | [Resource and coordinate review (Spanish)](sources/oefa.md). |
| OpenAQ | [External evaluation](evaluation.md#gemma-3-1b-and-the-cnn-on-external-archives) and [access and overlap review (Spanish)](sources/openaq.md). |
| Open-Meteo GFS archives | [Attribution and use](../DATA_ATTRIBUTION.md) and [weather source review (Spanish)](sources/weather.md). |
| Atmospheric and fire context | [CAMS reanalysis (Spanish)](sources/cams.md) and [NASA FIRMS (Spanish)](sources/firms.md). |

Follow the [inventory review (Spanish)](sources/inventory-review.md) for
the initial evidence and the [evaluation guide](evaluation.md) for the results
of specific sources and time periods.
