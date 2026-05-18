# Phase 4.5 Session-Authority Simplification And Runtime Debt Removal Evidence

Status: Reference

selected phase: Phase 4.5
current phase page: docs/execution/phases/phase-4.5-session-authority-simplification-and-mcp-runtime-continuity-cleanup.md
selected work packages: P4.5-WP1, P4.5-WP2, P4.5-WP3, P4.5-WP4, P4.5-WP5, P4.5-WP6
summary-only: no
delegated slices: listed
slice id: phase45-docs-execution
slice type: edit
owned surfaces: docs/execution/**, docs/redesign/prompt-layer/**, docs/redesign/prompt-layer/generated/*, docs/redesign/prompt-layer/prompt-catalog.yaml, docs/current/interfaces/api-trust-lanes.md, docs/current/interfaces/api-surface-and-route-map.md, docs/current/architecture/openclaw-dispatch-and-session-contract.md, docs/current/architecture/openclaw-and-bridge-plugin.md, docs/current/architecture/runtime-control-plane.md, docs/current/architecture/watchdog-and-runtime-monitoring.md, docs/current/operations/use-the-openclaw-bridge-plugin.md
touched surfaces: docs/execution/**, docs/redesign/prompt-layer/generated/*, docs/current/interfaces/api-trust-lanes.md, docs/current/interfaces/api-surface-and-route-map.md, docs/current/architecture/openclaw-dispatch-and-session-contract.md, docs/current/architecture/openclaw-and-bridge-plugin.md, docs/current/architecture/runtime-control-plane.md, docs/current/architecture/watchdog-and-runtime-monitoring.md, docs/current/operations/use-the-openclaw-bridge-plugin.md
slice id: phase45-authority-runtime-db
slice type: edit
owned surfaces: apps/api/app/runtime/**, apps/api/app/db/**, apps/api/app/schemas/**, apps/api/tests/integration/phase3/**, apps/api/tests/integration/phase4a/**, apps/api/tests/integration/runtime_schema_contract/**
touched surfaces: apps/api/app/runtime/**, apps/api/app/db/**, apps/api/app/schemas/**, apps/api/tests/integration/phase3/**, apps/api/tests/integration/phase4a/**, apps/api/tests/integration/runtime_schema_contract/**
slice id: phase45-node-mcp-callback
slice type: edit
owned surfaces: apps/api/autoclaw/openclaw/**, apps/api/app/api/routes/callback.py, apps/api/app/runtime/control/node_operations.py, apps/api/app/runtime/control/dispatch/authority.py, apps/api/tests/integration/phase4b/mcp/**, apps/api/tests/e2e/phase4/**, apps/api/tests/helpers/parent_first_lane.py, apps/api/tests/helpers/parent_first_lane_runtime.py, apps/api/tests/helpers/parent_first_lane_readback.py
touched surfaces: apps/api/autoclaw/openclaw/**, apps/api/app/api/routes/callback.py, apps/api/app/runtime/control/node_operations.py, apps/api/app/runtime/control/dispatch/authority.py, apps/api/tests/integration/phase4b/mcp/**, apps/api/tests/e2e/phase4/**, apps/api/tests/helpers/parent_first_lane.py
slice id: phase45-watchdog-observability
slice type: edit
owned surfaces: apps/api/app/runtime/watchdog/**, apps/api/app/runtime/projection/**, apps/api/tests/integration/phase4b/**, apps/api/tests/integration/runtime_schema_contract/**, apps/api/tests/e2e/**
touched surfaces: apps/api/app/runtime/watchdog/**, apps/api/app/runtime/projection/**, apps/api/tests/integration/phase4b/**, apps/api/tests/integration/runtime_schema_contract/**
slice id: phase45-prompt-runtime-assets
slice type: edit
owned surfaces: apps/api/app/runtime/prompt/**, apps/api/app/runtime/contract_models/**, apps/api/app/runtime/projection/dispatch/prompt.py, apps/api/app/runtime/task_root/**, apps/api/tests/unit/runtime_prompt_rendering/**, apps/api/tests/integration/phase2/bootstrap/**, apps/api/tests/integration/phase3/**
touched surfaces: apps/api/app/runtime/prompt/**, apps/api/app/runtime/projection/dispatch/prompt.py, apps/api/tests/integration/phase2/bootstrap/**, apps/api/tests/integration/phase3/**
slice id: phase45-qa-gate-review
slice type: review-only
owned surfaces: apps/api/**, docs/redesign/**, docs/current/**, docs/execution/plans/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md, docs/execution/evidence/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md
touched surfaces: none
slice id: phase45-strict-closeout-review
slice type: edit
owned surfaces: docs/execution/reviews/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md
touched surfaces: docs/execution/reviews/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md

## Slice identity

- work package or slice: final Phase 4.5 closeout evidence after the last Postgres-only proof repair
- slice type: authoritative phase-scoped closeout proof
- date: 2026-05-18

## Parent integration collateral truth

- parent-owned final-proof collateral outside delegated slices:
  - `apps/api/tests/integration/phase4a/dispatch_gateway_support.py`

## Plan and review links

- approved plan: `../plans/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md`
- mandatory review: `../reviews/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md`
- review artifact: `../reviews/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md`

## Commands run

- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli generate` -> passed
- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate` -> passed
- `./.venv/bin/python -m scripts.docs.docs_freeze.cli` -> passed
- `./.venv/bin/ruff format --check apps/api` -> passed
- `./.venv/bin/ruff check apps/api` -> passed
- `./.venv/bin/mypy apps/api/app apps/api/tests` -> passed
- `make pyright-api` -> passed
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings` -> passed
- `./.venv/bin/pytest -W error` -> passed, `351 passed in 2733.62s (0:45:33)`
- `make test-api-db` -> passed, `348 passed in 2344.68s (0:39:04)`
- targeted proving checkpoint split:
  - `./.venv/bin/pytest -W error -x apps/api/tests/integration/phase2/bootstrap apps/api/tests/integration/phase3/contracts/test_callback_cases.py apps/api/tests/integration/phase3/contracts/test_callback_failure_contract_cases.py apps/api/tests/integration/phase3/control/test_abort_cases.py apps/api/tests/integration/phase3/routes/test_surface_contract.py apps/api/tests/integration/phase4a/test_runtime_dispatch_gateway_integration.py apps/api/tests/integration/phase4a/test_gateway_session_reuse.py -q`
    -> passed, `50 passed in 541.14s (0:09:01)`
  - no separate late targeted rerun was kept for the remaining Phase 4B/watchdog/runtime-schema/e2e proof surfaces after the last cleanup cycle because the final full `pytest -W error`, final `make test-api-db`, and the split targeted coverage checkpoints below already re-proved those surfaces on the exact closeout tree
- targeted coverage checkpoint split:
  - `./.venv/bin/pytest -W error -x --cov=app.runtime.control.dispatch --cov=app.runtime.watchdog --cov=app.runtime.prompt --cov=app.runtime.projection --cov=autoclaw.openclaw --cov-report=term-missing:skip-covered apps/api/tests/integration/phase4a/test_runtime_dispatch_gateway_integration.py apps/api/tests/integration/phase4a/test_gateway_session_reuse.py -q`
    -> passed, `6 passed in 33.70s`; runtime-side targeted coverage report recorded `TOTAL 2217 / 972 missed / 56%`
    -> note: this runtime-side coverage pass emitted the expected coverage warning `Module autoclaw.openclaw was never imported` because it intentionally targeted the runtime-side surfaces only
  - `./.venv/bin/pytest -W error --cov=autoclaw.openclaw --cov-report=term-missing:skip-covered apps/api/tests/integration/phase4b/mcp/test_node_server.py apps/api/tests/integration/phase4b/mcp/test_operator_server.py apps/api/tests/integration/phase4b/mcp/test_operator_server_failures.py -q`
    -> passed, `16 passed in 140.81s (0:02:20)`; MCP-wrapper targeted coverage report recorded `TOTAL 372 / 76 missed / 80%`
- shipped-path SQLite reset plus real host proof:
  - `./.venv/bin/autoclaw db reset --config /tmp/autoclaw-phase45-host-proof/autoclaw-config.toml --json`
    -> passed, `{"ok": true, ...}`
  - `./.venv/bin/autoclaw serve --config /tmp/autoclaw-phase45-host-proof/autoclaw-config.toml`
    -> passed as the live host-proof service on `127.0.0.1:18123`
  - live MCP inventory and node-tool proof against that host:
    - operator MCP inventory on `http://127.0.0.1:18123/operator/mcp` returned the expected operator/runtime/support inventory
    - node MCP inventory on `http://127.0.0.1:18123/node/mcp/` returned exactly `call_parent_tool`, `get_definition`, `record_checkpoint`, `return_boundary`, and `search_definitions`
    - a real node MCP `get_definition(session_key, task_id, kind=role, key=researcher)` call succeeded and returned `role_key=researcher`, `revision_no=1`
- targeted regression repair proof:
  - `./.venv/bin/pytest -W error apps/api/tests/integration/phase4a/test_runtime_dispatch_gateway_integration.py apps/api/tests/integration/phase4a/test_gateway_session_reuse.py -q` -> passed, `6 passed`
  - DB-backed exact repro after reset:
    `docker compose run --rm api-test sh -lc 'cd /app && PYTHONPATH=/app/apps/api python -m autoclaw db upgrade && PYTHONPATH=/app/apps/api pytest -W error apps/api/tests/integration/phase4a/test_runtime_dispatch_gateway_integration.py::test_launch_runtime_persists_gateway_session_run_and_node_session_truth -q'`
    -> passed, `1 passed`

## Current workspace progress

- `P4.5-WP1` and `P4.5-WP2`: landed code keeps callback HTTP and node MCP on one `NodeSession.session_key` authority model and removes the old callback-binding live truth
- `P4.5-WP3`: landed code keeps parent/root same-attempt Gateway reuse on the same `sessionKey` with fresh `runId` and fresh `idempotencyKey`
- `P4.5-WP4`: landed code keeps `full_prompt` as the live prompt payload and keeps node-tool context explicit on `task_id` plus `session_key`
- `P4.5-WP5`: landed code keeps watchdog recovery narrowed and redundant transport-observation ballast removed from live runtime truth
- `P4.5-WP6`: the final proof matrix is now rerun and green on the exact closeout tree

## Final repair recorded in this closeout slice

- root causes:
  - `apps/api/tests/integration/phase4a/dispatch_gateway_support.py` assembled the success-path dispatch snapshot from multiple separate reads, so Postgres `READ COMMITTED` could observe mixed-time runtime rows
  - the failure-path selected-suite order could still surface late `aiosqlite` close callbacks as pytest unraisable or thread-exception warnings
- fixes:
  - `apps/api/tests/integration/phase4a/dispatch_gateway_support.py` now selects the latest `dispatch_id` first, then eager-loads dispatch, flow, delivery state, continuity state, node sessions, and provider events in one consistent read; the old reusable mixed-time helper seam was removed
  - `apps/api/tests/integration/phase4a/test_runtime_dispatch_gateway_integration.py` now drops the stale `runtime` reference before the fresh failure-path reread
  - `apps/api/app/db/session.py` now gives `aiosqlite` worker threads a short post-dispose scheduling window before pytest inspects unraisable or thread exceptions
- scope: the final closeout repair touched one app DB cleanup helper plus narrow Phase 4A proof surfaces; no product runtime contract changed

## Shipped-path host proof note

- first host attempt against the already-running local `autoclaw serve --config /home/ubuntu/.config/autoclaw/e2e-openclaw-test.toml` service exposed environment-side stale SQLite schema drift: `dispatch_turns.phase` was still `NOT NULL`
- Phase 4.5 requires reset-gate proof when runtime or persistence truth changes, so the authoritative closeout proof was rerun on a fresh current-schema config through the shipped `autoclaw db reset` plus `autoclaw serve` path instead of treating the stale local service as repo-code truth
- outcome: the fresh shipped-path host lane proved current schema, correct operator/node MCP inventories, and one real node-tool call

## Gate and validator summary

- docs or prompt validators:
  - `prompt_catalog generate` passed
  - `prompt_catalog validate` passed
  - `docs_freeze` passed
- language gates:
  - `ruff format --check apps/api` passed
  - `ruff check apps/api` passed
  - `mypy apps/api/app apps/api/tests` passed
  - `make pyright-api` passed
  - `style_audit --fail-on-findings` passed
- reset or package checks:
  - `make test-api-db` passed after full DB reset and container rebuild
  - shipped-path SQLite `autoclaw db reset --config /tmp/autoclaw-phase45-host-proof/autoclaw-config.toml --json` passed before the host proof replay

## Test lanes

- unit: included in the full `pytest -W error` replay and in the containerized Postgres replay; both passed
- integration: included in the full `pytest -W error` replay and in the containerized Postgres replay; both passed
- e2e: minimal, normal, and maximal lanes are included in `./.venv/bin/pytest -W error`; that replay passed
- SQLite or default local lane: `./.venv/bin/pytest -W error` passed with `351 passed`
- targeted proving split:
  - Phase 2/3/4A targeted proving prefix passed with `50 passed`
  - late Phase 4B/runtime-schema/e2e targeted proving surfaces were superseded by the final full `pytest -W error`, final `make test-api-db`, and the split targeted coverage checkpoints on the exact latest tree
- SQLite shipped-path reset proof: passed on `/tmp/autoclaw-phase45-host-proof/autoclaw-config.toml`
- Postgres or Docker lane: `make test-api-db` passed with `348 passed`
- host OpenClaw proof:
  - deep host audit passed with `deep.gateway.ok=true` from `openclaw security audit --deep --json`
  - fresh shipped-path host serve proof passed on `127.0.0.1:18123`
  - live operator/node MCP inventories were correct and a real node-MCP `get_definition` call succeeded

## Artifacts changed

- the final closeout repair changed:
  - `apps/api/app/db/session.py`
  - `apps/api/tests/integration/phase4a/dispatch_gateway_support.py`
  - `apps/api/tests/integration/phase4a/test_runtime_dispatch_gateway_integration.py`
- the authoritative Phase 4.5 evidence artifact now records the real proof matrix, the targeted proving split, the targeted coverage split, the exact final regression root causes, the shipped-path SQLite reset/serve host proof, and the environment-side stale-service note

## Residual blockers

- none in executed code-proof lanes
- the pre-existing `/home/ubuntu/.config/autoclaw/e2e-openclaw-test.toml` service carried stale local SQLite state before reset; that remained an environment-side local-instance condition, not a repo-code blocker, once the shipped-path reset plus host proof succeeded
- the remaining closeout step is the authoritative strict review verdict recorded in the Phase 4.5 review artifact
