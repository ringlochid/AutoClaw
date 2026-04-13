# AutoClaw

AutoClaw is a long-running adaptive workflow framework built on top of OpenClaw.

## Current repo purpose

This repo holds the **AutoClaw framework layer**:
- definition registry seeds for roles / policies / workflows
- deterministic compiler scaffolding
- runtime/control-plane scaffolding
- operator console scaffolding

It does **not** own OpenClaw's skill package source by default.

## Ownership boundary

- **OpenClaw owns** actual skill packages (`SKILL.md`, scripts, references, execution behavior).
- **AutoClaw owns** workflow/role/policy definitions, skill bindings/refs, compile/runtime state, and operator UX.

## Repo shape

- `definitions/` — user-editable seed definitions
- `apps/api/` — registry + compiler + runtime backend
- `apps/console/` — operator dashboard
- `examples/` — example workflows / plan patches / demo data
- `docs/` — architecture and decisions

## Roadmap

- `ROADMAP.md` — canonical front-door roadmap
- `docs/roadmap/current.md` — current working phase
- `docs/roadmap/` — detailed phase documents and backlog

## Docker run/test path

Default containerized workflow:

- `make docker-up` — start compose Postgres + API
- `make test-api-db` — run unit + integration tests against a real Postgres DB in Docker
- `make docker-down` — stop the compose stack

Current compose host ports:
- API: `http://127.0.0.1:8001`
- Postgres: `127.0.0.1:5433`

The integration suite uses a real async SQLAlchemy session against a real Postgres test database.

## First implementation target

Build only the minimum kernel first:
1. definition registry
2. deterministic compiler v0
3. parent + main-loop-child runtime
4. checkpoints / approvals / basic retries
5. simple operator status view
