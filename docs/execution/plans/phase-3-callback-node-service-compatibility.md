# Phase 3 Callback Node Service Compatibility

Status: Reference

selected phase: Phase 3
current phase page: docs/execution/phases/phase-3-runtime-parent-review-and-replan.md
selected work packages: P3-WP1, P3-WP2
summary-only: no
delegated slices: none

## Slice identity

- date: 2026-05-14
- slice type: `edit`
- owner: parent agent
- selected repair: tighten lifecycle settle semantics and remove owned helper shortcuts that bypass the real Gateway-backed runtime path

## Subagents decision

- no subagents

## Owned surfaces

- `apps/api/app/runtime/effects/worker.py`
- `apps/api/app/runtime/effects/__init__.py`
- `apps/api/tests/integration/phase3/runtime_support.py`
- `apps/api/tests/integration/phase3/control/test_boundary_cases.py`
- `apps/api/tests/integration/phase3/contracts/`
- `apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`
- `apps/api/app/cli.py` only if strictly needed
- `docs/execution/plans/phase-3-callback-node-service-compatibility.md`
- `docs/execution/evidence/phase-3-callback-node-service-compatibility.md`
- `docs/execution/reviews/phase-3-callback-node-service-compatibility.md`

## Do not edit / stop conditions

- do not edit `apps/api/autoclaw/**`
- do not edit `apps/api/app/runtime/openclaw/**`
- do not edit `apps/api/app/runtime/watchdog/**`
- do not edit Phase 4A or Phase 4B docs
- stop if the truthful repair needs callback route or node-operations changes

## Required reads completed

- `AGENTS.md`
- `STYLE.md`
- `docs/execution/README.md`
- `docs/execution/phases/overview.md`
- `docs/execution/maps/file-priority-map.md`
- `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
- `docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md`
- `docs/redesign/workflows/parent-root-release-and-closure.md`
- `tmp/PLAN_FIX_CLOSE_P4.md`
- `tmp/findings.5.14.2.md`
- current `runtime_support.py`, `worker.py`, and the owned Phase 3 and Phase 2 test surfaces

## Goal

- make `wait_for_runtime_effects(task_id=...)` stop on semantic settle rather than one unchanged reconcile cycle
- remove owned hidden `provider_completed` DB mutations where the real lifecycle wait path is already available
- keep the closure path off the public `cli.py` aliases by using the existing test-only helper entrypoints in owned support code
- refresh the Phase 3 execution artifacts to match the repaired contract and the proof actually run in this turn

## Planned edits

- in `worker.py`, keep task-scoped waits running until the selected task no longer requires foreground lifecycle reconciliation
- in `runtime_support.py`, use `cli._cmd_init` and `cli._command_env`, then assert provider-terminal truth before `/continue` instead of mutating `delivery_status`
- in the owned contract and e2e tests, replace direct `provider_completed` mutation with `wait_for_runtime_effects(...)` where the autoconfigured Gateway fixture already exercises the real path
- in the execution artifacts, replace the stale delegated-wave narrative with this narrow parent-owned repair record

## Success criteria

- `wait_for_runtime_effects(task_id=...)` no longer returns after a single unchanged pending snapshot
- owned helper and test paths do not force `dispatch.delivery_status = "provider_completed"` to advance continuation flow
- the closure path no longer depends on `runtime_support.py` importing the public `cli.cmd_init` or `cli.command_env` aliases
- the requested narrow proof passes without widening into OpenClaw adapter, watchdog, or callback-route ownership

## Validation

- `./.venv/bin/ruff check apps/api/app/runtime/effects/worker.py apps/api/app/runtime/effects/__init__.py apps/api/tests/integration/phase3/runtime_support.py apps/api/tests/integration/phase3/control/test_boundary_cases.py apps/api/tests/integration/phase3/contracts/ apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py apps/api/app/cli.py`
- `./.venv/bin/mypy apps/api/app/runtime/effects/worker.py apps/api/tests/integration/phase3/runtime_support.py`
- `./.venv/bin/pytest -q apps/api/tests/integration/phase3/control/test_boundary_cases.py::test_phase3_boundary_waits_for_inactivity_proof_before_opening_replacement_dispatch apps/api/tests/integration/phase3/control/test_boundary_cases.py::test_phase3_pause_waits_for_inactivity_proof_before_reopening_dispatch apps/api/tests/integration/phase3/contracts/test_staged_assignment_failure_cases.py::test_continue_route_maps_incomplete_staged_child_assignment_to_illegal_state apps/api/tests/integration/phase3/contracts/test_boundary_precondition_cases.py::test_yield_after_release_green_maps_to_boundary_precondition_failed apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py::test_phase2_minimal_runtime_lane_bootstraps_and_materializes_one_child_path`

## Expected blockers truth

- non-owned direct DB mutation helpers such as `apps/api/tests/integration/phase3/dispatch_support.py` may still exist after this slice because they are outside the allowed write surface
- broader Phase 3 closeout gates such as `make pyright-api`, style audit, full pytest, and Postgres lanes are not part of this narrow repair turn and must stay explicitly unclaimed here
