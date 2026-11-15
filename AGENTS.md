# AirAware contributor instructions

Read `CONSTRAINTS.md` before writing code. Do not weaken it to make a change pass.
Read `tasks/plan.md` and the issue being implemented; preserve incomplete work.

## Ownership and scope
Keneth Arias (`@keneth-arias`) is the main data and platform lead. See
`docs/lead-handbook.md` for decisions, handoffs and the first working session.
Read `docs/team-work-allocation.md` for owners and handoff boundaries. Each developer uses their own
checkout/environment; never switch branches in another developer's folder.
Use English for code/docs; preserve original Spanish source artifacts.

## Commands
Run from the repository root using uv: `make setup`, `make init`, `make check`,
`make build`, `make audit`, `make doctor`. Python development uses `.python-version`;
CI checks Python 3.11 and 3.13.13. Tests and catalog validation must work offline after sync.

## Boundaries
- `configs/sources.yaml` and `airaware.catalog` own discovery metadata and its schema.
- `metadata/*.csv` are legacy column templates, not an authoritative source inventory.
- Keep network acquisition separate from deterministic conversion.
- Use immutable raw files and trace every derived observation to source artifacts.
- Never invent units, timestamps, coordinates, missing measurements or license grants.
- Do not use random row splits for temporal benchmarks or future observations as features.
- Do not commit bulk data, credentials, notebook outputs, caches or checkpoints.
- Verify pinned TimeNet code before using its interfaces; see `configs/upstream.lock.json`.
- Add dependencies only for implemented behavior. Document architectural decisions in `docs/decisions/`.
- Bulk publication, external dataset PRs, paid services and expensive/unbounded downloads retain
  the authorization gates recorded in the plan. Initial setup is local storage plus GitHub Actions.

## Delivery
Use focused branches, tests before new logic, conventional commits and reviewable PRs.
Run `make check`, `make build` and `make audit` before handoff. Report exact results and
blockers. Never skip tests, suppress findings or claim unavailable data was inspected.
