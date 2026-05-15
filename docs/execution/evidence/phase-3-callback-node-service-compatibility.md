# Phase 3 Callback Node Service Compatibility Evidence

Status: Reference

selected phase: Phase 3
current phase page: docs/execution/phases/phase-3-runtime-parent-review-and-replan.md
selected work packages: P3-WP1, P3-WP2
summary-only: no
delegated slices: none

## Slice identity

- date: 2026-05-14
- slice type: `edit`
- scope: narrow Phase 3 compatibility and regression repair for lifecycle settle semantics, owned helper truth, and the Phase 2 minimal runtime lane

## Plan and review links

- approved plan: `../plans/phase-3-callback-node-service-compatibility.md`
- mandatory review: `../reviews/phase-3-callback-node-service-compatibility.md`
- review artifact: `../reviews/phase-3-callback-node-service-compatibility.md`

## Commands run

- `./.venv/bin/ruff check apps/api/app/runtime/effects/worker.py apps/api/app/runtime/effects/__init__.py apps/api/tests/integration/phase3/runtime_support.py apps/api/tests/integration/phase3/control/test_boundary_cases.py apps/api/tests/integration/phase3/contracts/test_callback_failure_contract_cases.py apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py apps/api/app/cli.py`
  outcome: passed
- `./.venv/bin/mypy apps/api/app/runtime/effects/worker.py apps/api/tests/integration/phase3/runtime_support.py`
  outcome: passed
- `./.venv/bin/pytest -q apps/api/tests/integration/phase3/control/test_boundary_cases.py::test_phase3_boundary_waits_for_inactivity_proof_before_opening_replacement_dispatch apps/api/tests/integration/phase3/control/test_boundary_cases.py::test_phase3_pause_waits_for_inactivity_proof_before_reopening_dispatch apps/api/tests/integration/phase3/contracts/test_callback_failure_contract_cases.py::test_continue_route_maps_incomplete_staged_child_assignment_to_illegal_state apps/api/tests/integration/phase3/contracts/test_callback_failure_contract_cases.py::test_yield_after_release_green_maps_to_boundary_precondition_failed apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py::test_phase2_minimal_runtime_lane_bootstraps_and_materializes_one_child_path`
  outcome: passed (`5 passed in 97.61s`)
- `./.venv/bin/ruff check`
  outcome: passed
- `make typecheck-api`
  outcome: passed
- `make pyright-api`
  outcome: passed
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
  outcome: passed
- `./.venv/bin/pytest -q`
  outcome: passed (`313 passed` in `27:49`)
- `make test-api-db`
  outcome: passed (`311 passed` in `22:52`)

## Scope proved

- task-scoped `wait_for_runtime_effects(...)` now returns only after the task no longer needs foreground lifecycle reconciliation or the caller hits the explicit timeout
- owned helper paths no longer mutate `dispatch.delivery_status` to force continuation flow
- owned closure-path support no longer depends on `cli.cmd_init` or `cli.command_env`
- the Phase 2 minimal runtime lane still exercises two real Gateway `agent` launches across root and child dispatches under the repaired wait semantics

## Search proof

- command: `rg -n "delivery_status = \"provider_completed\"|mark_dispatch_provider_completed|cli\\.(cmd_init|command_env)\\b" apps/api/app/runtime/effects/worker.py apps/api/tests/integration/phase3/runtime_support.py apps/api/tests/integration/phase3/control/test_boundary_cases.py apps/api/tests/integration/phase3/contracts/test_callback_failure_contract_cases.py apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py -S`
  outcome: no matches

## Not run in this slice

- `none`

## Remaining blockers

- residual harness debt only: non-owned helper/test surfaces such as
  `apps/api/tests/integration/phase3/dispatch_support.py` still contain direct
  provider-terminal mutation paths, but they are outside the owned slice and do
  not block this closure chain
