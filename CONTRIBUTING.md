# Contribute to Neblima

Use your own checkout, branch, environment, and credentials. If you're
joining the team, start with the [team onboarding guide
(Spanish)](docs/team-onboarding.md) and verify the owner and acceptance
criteria in the relevant issue.

## Prepare and check your change

From the repository root, install the pinned environment and run the checks
below. The [setup guide](docs/getting-started.md) lists prerequisites and
shows how to replay the data pipeline.

```bash
uv python install
make setup
make init
make doctor
UV_OFFLINE=true make check
make build
make audit
```

Setup and package builds can download tools. `make check` runs offline after
setup. `make audit` queries a vulnerability advisory service. Continuous
integration (CI) checks Python 3.11 and 3.13.13, runs the isolated TimeF
test suite on Python 3.13.13, and audits dependencies independently.
[Quality requirements (Spanish)](CONSTRAINTS.md)

Write tests before changing behavior. Open a focused pull request (PR), link
the issue, and record the commands you ran, their results, and any blockers.
Request review from Keneth Arias for shared data contracts, source decisions,
and evaluation changes. Review the [repository instructions](AGENTS.md) and
[current work plan (Spanish)](tasks/plan.md).

## Write documentation

Use English for the README and maintained public guides. Keep the Spanish
landing page available for local readers. Use Peruvian Spanish for team
coordination, issues, and PRs, and preserve source communications in their
original language. Keep identifiers, paths, field names, and commands as
implemented. Follow TimeNet's requirements for upstream contributions.
[Language decision](docs/decisions/002-espanol-peru.md)

## Work with sources and licenses

Review the [source catalog](docs/sources.md) and keep unknown units,
timestamps, coordinates, or rights unknown. Preserve source bytes and
document the provenance of derived records. Use chronological splits for
forecast evaluation and keep future information outside model inputs.
Keep bulk data, credentials, and model weights out of Git.

Follow the publication and download authorizations in the work plan.
Contributions to Neblima use AGPL-3.0-only. Data retain their source terms.
A contribution to TimeNet under MIT requires separate authorship and
permission review. [Data attribution](DATA_ATTRIBUTION.md) ·
[Licensing decision (Spanish)](docs/decisions/003-licencia-agpl-v3.md)
