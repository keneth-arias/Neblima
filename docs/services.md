# Service and access checklist

Initial choice: local storage plus GitHub Actions; no paid cloud services.
Checked 2026-11-15. Access states can change; recheck before relying on them.

| Tool/service | Current state | Lead action |
| --- | --- | --- |
| Git + GitHub CLI | Installed; authenticated as keneth-arias in this workspace | Teammates authenticate their own accounts with `gh auth login`; never share tokens |
| uv | Installed 0.11.20 | Use official [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) on other machines |
| Python | Local default installed: 3.13.13, pinned in .python-version | `uv python install`, then `make setup` |
| GitHub repository | Public, keneth-arias/airaware | Keep only code, docs and permitted small fixtures in Git |
| GitHub Project | Linked backlog with 35 implementation issues | Own priorities and unblock source decisions |
| GitHub Actions | First foundation run passed Python 3.11, Python 3.13.13 and dependency audit | Keep all three checks green |
| Local storage | Layer directories initialized under data/ | Use AIRAWARE_DATA_DIR for another disk; check free space before real downloads |
| Data backup | Not configured | Choose and verify backup/artifact sharing before irreplaceable collection |
| SENAMHI/OEFA | Candidate links inventoried; access/rights not verified | Work through #4/#5; record real resources, terms and blockers |
| OpenAQ | Optional for #31; no credential required or configured now | Follow [official API-key guide](https://docs.openaq.org/using-the-api/api-key) when needed |
| TimeNet | Upstream source inspected and revision recorded; SDK not installed | Install a pinned isolated integration environment when #21 starts |
| OpenTSLM | Remote revision recorded; model interfaces not yet inspected | Defer training setup until #27 after dataset gates pass |
| Hackathon | Submission checklist documented | Each participant registers; account/submission completion is not verified here |

Main branch protection requires up-to-date passing `quality (3.11)`, `quality (3.13.13)` and
`audit` checks. Force pushes and branch deletion are blocked. Admin enforcement is off so the owner
retains an emergency override. Mandatory review approval is not configured. GitHub CODEOWNERS
requests reviews; it does not itself enforce approval. Repository collaborator roles and personal Project roles are distinct. J0r-PS has Project
admin access; personal-repo collaborators have write access. Do not assume pending invitations were
accepted. No account creation or paid subscription is needed to run the current foundation.

Official tooling references used for setup:
- [uv GitHub Actions integration](https://docs.astral.sh/uv/guides/integration/github/)
- [uv build backend](https://docs.astral.sh/uv/concepts/build-backend/)
- [Pydantic model validation](https://docs.pydantic.dev/latest/concepts/models/)
- [Typer CLI testing](https://typer.tiangolo.com/tutorial/testing/)
