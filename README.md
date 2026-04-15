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

## Current focus

The current active work is **Phase 6.5**:
- tighten control integrity on runtime writes
- simplify transition ownership before controller-driven looping lands
- clean the operator/public surface so it reflects the flow-first model
- align front-door docs and indexes with the real current state
