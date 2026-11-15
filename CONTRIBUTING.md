# Contributing

Start with [the lead handbook](docs/lead-handbook.md), [the plan](tasks/plan.md), and your GitHub issue.
Development is supported on Linux/macOS; Windows contributors should use WSL for Make targets.
Install Git, Make, uv >=0.11.20 and optionally the GitHub CLI through their official installation guides.
Python is managed by uv; `.python-version` pins the default interpreter.

```bash
uv python install
make setup
make init
make doctor
make check
make build
make audit
```

Setup and build may download tooling. `make check` uses no live environmental data; after setup it
can run with `UV_OFFLINE=true`. The advisory audit deliberately queries an external service.
CI repeats quality checks on Python 3.11 and 3.13.13 and runs the dependency audit separately.

Create a focused branch, reference the issue in the PR, include verification evidence, and request
review from the data and platform lead. CODEOWNERS requests a review; it does not itself enforce one.
A contributor cannot approve their own PR. Use the PR template and leave sources at `discovered`
until evidence justifies a status change. Read `AGENTS.md` for data handling rules.

The CLI currently implements `catalog validate`, `workspace init` and `doctor`. Proposed download,
profile, normalization, training and TimeF commands in the initial brief are not implemented.
Do not publish dataset artifacts or open an upstream dataset PR without the authorization recorded
in the plan. The code license is still a lead decision; no dataset license is implied by a public repo.
