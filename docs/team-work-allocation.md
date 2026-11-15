# Team ownership and work queues

Allocation on 2026-11-15: 18 of 35 open implementation issues are reserved for teammates using owner labels and issue handoffs.
Native GitHub assignees are pending invitation acceptance; Keneth explicitly chose to keep these
planned ownership queues until teammates can accept. This is an
ownership queue, not 18 tasks to run at once. Live ownership labels, assignments and acceptance criteria are in GitHub;
existing dependencies are unchanged. Keep one active issue per person, and split large issues into
small PRs rather than marking partially complete issues done.

| Owner | Role | Issue queue |
| --- | --- | --- |
| Keneth / keneth-arias | Main data and platform lead; shared interfaces, scientific decisions, CI, leakage and releases | #1, #2, #3, #4, #6, #7, #11, #12, #14, #19, #20, #21, #22, #23, #27, #28, #32 |
| Cristopher / qriqs | Full-time contributor; source research and bounded, tested implementation | #5, #8, #9, #10, #13, #15, #16, #17, #18, #25, #26, #30, #31, #33, #34, #35 |
| Jordan / J0r-PS | Part-time contributor; guided documentation and showcase preparation | #24, #29 |

## Start without blocking the engineering path

- Cristopher starts with #5: investigate OEFA links/dictionaries and record evidence/unknowns in
  docs/sources/oefa.md. No bulk download or coordinate guesses. Final catalog edits wait for #3;
  Keneth reviews licensing and CRS interpretation. Weather/OpenAQ research (#16/#31) is an alternative
  if OEFA is inaccessible; acquisition/integration still waits for the listed dependencies.
- Jordan starts with #29: draft the showcase outline and submission-link checklist with explicit
  placeholders. No metrics or public posting are needed to make this first PR. The final showcase
  still waits for #24/#28. #24 can begin later with a dataset-card template; Keneth supplies verified
  scientific/license facts and connector code, and retains publication decisions.
- Keneth clears #1–#3/foundation review and #4, then owns the downloader contract (#6/#7), canonical
  contracts, scientific source precedence and split/leakage enforcement. Teammates implement against
  these contracts instead of independently redesigning them.

Research and documentation can start before their final completion dependencies are satisfied.
Implementation that consumes an unfinished interface must wait or use an agreed fixture contract.
For example, Cristopher can draft profiling tests with explicitly synthetic fixtures, but cannot
report real coverage before acquiring actual artifacts. No assignment is permission to bypass a
source, budget, scientific-validity, leakage or publication gate.

## Handoff rules

Each reassigned issue contains a first small deliverable and a dependency/review gate. Work in
separate source-specific documents and modules; avoid simultaneous wholesale edits to
configs/sources.yaml, shared schemas or CLI contracts. Submit the evidence/document first if the
shared file is under review, then Keneth coordinates its catalog integration.

When blocked, record the concrete missing input and next action on the issue, then choose independent
research/documentation. Do not bypass another owner's module to get unstuck. Optional weather,
national, atmospheric and QA queues do not delay the first pollution-only benchmark.

Keneth reviews shared schema, units, CRS, licensing, missingness and leakage changes. Jordan's first
PRs are documentation-only, with no fabricated results, code-generation responsibility, or external
posting. Queue ownership does not impose a deadline or increase the agreed availability.
