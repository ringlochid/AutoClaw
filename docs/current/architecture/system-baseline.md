# Current system baseline

Status: Current

Last verified: 2026-04-24

AutoClaw is currently a local-first workflow control plane with a FastAPI backend, a deterministic compiler/registry path, a relational runtime model, a bundled operator console, and OpenClaw as the delegated worker transport.

## Current ownership boundary

AutoClaw currently owns:

- workflow, role, policy, and skill registry records
- compile-time workflow resolution
- runtime truth for tasks, task roots, flows, revisions, nodes, attempts, checkpoints, approvals, replans, sessions, context items, and manifests
- operator/API read models
- package-first CLI and bootstrap behavior

OpenClaw currently owns:

- delegated execution
- session-level worker behavior
- plugin/tool execution inside the delegated runtime

## Evidence

Inspected code:

- `autoclaw-main/apps/api/app/api/router.py`
- `autoclaw-main/apps/api/app/db/models/runtime.py`
- `autoclaw-main/apps/api/app/compiler/resolve.py`
- `autoclaw-main/apps/api/app/integrations/openclaw.py`
- `autoclaw-main/apps/api/app/services/openclaw_bridge.py`
- `autoclaw-main/apps/api/app/cli.py`

Inspected tests:

- `autoclaw-main/apps/api/tests/integration/test_runtime_api.py`
- `autoclaw-main/apps/api/tests/unit/test_openclaw_integration.py`

## Current limits

- Current code is still OpenClaw-shaped at the worker boundary.
- Current code still uses `skill_refs` and resolved `skill_bindings`.
- Current code does not yet expose the redesign's explicit provider-preference and capability-envelope model.

## Next read

For current runtime behavior, continue with `runtime-control-plane.md`.
