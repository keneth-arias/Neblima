# Data and platform lead handbook

Keneth Arias (`@keneth-arias`) is the main data and platform lead. CODEOWNERS routes repository
review requests to you. This role owns source selection, canonical contracts, scientific data
quality, provenance, split integrity, developer tooling, CI and release readiness. Teammate roles
remain unassigned until the team agrees on them.

## Your first working session
Run from the repository root:

```bash
make setup
make init
make doctor
make check
```

`doctor` checks Python, Git, uv, timezone support, catalog validity and storage readiness without
network requests or writes. It reports optional credential presence as booleans, never values.
A healthy result means the local foundation is ready; it does not verify provider access,
GitHub authentication, backup health, available data, or dataset rights.

Review `configs/sources.yaml`. Pick `senamhi-lima` for issue #4 and `oefa-national` for issue #5.
Resolve actual download resources and dictionaries, verify license evidence, then record a dated
source review using the GitHub issue form. Leave unknown coverage and units as null. Keep blocked
sources with a reason. `verified`, `downloaded` and later statuses require timestamped evidence;
`integrated` additionally requires documented redistribution permission and a known data category.

After verification, implement the tested downloader in #6–#7 before acquisition #8–#9. First inspect
real artifacts, then produce measured profiles and comparison (#10–#11). Select the benchmark from
that evidence; four stations, 24 months and 72/24-hour windows remain provisional targets.

## Services and secrets
Use the [service checklist](services.md). No API key is needed for current commands. The `.env` file
is ignored and is not auto-loaded. If needed, set variables in your shell, for example:

```bash
export AIRAWARE_DATA_DIR="$HOME/airaware-data"
make init
make doctor
```

Do not put provider keys into catalog URLs, issue comments, notebook outputs or Git. OpenAQ is a
later task; acquire your own key through its official account flow when that integration starts.
Local artifacts are not committed or automatically backed up. Choose and test a backup procedure
before relying on them. Keep original raw bytes immutable and derived artifacts rebuildable.

## Decisions and handoffs

- You decide source inclusion after license and measurement review; record major decisions in ADRs.
- Contributors include issue scope, exact verification results and known unknowns in each PR.
- Review changes to schemas, source precedence, quality filters and split dates before downstream use.
- Freeze test boundaries before model iteration; prohibit preprocessing fitted to held-out data.
- Before a release, inspect source licenses, provenance, quality reports, leakage tests, SDK round
  trips and baseline metrics. Publish only after the authorization required by the plan.
- Maintain the GitHub Project and issue blockers as the live status; the plan is an ordered index.

## Initial delivery evidence
The foundation adds a locked local environment, a validated discovery catalog, three offline CLI
commands, tests and CI configuration. It does not implement downloading, profiling, normalization,
TimeF export or model training. The integration note records source inspection separately from
runtime verification so you can assess readiness without assuming unfinished work is complete.
