# Current Phase

## Active phase

**Phase 1 — Kernel and Data Model**

## Already done

- repo scaffold
- async-first backend/tooling baseline
- initial definitions seed files
- initial API health/ready path
- architecture/roadmap docs skeleton
- first SQLAlchemy registry/runtime models
- first Alembic env + initial migration scaffold
- initial Pydantic registry/runtime schemas
- initial registry seed-loading helpers
- initial run/attempt/flow/checkpoint service scaffolding
- persisted registry bootstrap/publish flow for roles, policies, workflows, and external skill refs
- deterministic compiler v0 path: resolve -> validate -> normalize -> hash -> persist compiled plan
- compose-backed Postgres run/test path with DB-backed integration tests

## Current implementation focus

1. Add minimal run creation + flow instantiation from compiled plans.
2. Expose the first runtime/registry API endpoints.
3. Add inspect/read endpoints for compiled plans, runs, checkpoints, and approvals.
4. Tighten registry/compiler persistence behavior around versioning and idempotency.
5. Build the first end-to-end API demo path: publish -> compile -> run -> checkpoint -> inspect.

## Immediate next checkpoint

The next meaningful checkpoint is:

> create a task from a published workflow, compile it, start a run, instantiate a flow, and persist one checkpoint.

## Intentionally deferred right now

- advanced hierarchy
- rich console work
- dynamic plan patch adoption
- broad workflow-pack expansion
