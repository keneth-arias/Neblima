# Source discovery inventory

`configs/sources.yaml` is the active inventory; `airaware.catalog.Source` is its validated schema.
Use `uv run --locked airaware catalog validate`. Missing optional fields use explicit unknown defaults
(null, empty lists or `unknown`), not inferred facts. `metadata/sources.csv` is an earlier template.
The 37 candidate resource links are copied from the original brief, including distinct data,
dictionary and metadata resources. They do not constitute 37 independent measurement datasets.

Priority 0 is official physical observations; 1 additional/aggregated observations; 2 meteorology;
3 atmospheric/satellite products; 4 contextual research. Data category stays `unknown` until verified.
Catalog URL is the original lead; fill resource_urls only after resolving actual files or endpoints.

Each record supports publisher, description, geographic/historical coverage, temporal/spatial
resolution, variables/units/methodology, data category, formats/size, authentication/rate limits,
update frequency, license/attribution/redistribution, limitations, priority, status and timestamped
notes. See the Source model for exact fields. Keep credentials in environment variables, never URLs.

Status vocabulary: discovered, verified, downloaded, profiled, integrated, blocked, duplicate, excluded.
Progressed statuses require a timezone-aware verification timestamp and evidence notes; blocked,
duplicate and excluded require explanations. The validator checks evidence is present, not whether
it is true: source review and actual artifact inspection remain the lead's responsibility.

Contextual leads without identified dataset URLs remain research items: traffic/mobility, industrial
emissions, electricity/industrial activity, construction/dust, holidays, and land use/elevation/urban
morphology. Do not invent endpoints to turn those topics into datasets. NASA FIRMS is already listed
as a candidate for wildfire context. Review availability and relevance before adding any source.
