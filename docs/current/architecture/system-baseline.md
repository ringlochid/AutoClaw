# Current system baseline

Status: Current

Last verified: 2026-05-12

AutoClaw is currently a local-first workflow control plane with a FastAPI
backend, a registry-backed compiler and launch path, a relational runtime
model, operator API surfaces, and controller-owned OpenClaw-shaped
dispatch/session records.

## Current ownership boundary

AutoClaw currently owns:

- workflow, role, policy, and skill registry records
- compile-time workflow resolution
- runtime truth for tasks, task roots, flows, revisions, nodes, attempts,
  checkpoints, approvals, replans, sessions, context items, and manifests
- operator and API read models
- packaged CLI, service-unit render/install, and bootstrap behavior

OpenClaw currently owns:

- delegated execution outside this repo
- session-level worker behavior on the external worker side
- plugin and tool execution inside the delegated runtime

## Evidence

Inspected code:

- `apps/api/app/api/router.py`
- `apps/api/app/registry/current.py`
- `apps/api/app/compiler/compile.py`
- `apps/api/app/runtime/launch/service.py`
- `apps/api/app/runtime/control/dispatch/opening.py`
- `apps/api/app/api/routes/callback.py`
- `apps/api/app/cli.py`

Inspected tests:

- `apps/api/tests/integration/definition_registry/test_launch_snapshot.py`
- `apps/api/tests/integration/phase2/bootstrap/test_dispatch.py`
- `apps/api/tests/integration/phase3/routes/test_surface_contract.py`

## Current limits

- Current code is still OpenClaw-shaped at the worker boundary.
- Current code still uses `skill_refs` and resolved `skill_bindings`.
- Current repo does not ship the older bundled console or old bridge transport
  modules that older docs used to cite.
- Current code does not yet expose the redesign's explicit
  provider-preference and capability-envelope model.

## Next read

For current runtime behavior, continue with `runtime-control-plane.md`.
