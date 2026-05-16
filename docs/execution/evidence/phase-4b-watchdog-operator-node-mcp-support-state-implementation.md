# Phase 4B Watchdog, Operator MCP, Node MCP, And Support-State Implementation Evidence

Status: Reference

selected phase: Phase 4B
current phase page: docs/execution/phases/phase-4b-watchdog-operator-plugin-and-support-state.md
selected work packages: P4B-WP1, P4B-WP2, P4B-WP3
summary-only: yes
delegated slices: listed
slice id: phase4b-watchdog-runtime-loop
slice type: edit
owned surfaces: apps/api/app/runtime/watchdog/**, apps/api/app/config.py, apps/api/app/main.py, apps/api/tests/integration/phase4b/watchdog/**, docs/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md
touched surfaces: apps/api/app/runtime/watchdog/service.py, apps/api/app/runtime/watchdog/recovery.py, apps/api/app/runtime/watchdog/classification.py, apps/api/tests/integration/phase4b/watchdog/support.py, apps/api/tests/integration/phase4b/watchdog/case_support.py, apps/api/tests/integration/phase4b/watchdog/test_recovery_actions.py, apps/api/tests/integration/phase4b/watchdog/test_stale_classification.py, apps/api/tests/integration/phase4b/watchdog/test_foreground_guards.py, docs/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md
slice id: phase4b-operator-mcp-wrapper
slice type: edit
owned surfaces: apps/api/autoclaw/openclaw/common.py, apps/api/autoclaw/openclaw/operator_server.py, apps/api/app/runtime/effects/writes.py, apps/api/tests/integration/phase4b/mcp/test_operator_server.py, apps/api/tests/integration/phase4b/mcp/support.py, docs/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md
touched surfaces: apps/api/autoclaw/openclaw/common.py, apps/api/autoclaw/openclaw/operator_server.py, apps/api/app/runtime/effects/writes.py, apps/api/tests/integration/phase4b/mcp/test_operator_server.py, apps/api/tests/integration/phase4b/mcp/support.py, docs/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md
slice id: phase4b-node-mcp-wrapper
slice type: edit
owned surfaces: apps/api/autoclaw/openclaw/node_server.py, apps/api/autoclaw/openclaw/bindings.py, apps/api/app/runtime/control/node_operations.py, apps/api/tests/integration/phase4b/mcp/test_node_server.py, apps/api/tests/integration/phase4b/mcp/support.py, docs/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md
touched surfaces: apps/api/autoclaw/openclaw/node_server.py, apps/api/autoclaw/openclaw/bindings.py, apps/api/app/runtime/control/node_operations.py, apps/api/tests/integration/phase4b/mcp/test_node_server.py, apps/api/tests/integration/phase4b/mcp/support.py, docs/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md
slice id: phase4b-review
slice type: review-only
owned surfaces: apps/api/app/runtime/watchdog/**, apps/api/autoclaw/openclaw/**, apps/api/app/runtime/effects/writes.py, apps/api/app/runtime/control/node_operations.py, apps/api/tests/integration/phase4b/**, docs/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md, docs/execution/evidence/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md, docs/execution/reviews/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md
touched surfaces: none

## Authoritative replacements

- `../evidence/phase-4b-session-bound-node-mcp-and-support-state-closeout.md`

## Slice identity

- work package or slice: final integrated proof for the merged Phase 4B watchdog/MCP/support-state work
- slice type: mixed delegated edit plus parent integration
- date: 2026-05-14

## Plan and review links

- approved plan: `../plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md`
- mandatory review: `../reviews/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md`
- review artifact: `../reviews/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md`

## Commands run

- `./.venv/bin/ruff check apps/api/app/runtime/watchdog apps/api/autoclaw/openclaw apps/api/tests/integration/phase4b apps/api/app/runtime/effects/writes.py apps/api/app/runtime/control/node_operations.py`
  outcome: passed
- `./.venv/bin/mypy apps/api/app/runtime/watchdog apps/api/autoclaw/openclaw apps/api/tests/integration/phase4b apps/api/app/runtime/effects/writes.py apps/api/app/runtime/control/node_operations.py`
  outcome: passed
- `make pyright-api`
  outcome: passed
- `./.venv/bin/pytest apps/api/tests/unit/test_config.py apps/api/tests/integration/phase4b -q`
  outcome: passed (`22 passed` in `160.50s`)
- `./.venv/bin/pytest -q`
  outcome: passed (`313 passed` in `27:49`)
- `make test-api-db`
  outcome: passed (`311 passed` in `22:52`)
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
  outcome: passed
- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
  outcome: passed
- `openclaw security audit --deep --json`
  outcome: executed; the deep probe reached the live gateway successfully and the findings were environment-scoped rather than repo-code blockers
- `./.venv/bin/pytest apps/api/tests/integration/test_db_reset_db.py apps/api/tests/integration/test_readyz_real_db.py -q`
  outcome: passed (`2 passed` in `5.77s`)

## 2026-05-14 repair slice proof

- `./.venv/bin/ruff check apps/api/autoclaw/openclaw apps/api/app/runtime/watchdog apps/api/app/runtime/control/node_operations.py apps/api/tests/integration/phase4b/mcp/test_node_server.py apps/api/tests/integration/phase4b/mcp/test_operator_server.py apps/api/tests/integration/phase4b/watchdog`
  outcome: passed
- `./.venv/bin/mypy apps/api/autoclaw/openclaw apps/api/app/runtime/watchdog/service.py apps/api/app/runtime/control/node_operations.py apps/api/tests/integration/phase4b/mcp/test_node_server.py apps/api/tests/integration/phase4b/mcp/test_operator_server.py`
  outcome: passed
- `./.venv/bin/pytest -q apps/api/tests/integration/phase4b/mcp/test_operator_server.py::test_phase4b_operator_mcp_uses_query_arguments_in_tool_schemas apps/api/tests/integration/phase4b/mcp/test_node_server.py::test_phase4b_node_mcp_call_parent_tool_keeps_top_level_revision_argument apps/api/tests/integration/phase4b/mcp/test_node_server.py::test_phase4b_node_mcp_rejects_same_dispatch_stale_authority apps/api/tests/integration/phase4b/watchdog/test_stale_classification.py::test_phase4b_watchdog_classifies_execution_stale_when_only_provider_signals_move`
  outcome: passed (`6 passed`)
- `./.venv/bin/pytest -q apps/api/tests/integration/phase4b/mcp/test_node_server.py apps/api/tests/integration/phase4b/mcp/test_operator_server.py apps/api/tests/integration/phase4b/watchdog`
  outcome: passed (`18 passed` in `187.01s`)

## 2026-05-14 repair slice delta

- `node MCP` now revalidates callback authority before bound writes and rejects
  revoked-binding, paused, cancel, and same-dispatch stale contexts through
  the same callback validator path.
- `operator MCP` now exposes `query` instead of `q` on the tool schemas for
  runtime-task listing and operator trace.
- `node MCP` keeps top-level `expected_structural_revision_id` on
  `call_parent_tool`.
- watchdog execution-stale timing now keys off controller progress only;
  recent provider signals alone no longer suppress stale classification.

## 2026-05-14 support-state freeze and inventory proof slice

- `./.venv/bin/ruff check apps/api/autoclaw/openclaw apps/api/tests/integration/phase4b/mcp/support.py apps/api/tests/integration/phase4b/mcp/test_operator_server.py apps/api/tests/integration/phase4b/mcp/test_node_server.py apps/api/tests/integration/phase3/routes/observability_support.py apps/api/tests/e2e/phase3/normal_lane/readback.py`
  outcome: passed
- `./.venv/bin/mypy apps/api/autoclaw/openclaw apps/api/tests/integration/phase4b/mcp/test_operator_server.py apps/api/tests/integration/phase4b/mcp/test_node_server.py`
  outcome: passed
- `./.venv/bin/python -m py_compile apps/api/tests/integration/phase3/routes/observability_support.py apps/api/tests/integration/phase4b/mcp/test_operator_server.py apps/api/tests/e2e/phase3/normal_lane/readback.py`
  outcome: passed
- `./.venv/bin/pytest -vv apps/api/tests/integration/phase4b/mcp/test_node_server.py apps/api/tests/integration/phase4b/mcp/test_operator_server.py apps/api/tests/integration/phase3/routes/test_surface_contract.py::test_phase3_runtime_routes_materialize_observability_files_from_dispatch_rows`
  outcome: passed (`11 passed` in `102.62s`)
- `./.venv/bin/pytest -vv -W error apps/api/tests/integration/phase4b/mcp/test_operator_server.py::test_phase4b_operator_mcp_cancel_wakes_shared_runtime_lifecycle`
  outcome: passed (`1 passed` in `9.87s`)

## 2026-05-14 support-state proof delta

- landed exact frozen field-set assertions for `delivery-state.json`,
  `continuity-state.json`, `watchdog-state.json`, and
  `provider-events.ndjson` in the shared observability helper used by the
  Phase 3 route surface contract and by the Phase 3 normal-lane readback
  assertions
- landed a live `operator MCP` support-state proof test that reads all four
  surfaced refs and validates the exact frozen field sets and root-dispatch
  values
- landed a live operator-vs-node MCP inventory comparison test that uses the
  actual repo-local `ClientSession.list_tools()` inventory read on separate
  operator and node MCP sessions; this is the truthful local equivalent of the
  Phase 4B `tools.effective` proof in this repo
- landed the Phase 4B test-harness DB teardown fix in
  `apps/api/tests/integration/phase4b/mcp/support.py`, and the targeted cancel
  lane now passes with warnings promoted to errors

## Gate and validator summary

- docs or prompt validators: `docs_freeze` passed after the final artifact path
  refresh
- language gates: integrated `ruff` and `mypy` passed on the touched Phase 4B surfaces
- reset or package checks: shipped reset-smoke proof passed on the final branch state

## Test lanes

- unit: not applicable
- integration: full Phase 4B integration lane passed
- e2e: covered by the final full local `pytest` lane for the currently viable minimal, normal, and maximal e2e set
- SQLite: covered by the integrated local Phase 4B pytest lane and the later full local `pytest` pass
- Postgres or Docker: covered by the later `make test-api-db` pass

## Artifacts changed

- `apps/api/app/runtime/watchdog/**`
- `apps/api/autoclaw/openclaw/**`
- touched shared runtime write/node-operation seams required by the Phase 3 and Phase 4 boundary integration
- `apps/api/tests/integration/phase4b/**`

## Residual blockers

- `none`
