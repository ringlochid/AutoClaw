# Test structure standard

Status: Reference

Use this guide when adding tests, reorganizing test trees, or deciding what counts as acceptable proof for a touched slice.

## Goals

- each lane should prove one clear level of behavior
- shipped persistence and runtime truth should be exercised through shipped paths
- evidence should be easy to audit and hard to fake

## Lane ownership

- `make test-api`: unit behavior under `apps/api/tests/unit`
- `make test-api-integration-local`: repo-native SQLite and runtime-template integration behavior
- `make test-api-db`: Docker/Postgres-backed integration behavior using shipped schema/setup paths
- `make test-api-e2e-minimal|normal|maximal`: progressive end-to-end behavior

## Placement rules

- put pure unit behavior in `apps/api/tests/unit/**`
- put local integration flows in `apps/api/tests/integration/**`
- put end-to-end workflow and public-surface behavior in `apps/api/tests/e2e/**`
- keep reusable helpers under `apps/api/tests/helpers/**` and keep them support-only

## Steady-state test tree

Phase-numbered test trees are transitional only.

The steady-state layout should converge toward feature-, boundary-, or product-owned folders beneath each main lane.

Preferred direction:

```text
apps/api/tests/
  unit/
    cli/
    compiler/
    registry/
    runtime/
    integrations/
    schemas/
  integration/
    api/
    cli/
    db/
    registry/
    runtime/
    integrations/
  e2e/
    workflows/
    gateway/
    operator/
    onboarding/
```

Rules:

- keep the top-level lanes `unit`, `integration`, and `e2e`
- beneath those lanes, prefer product or feature ownership over redesign-phase history
- use provider or integration subfolders only when the external boundary is a real owner surface
- phase history belongs in `docs-internal/execution/v1/**`, not as the long-term primary source of test ownership
- when migrating an old phase-owned test family, keep the new feature-owned location authoritative and reduce the old phase bucket to a temporary bridge

## Proof rules

- do not use mocks as the primary proof for shipped persistence, runtime truth, or public API/CLI behavior
- do not manually install missing schema or synthesize missing setup paths inside tests and then treat that as install or runtime proof
- if the behavior reaches a public route, public CLI noun family, end-to-end workflow, or support-state readback, use the lane that exercises that surface for real
- once a progressive e2e lane becomes viable for a surface, later work should keep it green

## Test authoring rules

- where practical, start with a failing or gap-revealing test
- keep test names aligned with the contract or behavior under proof
- keep fixture setup explicit and narrow
- avoid helper stacks that hide what state or side effect the test is actually proving
- when reorganizing tests, preserve or improve readable progress output

## Runtime wait and timing rules

- use `wait_for_runtime_effects(...)` for post-commit visibility or task-scoped drain only; do not stack it as an outer retry loop when a predicate-driven helper is the real owner
- use `drive_runtime_until(...)` when the proof is waiting for controller-owned runtime state to reach a predicate
- use `drive_watchdog_until(...)` when the proof is waiting for watchdog-owned state to reach a predicate
- shared test contexts and helper stacks must not widen `dispatch_drain_timeout_seconds` broadly by default; keep the fast template baseline and opt specific long-drain tests up locally
- avoid helper loops that combine `for range(...)`, `wait_for_runtime_effects(...)`, `drive_runtime_once(...)`, and fixed sleeps in one stack
- direct sleeps in tests are acceptable only when the boundary is genuinely external or commit-visibility polling cannot yet be expressed through the runtime or watchdog helpers; keep them narrow and explain the reason

## Review checklist

- did the touched slice update the right lane
- if the test tree was reorganized, did it move toward feature/domain ownership rather than deeper phase history
- does the lane exercise the shipped boundary that changed
- did any helper or fixture silently substitute for real runtime or DB behavior
- if a lane was skipped, is the exact reason written down in review or evidence
