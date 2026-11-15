# AirAware Perú

Reproducible air-quality time-series dataset engineering for Lima, Callao and Peru, participating in
the [TimeNet hackathon](https://challenge.timenet.ai/). The first use case is measured PM2.5 forecasting.
Keneth Arias (`@keneth-arias`) is the main data and platform lead.

## Start locally

Install Git, Make and [uv](https://docs.astral.sh/uv/getting-started/installation/), then run from this
repository root:

```bash
uv python install
make setup
make init
make doctor
make check
```

The default Python is 3.13.13. Dependencies are locked in `uv.lock`. Setup needs network access for
tooling; catalog validation and tests work offline after setup. No paid service or provider API key
is needed for current commands. [Contributor setup](CONTRIBUTING.md) includes build and audit checks.

```bash
uv run --locked airaware catalog validate
uv run --locked airaware workspace init
uv run --locked airaware doctor
```

`AIRAWARE_DATA_DIR` selects another local artifact root. Environment files are not auto-loaded.
See the [lead handbook](docs/lead-handbook.md) and [service/access checklist](docs/services.md).

## Current capabilities
The foundation validates 37 candidate source resources, initializes local storage layers, and checks
the local environment. Every source remains unverified. Acquisition, profiling, normalization,
TimeF export and training are future tasks; no environmental observations have been collected.

## Layout and next work

- `configs/sources.yaml`: active source inventory; [schema and status rules](docs/sources.md).
- `src/airaware/`: catalog validation and CLI; `tests/`: offline behavior checks.
- `data/`: raw, staging, normalized, curated, benchmarks and timef artifacts, excluded from Git.
- `metadata/*.csv`: original internal column templates, not TimeNet exports.
- `docs/`: methodology, decisions, lead onboarding and verified upstream research.
- `.github/`: CI, CODEOWNERS, source-review issue form and PR template.

Start with source verification in [#4](https://github.com/keneth-arias/airaware/issues/4) and
[#5](https://github.com/keneth-arias/airaware/issues/5), then implement acquisition before downloading.
The [implementation plan](tasks/plan.md), [GitHub Project](https://github.com/users/keneth-arias/projects/1)
and [issues](https://github.com/keneth-arias/airaware/issues) track delivery.
The [initial brief](docs/initial-plan.md) retains the complete scope; its proposed commands are not
implemented APIs. [Architecture](ARCHITECTURE.md) describes current and planned boundaries.

Never commit credentials or bulk data. Source licenses must be verified before redistribution;
a public repository does not grant rights to candidate datasets. The project's code license remains
a lead decision, and no dataset license is asserted by this foundation.
