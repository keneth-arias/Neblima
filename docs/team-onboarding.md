# Team local setup

All three developers use the same tracked tools/configuration and separate checkouts. On the shared
machine, use your own Linux account and checkout; do not change branches in another person's folder.

| Developer | Linux user | GitHub | Checkout |
| --- | --- | --- | --- |
| Keneth | kymai | keneth-arias | /home/shared/github/keneth-arias/airaware |
| Cristopher | cristopher | qriqs | /home/cristopher/github/airaware |
| Jordan | jordan | J0r-PS | /home/jordan/github/airaware |

Cristopher and Jordan each have Python 3.13.13, their own .venv and uv cache, an ignored private .env,
and private local data storage in their checkout. Git, gh, Make and uv are installed system-wide.
Repository-local Git author identities use their GitHub noreply email addresses; pull is fast-forward
only and the first push automatically sets upstream. No GitHub credential was copied between users.

## First session

Log in as your own Linux user and run:

```bash
cd ~/github/airaware
make doctor
make check
```

For another computer, clone the public repository and follow CONTRIBUTING.md. As of setup, the
foundation is in PR #36 on `chore/platform-foundation`, and each prepared checkout uses that branch.
After it merges, switch to main and pull before starting new work:

```bash
git fetch origin
git switch main
git pull --ff-only
```

Before merge, create issue branches from `origin/chore/platform-foundation` and target that branch
for early review. After #36 merges, base new branches on `origin/main`. Keneth coordinates retargeting
any early PRs so the foundation diff is not reviewed twice.

Cristopher's suggested first branch is `docs/issue-5-oefa-review`; Jordan's is
`docs/issue-29-showcase-outline`. Create branches only when beginning the task:

```bash
git switch -c docs/issue-5-oefa-review
```

Jordan uses his own issue-29 branch name instead. Keep the first PR focused on the first deliverable
in the issue handoff; it need not finish the entire issue. Leave acceptance criteria unchecked until
there is evidence. One active issue per person is the initial work-in-progress limit.

## GitHub access still needs personal sign-in

Repository invitations to qriqs and J0r-PS are pending as of setup. Both must accept their invitation
through their own GitHub account before pushing or receiving native issue assignments. Until then,
owner labels and handoff sections reserve their issue queues. Both have been granted personal Project admin
access; repository access is collaborator/write because the repo belongs to a personal account.
Local gh is installed but neither teammate's local account is authenticated yet. Read-only public
cloning, local editing, tests and builds work already. Each developer must establish their own GitHub
login before pushing or creating PRs; never reuse Keneth's token or another developer's login.

## Shared configuration and private artifacts

Changes to pyproject.toml, uv.lock, configs, Makefile, AGENTS.md and CI travel through Git and PRs.
After pulling changes, use `make setup` to synchronize your own environment. The CLI does not load
.env automatically; export environment variables explicitly when needed. Default data is local to
your checkout. Do not move credentials, .venv, caches or raw data between developers as a setup step.
Publish source evidence and small permitted fixtures through PRs so others can reproduce your work.

Both prepared accounts passed doctor, 29 offline tests, formatting, lint, type/catalog checks, package
build and dependency audit on 2026-11-15. Provider access, actual datasets and their rights remain
unverified. See [work allocation](team-work-allocation.md) for the issue queues and handoff rules.
