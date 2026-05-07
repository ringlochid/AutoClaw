# AutoClaw

Last verified: 2026-05-07

AutoClaw is a controlled agent runtime for multi-step work that must stay auditable, replayable, and operationally recoverable.

This root README is a front-door router only. Canonical implementation, redesign, and execution truth lives under `docs/`.

## Start here

- Current shipped behavior: [docs/current/README.md](docs/current/README.md)
- Target redesign contract: [docs/redesign/README.md](docs/redesign/README.md)
- Redesign landing and phase execution: [docs/execution/README.md](docs/execution/README.md)
- Docs map and reading guide: [docs/README.md](docs/README.md)
- Coding-agent policy: [AGENTS.md](AGENTS.md)
- Coding standards: [STYLE.md](STYLE.md)

## Repo shape

- `apps/api/` - backend API, runtime, DB, CLI, and tests
- `definitions/` - workflow and definition content used by owning phases
- `docs/` - current behavior, redesign contract, and execution canon
- `scripts/` - repo tooling, including docs validation under `scripts/docs/`
- `examples/` - example workflows and supporting artifacts

## Common verification lanes

- Local backend suite: `./.venv/bin/pytest -q apps/api/tests`
- Docker/Postgres verification: `make test-api-db`
- Docs freeze validation: `./.venv/bin/python scripts/docs/docs_freeze_validate.py`

## Surface rule

Use this page for fast routing only.

Do not treat it as the authoritative source for detailed runtime behavior, redesign contracts, or phase-closeout status.
