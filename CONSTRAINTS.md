# Foundation quality contract

Established 2026-11-15 from the project brief and local-first setup scope.
Owner: @keneth-arias. This is the initial floor; further coverage/performance budgets
remain a lead decision after real pipeline measurements.

| Check | Gate | Command |
| --- | --- | --- |
| Lockfile | Current project metadata resolves without lock changes | `uv lock --check` |
| Formatting and lint | No configured findings | `uv run --locked ruff format --check src tests` and `uv run --locked ruff check src tests` |
| Types | No type errors against Python 3.11 floor | `uv run --locked ty check src tests` |
| Source catalog | Valid schema, unique IDs, evidence for progress | `uv run --locked airaware catalog validate` |
| Behavior | All offline tests pass | `uv run --locked pytest` |
| Packaging | Source distribution and wheel build | `make build` |
| Dependency advisories | No known vulnerabilities in installed locked environment | `make audit` (network required) |

`make check` runs the first five rows locally and in CI. Dependency audit includes dev tools;
the editable local package is skipped by the advisory service because it is unpublished.
No numerical coverage target is asserted yet. Branch protection is separate from having a CI file;
see the service checklist for the active state.

Review-enforced floor: no secrets, suppression comments, unfinished stubs, skipped/deleted tests
without a documented reason, or weakened checks. These review rules are not represented as a
complete automatic scanner. Do not edit this contract to bypass a failing change.
