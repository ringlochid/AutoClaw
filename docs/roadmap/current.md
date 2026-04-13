# Current Phase

## Active phase

**Phase 3 — Runtime and OpenClaw Integration**

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
- persisted registry bootstrap/publish flow for roles, policies, workflows, and external skill refs
- deterministic compiler v0 path: resolve -> validate -> normalize -> hash -> persist compiled plan
- compose-backed Postgres run/test path with DB-backed integration tests
- query-path indexes for registry/runtime lookup paths
- Phase 2 deliverables are effectively satisfied in the current codebase:
  - published registry bootstrap/publish path
  - deterministic compile path + compiled plan persistence
  - compile-backed run start from published workflow versions
- exposed runtime/registry API surface:
  - `POST /registry/bootstrap`
  - `POST /workflows/{workflow_key}/compile`
  - `GET /workflows/compiled-plans/{compiled_plan_id}`
  - `POST /runs/from-workflow/{workflow_key}`
  - `GET /runs/{run_id}`
  - `GET /runs/{run_id}/checkpoints`
  - `POST /runs/checkpoints`
  - `POST /approvals`, `GET /approvals/{id}`, `POST /approvals/{id}/resolve`
- initial Phase 3 runtime control slice is now in place:
  - approval creation blocks the active run/attempt/flow chain
  - checkpoint writes now drive basic runtime state transitions
  - `POST /runs/{run_id}/continue` advances/unblocks the current run
  - `POST /runs/{run_id}/cancel` cancels the current chain and pauses open nodes
  - approval rejection/expiry fails the run cleanly
- API integration coverage now includes runtime control flow (`continue`, blocked approvals, rejection failure, cancel)

## Current implementation status

Current verified state is green for local + compose-backed DB integration:

- unit tests: **6 passed**
- DB integration tests: **13 passed**
- `make check-api`: clean
- compose-backed runtime/API path verified through integration tests

## Next phase focus

- real OpenClaw adapter for session/task dispatch from runnable flow nodes
- richer retry semantics (attempt retry policy vs simple node reset)
- pause/resume semantics beyond the current cancel placeholder
- API endpoints for listing/history by user/workflow/run
- stronger policy constraints and richer validation for approvals/checkpoints
- minimal session-link/runtime ownership fields if the adapter needs them
