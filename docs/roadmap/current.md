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
- expose initial runtime/registry API surface:
  - `POST /registry/bootstrap`
  - `POST /workflows/{workflow_key}/compile`
  - `GET /workflows/compiled-plans/{compiled_plan_id}`
  - `POST /runs/from-workflow/{workflow_key}`
  - `GET /runs/{run_id}`
  - `GET /runs/{run_id}/checkpoints`
  - `POST /runs/checkpoints`
  - `POST /approvals`, `GET /approvals/{id}`, `POST /approvals/{id}/resolve`
- added runtime e2e API verification (`test_full_phase_one_runtime_path_via_api`)

## Phase 1 implementation status

Phase 1 is now implemented and green for local + compose-backed DB integration:

- unit tests: **6 passed**
- DB integration tests: **12 passed**
- `make lint-api`: clean
- `make typecheck-api`: clean
- compose API smoke: bootstrap → compile → start run → inspect → checkpoint → approve

## Next phase focus

- phase-2 runtime transition engine (`ready/blocked/succeeded/failed` transitions, retries)
- API endpoints for listing/history by user/workflow/run
- task cancellation/attempt retry policy and worker execution bridge
- stronger policy constraints and richer validation for approvals/checkpoints
