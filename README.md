# AutoClaw

AutoClaw is a long-running adaptive workflow framework built on top of OpenClaw.

## Current repo purpose

This repo holds the **AutoClaw framework layer**:
- definition registry seeds for roles / policies / workflows
- deterministic compiler
- flow-first runtime / control plane
- operator console

It does **not** own OpenClaw's skill package source by default.

## Ownership boundary

- **OpenClaw owns** actual skill packages (`SKILL.md`, scripts, references, execution behavior).
- **AutoClaw owns** workflow/role/policy definitions, skill bindings/refs, compile/runtime state, and operator UX.

## Repo shape

- `definitions/` — user-editable seed definitions
- `apps/api/` — registry + compiler + runtime backend
- `apps/console/` — operator console
- `examples/` — example workflows / plan patches / demo data
- `docs/` — architecture, roadmap, and decisions

## Roadmap

- `ROADMAP.md` — short front-door roadmap
- `docs/roadmap/current.md` — current working status
- `docs/roadmap/06.5-phase-6.5-pre-phase-7-stabilization.md` — active stabilization gate before Phase 7
- `docs/roadmap/07-phase-7-controller-driven-looping-and-governance.md` — next phase after stabilization
- `docs/roadmap/` — detailed phase documents and backlog

## Docker run/test path

Default containerized workflow:

- `make docker-up` — start compose Postgres + API
- `make test-api-db` — run unit + integration tests against a real Postgres DB in Docker
- `make docker-down` — stop the compose stack

Current compose host ports:
- API: `http://127.0.0.1:8001`
- Postgres: `127.0.0.1:5433`

Public/operator runtime routes are intended for `AUTOCLAW_API_KEY`.
Internal audit/control routes require `AUTOCLAW_INTERNAL_API_KEY`; that internal key is also accepted on the public/operator routes for internal automation.
`/healthz` and `/readyz` remain public.
For the console, pass the operator key through `VITE_AUTOCLAW_API_KEY`.

The integration suite uses a real async SQLAlchemy session against a real Postgres test database.

## Package-first local install

The target product shape is now **package-first**, with **`pipx` as the default user install path**.

Typical local install:

- `pipx install autoclaw`
- `autoclaw doctor`
- `autoclaw init`
- `autoclaw up`

Repo-local contributor install still works too:

- `python3 -m venv .venv`
- `./.venv/bin/pip install .`
- `./.venv/bin/autoclaw doctor`
- `./.venv/bin/autoclaw init`
- `./.venv/bin/autoclaw up`

Notes:

- default config lives in `~/.config/autoclaw/config.toml`, with the default editable definitions root at `~/.config/autoclaw/definitions/`
- default local DB is SQLite under the AutoClaw data dir, and the package-first default API/console port is `8123`
- `autoclaw init` is the pretty default entrypoint: interactive on a real TTY, split into clearer setup sections, auto-prefilling a detected local OpenClaw when possible, surfacing the definitions root explicitly, and leaving flags like `--database-url`, `--sqlite-path`, `--definitions-root`, `--host`, and `--port` for scripting/CI via `--non-interactive`
- after a successful interactive init, AutoClaw now offers a final optional `autoclaw service install` step instead of making you remember it later
- `autoclaw doctor` now reports both packaged definitions and the configured editable definitions root separately, so the active source layout is obvious
- `autoclaw up` runs the DB upgrade, then starts the API and bundled console
- packaged console assets / definitions / alembic resources / systemd template ship from `app.resources`
- Postgres remains the stronger production/concurrency path; use `pipx install 'autoclaw[postgres]'` or `pip install '.[postgres]'` when you want that lane

## User-level systemd install path

A first real user-service CLI now exists:

- `autoclaw service install`
- `autoclaw service up`
- `autoclaw service status`
- `autoclaw service restart`
- `autoclaw service stop`

`autoclaw service install` renders `~/.config/systemd/user/autoclaw.service` and uses the current Python environment via `python -m autoclaw ...`, so the same command shape works for pipx and venv installs.

For contributors working from the repo, the helper script still exists:

- `bash scripts/install-systemd-user.sh`

Optional helper-script flags:

- `--editable` for a contributor-style editable install
- `--postgres` to install the Postgres extra
- `--force-init` to rewrite `config.toml`
- `--no-start` to install without starting immediately

## Current focus

The current active work is **Phase 6.5**:
- tighten control integrity on runtime writes
- simplify transition ownership before controller-driven looping lands
- clean the operator/public surface so it reflects the flow-first model
- align front-door docs and indexes with the real current state
