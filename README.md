# AutoClaw

Last verified: 2026-05-03

AutoClaw is currently in a Phase 0.5 hard-reset baseline.

## Current repo purpose

This repo currently holds only the minimal baseline needed for future redesign implementation:
- config and package shell
- minimal API process with `/healthz` and `/readyz`
- DB file creation and reset shell
- service-install shell
- redesign and execution docs

## Ownership boundary

- **OpenClaw owns** provider transport and worker execution behavior.
- **AutoClaw redesign docs own** the future workflow, runtime, API, CLI, and plugin contracts.
- **This repo baseline does not currently implement** the redesign runtime, ingest, compiler, or console surfaces.

## Repo shape

- `definitions/` — intentionally emptied during the Phase 0.5 reset
- `apps/api/` — minimal baseline API, CLI, and package shell
- `apps/console/` — intentionally removed during the Phase 0.5 reset
- `examples/` — example workflows / plan patches / demo data
- `docs/` — architecture, roadmap, and decisions

## Roadmap

- `docs/README.md` — documentation index and reading guide
- `ROADMAP.md` — short front-door roadmap
- `docs/roadmap/current.md` — current working status
- `docs/refactor-checklist-runtime-stabilization.md` — completed runtime-stabilization closure record
- `docs/roadmap/` — detailed phase documents and backlog

## Start here

If you need the current repo truth instead of historical planning:

1. `README.md` — repo shape and quick orientation
2. `ROADMAP.md` — short public-facing status
3. `docs/roadmap/current.md` — current implementation status and verified baseline
4. `docs/README.md` — documentation map
5. `docs/refactor-checklist-runtime-stabilization.md` — closure record for the finished runtime-stabilization pass

## Docker run/test path

Default containerized workflow:

- `make docker-up` — start compose Postgres + API
- `make test-api-db` — run unit + integration tests against a real Postgres DB in Docker
- `make docker-down` — stop the compose stack

Current compose host ports:
- API: `http://127.0.0.1:8001`
- Postgres: `127.0.0.1:5433`

Only `/healthz` and `/readyz` remain live in the reset baseline. Redesign public API and CLI surfaces are documented under `docs/redesign/` and will be rebuilt in later phases.

The integration suite uses a real async SQLAlchemy session against a real Postgres test database.

## Package-first local install

The target product shape is now **package-first**, with **`pipx` as the default user install path**.

Current local baseline flow:

- `pipx install autoclaw`
- `autoclaw init`
- `autoclaw db upgrade`
- `autoclaw serve`

Repo-local contributor install still works too:

- `python3 -m venv .venv`
- `./.venv/bin/pip install .`
- `./.venv/bin/autoclaw init`
- `./.venv/bin/autoclaw db upgrade`
- `./.venv/bin/autoclaw serve`

Notes:

- default config lives in `~/.config/autoclaw/config.toml`
- default local DB is SQLite under the AutoClaw data dir
- `autoclaw init` writes the minimal config and ensures the DB file exists
- `autoclaw db reset` recreates an empty SQLite DB baseline
- packaged systemd template ships from `app.resources`
- Postgres remains the stronger verification lane; use `pipx install 'autoclaw[postgres]'` or `pip install '.[postgres]'` when you want that lane

## User-level systemd install path

A baseline user-service CLI exists:

- `autoclaw service install`
- service lifecycle control remains systemd-owned after install

`autoclaw service install` renders `~/.config/systemd/user/autoclaw.service` and uses the current Python environment via `python -m autoclaw ...`, so the same command shape works for pipx and venv installs.

For contributors working from the repo, the helper script still exists:

- `bash scripts/install-systemd-user.sh`

Optional helper-script flags:

- `--editable` for a contributor-style editable install
- `--postgres` to install the Postgres extra
- `--force-init` to rewrite `config.toml`
- `--no-start` to install without starting immediately

## Current focus

The current active work is **hard reset for future redesign implementation**:
- keep stale code, schema, tests, and package surfaces out of the future implementation baseline
- preserve only the minimal install/reset/health shell
- use `docs/redesign/` as the target contract for later rebuild phases

## Documentation rule

Current-behavior docs should say what is live now and carry a `Last verified` date. Historical phase docs should remain available, but they should not masquerade as the current source of truth.
