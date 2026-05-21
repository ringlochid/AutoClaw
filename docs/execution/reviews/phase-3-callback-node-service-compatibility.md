# Phase 3 Callback Node Service Compatibility Review

Status: Reference

selected phase: Phase 3
current phase page: docs/execution/phases/phase-3-runtime-parent-review-and-replan.md
selected work packages: P3-WP1, P3-WP2
summary-only: no
delegated slices: none

## Slice identity

- work package or slice: narrow Phase 3 compatibility and regression repair for lifecycle settle semantics, owned helper truth, and the Phase 2 minimal runtime lane
- date: 2026-05-14

## Phase-local contract

- current phase page: `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`

## Scope

- reviewed plan: `../plans/phase-3-callback-node-service-compatibility.md`
- reviewed evidence: `../evidence/phase-3-callback-node-service-compatibility.md`

## Findings

1. Medium: direct DB mutation still exists in non-owned Phase 3 helper and test surfaces such as `apps/api/tests/integration/phase3/dispatch_support.py`, so the broader harness still has hidden provider-terminal shortcuts outside this slice.
2. Low: the final closure claim depends on the later broad-gate reruns recorded below, not on the original narrow slice alone.
3. Low: `apps/api/app/cli.py` remains dirty in the worktree, but the owned closure path no longer depends on its public alias drift because `runtime_support.py` now uses the existing test-only `_cmd_init` and `_command_env` entrypoints.

## Verdict

- pass/fail: pass
- summary: the selected Phase 3 compatibility repair is now closeable. The semantic-settle waiting fix is landed, `/callback` stays transport-thin over the shared node-operation seam, and the previously missing broad closure gates are green.

## Scope reviewed

- `apps/api/app/runtime/effects/worker.py`
- `apps/api/tests/integration/phase3/runtime_support.py`
- `apps/api/tests/integration/phase3/contracts/test_callback_failure_contract_cases.py`
- `apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py`
- `docs/execution/plans/phase-3-callback-node-service-compatibility.md`
- `docs/execution/evidence/phase-3-callback-node-service-compatibility.md`
- `docs/execution/reviews/phase-3-callback-node-service-compatibility.md`

## Delegated-slice compliance

- `no subagents` or delegated-slice summary: none; this narrow follow-up was integrated as a parent-owned repair patch
- owned-surface compliance: pass for the listed Phase 3 runtime, helper, test, and artifact surfaces
- review-only compliance: not applicable
- wave integration proof: parent reran the narrow validation bundle after the helper/test repair and updated the matching Phase 3 evidence
- authoritative proof link: `../evidence/phase-3-callback-node-service-compatibility.md`

## Proof lanes relied on

- `./.venv/bin/ruff check apps/api/app/runtime/effects/worker.py apps/api/app/runtime/effects/__init__.py apps/api/tests/integration/phase3/runtime_support.py apps/api/tests/integration/phase3/control/test_boundary_cases.py apps/api/tests/integration/phase3/contracts/test_callback_failure_contract_cases.py apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py apps/api/app/cli.py`
- `./.venv/bin/mypy apps/api/app/runtime/effects/worker.py apps/api/tests/integration/phase3/runtime_support.py`
- `./.venv/bin/pytest -q apps/api/tests/integration/phase3/control/test_boundary_cases.py::test_phase3_boundary_waits_for_inactivity_proof_before_opening_replacement_dispatch apps/api/tests/integration/phase3/control/test_boundary_cases.py::test_phase3_pause_waits_for_inactivity_proof_before_reopening_dispatch apps/api/tests/integration/phase3/contracts/test_callback_failure_contract_cases.py::test_continue_route_maps_incomplete_staged_child_assignment_to_illegal_state apps/api/tests/integration/phase3/contracts/test_callback_failure_contract_cases.py::test_yield_after_release_green_maps_to_boundary_precondition_failed apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py::test_phase2_minimal_runtime_lane_bootstraps_and_materializes_one_child_path`
- full local `pytest` (`313 passed`) as the broader SQLite proof lane for the final repaired branch state
- `make test-api-db` (`311 passed`) as the broader Postgres strong-lane proof for the final repaired branch state
- `rg -n "delivery_status = \"provider_completed\"|mark_dispatch_provider_completed|cli\\.(cmd_init|command_env)\\b" apps/api/app/runtime/effects/worker.py apps/api/tests/integration/phase3/runtime_support.py apps/api/tests/integration/phase3/control/test_boundary_cases.py apps/api/tests/integration/phase3/contracts/test_callback_failure_contract_cases.py apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py -S`
- style-audit inventory on the final branch state: oversized files `0`, oversized functions `0`, cross-module underscore imports `0`

## Stale-logic search proof

- commands or search terms: `delivery_status = "provider_completed"`, `mark_dispatch_provider_completed`, and closure-path `cli.(cmd_init|command_env)` usage across the owned helper/test seam
- outcome: the owned helper and minimal e2e closure path no longer force provider-terminal truth through direct DB mutation or Phase 5A CLI alias dependence

## Kill-list proof

- phase kill-list source: `docs/execution/phases/phase-3-runtime-parent-review-and-replan.md`
- terms checked: thin callback compatibility, no hidden helper-only authority, no later-phase closure dependence on public CLI drift
- outcome: satisfied for this narrow repair slice; broader non-owned helper/test mutation remains outside the selected closure authority and does not affect the selected proof lanes

## Docs answer-sourcing proof

- redesign owners relied on: `docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md` and `docs/redesign/workflows/parent-root-release-and-closure.md`
- supporting redesign reads or appendix owners relied on: none beyond the phase-required reads for this narrow repair
- current-contrast pages relied on: `docs/current/interfaces/api-surface-and-route-map.md` and `docs/current/interfaces/api-trust-lanes.md`
- code or tests inspected: `worker.py`, `runtime_support.py`, the owned Phase 3 contract/control tests, and the Phase 2 minimal runtime lane
- canon gap or explicit `none`: none inside the owned slice

## Private-symbol search proof

- exact repo search used the `rg -n "delivery_status = \"provider_completed\"|mark_dispatch_provider_completed|cli\\.(cmd_init|command_env)\\b"` lane above to confirm the owned closure path no longer depends on the public `cli.py` aliases and no new underscore-private shared helper drift was introduced inside the owned slice

## Change summary

- `wait_for_runtime_effects(task_id=...)` now waits for semantic settle instead of one unchanged pending cycle
- owned helper and e2e paths now use the real Gateway-backed settle path rather than forcing `provider_completed`
- the owned closure path no longer needs the public `cli.py` aliases

## Phase-bounded STYLE exceptions

- `none`

## Reset-gate outcome

- not applicable for this narrow repair slice

## Remaining exact blockers

- none

## Cross-links

- aggregate historical summary, if any: none
- companion exceptions page, if any: none
