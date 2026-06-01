# Test structure standard

Status: Reference

Use this guide when adding tests, reorganizing test trees, or deciding what
counts as acceptable proof for a touched slice.

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

## Review checklist

- did the touched slice update the right lane
- does the lane exercise the shipped boundary that changed
- did any helper or fixture silently substitute for real runtime or DB behavior
- if a lane was skipped, is the exact reason written down in review or evidence
