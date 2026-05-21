# Phase 4B Watchdog, Operator MCP, Node MCP, And Support-State Implementation Review

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
owned surfaces: apps/api/autoclaw/openclaw/node_server.py, apps/api/autoclaw/openclaw/bindings.py, apps/api/app/runtime/control/node_operations.py, apps/api/tests/integration/phase4b/mcp/node_server, apps/api/tests/integration/phase4b/mcp/support.py, docs/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md
touched surfaces: apps/api/autoclaw/openclaw/node_server.py, apps/api/autoclaw/openclaw/bindings.py, apps/api/app/runtime/control/node_operations.py, apps/api/tests/integration/phase4b/mcp/node_server, apps/api/tests/integration/phase4b/mcp/support.py, docs/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md
slice id: phase4b-review
slice type: review-only
owned surfaces: apps/api/app/runtime/watchdog/**, apps/api/autoclaw/openclaw/**, apps/api/app/runtime/effects/writes.py, apps/api/app/runtime/control/node_operations.py, apps/api/tests/integration/phase4b/**, docs/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md, docs/execution/evidence/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md, docs/execution/reviews/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md
touched surfaces: none

## Authoritative replacements

- `../reviews/phase-0-phase45-simplification-canon-fix.md`

## Slice identity

- work package or slice: final independent review transcription for the merged Phase 4B slices
- date: 2026-05-14

## Phase-local contract

- current phase page: `docs/execution/phases/phase-4b-watchdog-operator-plugin-and-support-state.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`

## Scope

- reviewed plan: `../plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md`
- reviewed evidence: `../evidence/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md`

## Verdict

- pass/fail: pass
- summary: Phase 4B-owned code/test proof is sufficient and the remaining environment-scoped security findings do not map back to repo-managed wrapper code.

## 2026-05-14 repair slice review

- pass/fail: pass
- summary: the callback-authority parity gap on `node MCP`, the `operator MCP` `q`/`query` schema drift, the watchdog provider-signal stale-classification bug, the ghost watchdog-config debt, and the oversized operator MCP registration function are all repaired and backed by focused plus broad proof lanes.

## Findings

- watchdog recovery now executes and the focused watchdog suite was green
- operator MCP writes now use the shared controller-owned runtime write boundary and the focused operator suite was green
- node MCP now routes through the shared node-operation seam and the focused node suite was green
- runtime-effective inventory proof is satisfied by the equivalent live operator/node `ClientSession.list_tools()` reads on separate MCP sessions
- exact support-state freeze proof is satisfied by the new field-set assertions and their executed operator/route/e2e coverage
- the retained `aiosqlite` warning is resolved in the targeted cancel lane and no longer appears in the final broad proof totals
- `openclaw security audit --deep --json` executed; its findings are environment-scoped and do not map back to repo-managed Phase 4B wrapper code

## 2026-05-14 repair slice findings

- fixed: `node MCP` now calls the same callback validator path used by `/callback` before bound writes, so revoked-binding, paused, cancel, and stale same-dispatch contexts are rejected before any runtime mutation.
- fixed: `operator MCP` tool schemas now expose `query` instead of `q` for task listing and operator trace.
- fixed: watchdog execution-stale classification now ignores `last_provider_signal_at` and classifies based on controller progress only.
- confirmed: top-level `expected_structural_revision_id` remains present on `node MCP` `call_parent_tool`.
- final Phase 4B-owned code/test surface has no unresolved repo-local blocker.

## 2026-05-14 support-state freeze and inventory proof review

- proof-only verdict: pass
- summary: the exact-shape support-state assertions, live operator-vs-node inventory proof, and cancel-lane warning fix are all landed and executed.

## 2026-05-14 support-state proof findings

- fixed in code: the shared observability helper now freezes exact field sets for `delivery-state.json`, `continuity-state.json`, `watchdog-state.json`, and `provider-events.ndjson`, and the Phase 3 normal-lane readback now asserts those frozen shapes as well
- fixed in code: `operator MCP` now has a dedicated support-state proof test that reads all four surfaced refs and validates the frozen shapes and root-dispatch values
- fixed in code: the runtime-effective separation proof is now written as the truthful local equivalent runtime inventory read available in this repo, using separate operator and node `ClientSession.list_tools()` reads instead of overclaiming unavailable `tools.effective` support
- fixed in execution: the support-state and live-inventory tests now execute and pass after the later dispatch/opening and observability-support cleanup
- fixed in execution: the targeted MCP cancel lane passes with `-W error`, so the retained `aiosqlite` warning is resolved in the repo-local proof surface
- fixed in execution: the shipped reset-smoke lane now passes on the final branch state
- confirmed in execution: `openclaw security audit --deep --json` now reaches the live gateway successfully; its remaining findings are host-environment findings outside the repo-managed wrapper code

## Delegated-slice compliance

- `no subagents` or delegated-slice summary: three edit slices and one review-only slice were used
- owned-surface compliance: pass for the final owned plus allowed-collateral surface set
- review-only compliance: pass; the review-only slice did not edit files
- wave integration proof: parent integrated the merged watchdog/operator/node slices and reran the integrated Phase 4B pytest lane
- authoritative proof link: `../evidence/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md`

## Proof lanes relied on

- integrated `ruff` and `mypy` across the touched Phase 4B surfaces
- `make pyright-api`
- integrated `pytest apps/api/tests/unit/test_config.py apps/api/tests/integration/phase4b -q`
- full local `pytest` (`313 passed`)
- `make test-api-db` (`311 passed`)
- shipped reset-smoke lane (`2 passed`)
- `openclaw security audit --deep --json`

## 2026-05-14 repair slice proof lanes relied on

- `./.venv/bin/ruff check apps/api/autoclaw/openclaw apps/api/app/runtime/watchdog apps/api/app/runtime/control/node_operations.py apps/api/tests/integration/phase4b/mcp/node_server apps/api/tests/integration/phase4b/mcp/test_operator_server.py apps/api/tests/integration/phase4b/watchdog`
- `./.venv/bin/mypy apps/api/autoclaw/openclaw apps/api/app/runtime/watchdog/service.py apps/api/app/runtime/control/node_operations.py apps/api/tests/integration/phase4b/mcp/node_server apps/api/tests/integration/phase4b/mcp/test_operator_server.py`
- focused regression lane (`6 passed`)
- targeted Phase 4B MCP/watchdog lane (`18 passed`)

## 2026-05-14 support-state proof lanes relied on

- `./.venv/bin/ruff check apps/api/autoclaw/openclaw apps/api/tests/integration/phase4b/mcp/support.py apps/api/tests/integration/phase4b/mcp/test_operator_server.py apps/api/tests/integration/phase4b/mcp/node_server apps/api/tests/integration/phase3/routes/observability_support.py apps/api/tests/e2e/phase3/normal_lane/readback.py`
- `./.venv/bin/mypy apps/api/autoclaw/openclaw apps/api/tests/integration/phase4b/mcp/test_operator_server.py apps/api/tests/integration/phase4b/mcp/node_server`
- `./.venv/bin/python -m py_compile apps/api/tests/integration/phase3/routes/observability_support.py apps/api/tests/integration/phase4b/mcp/test_operator_server.py apps/api/tests/e2e/phase3/normal_lane/readback.py`
- `./.venv/bin/pytest -vv apps/api/tests/integration/phase4b/mcp/node_server apps/api/tests/integration/phase4b/mcp/test_operator_server.py apps/api/tests/integration/phase3/routes/test_surface_contract.py::test_phase3_runtime_routes_materialize_observability_files_from_dispatch_rows` outcome: passed (`11 passed` in `102.62s`)
- `./.venv/bin/pytest -vv -W error apps/api/tests/integration/phase4b/mcp/test_operator_server.py::test_phase4b_operator_mcp_cancel_wakes_shared_runtime_lifecycle` outcome: passed (`1 passed` in `9.87s`)

## Stale-logic search proof

- commands or search terms: watchdog recovery execution vs projection-only state, operator/node raw commit paths, duplicated node/callback logic
- outcome: the earlier raw commit-path, projection-only seam, and callback-parity drift were removed from the integrated code paths reviewed in this slice

## Kill-list proof

- phase kill-list source: `docs/execution/phases/phase-4b-watchdog-operator-plugin-and-support-state.md`
- terms checked: raw transport state treated as controller truth, mixed worker/operator assumptions, config-only success without proof
- outcome: satisfied

## Docs answer-sourcing proof

- redesign owners relied on: watchdog/recovery contract, runtime observability and boundary log, MCP boundary, plugin tool reference, human/operator control surface, runtime DB/object contract
- supporting redesign reads or appendix owners relied on: runtime monitoring and watchdog automation, runtime lane separation rationale, provider/worker/operator boundary, watchdog/provider recovery, operator role boundary, guarded runtime writes, ADR-0004, debug/recover how-to pages, API schema appendix, prompt resource appendix
- current-contrast pages relied on: watchdog/runtime monitoring, watchdog/OpenClaw bridge, current bridge-plugin usage, API surface/trust-lane pages
- code or tests inspected: merged Phase 4B watchdog and MCP surfaces plus the touched Phase 4B tests
- canon gap or explicit `none`: none

## Private-symbol search proof

- exact repo search confirmed no retained flagged underscore-private shared helper or private-symbol exception remained in the touched Phase 4B watchdog/MCP/support-state surfaces after the final cleanup pass

## Phase-bounded STYLE exceptions

- `none`

## Reset-gate outcome

- pass: runtime/support-state truth changed, and the shipped reset-smoke lane plus the broad SQLite/Postgres verification lanes were rerun on the final branch state

## Cross-links

- aggregate historical summary, if any: none
- companion exceptions page, if any: none
