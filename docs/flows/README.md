# Flow Docs Index

Last verified: 2026-04-20

Use this folder for runtime and lifecycle examples.
The files are split into current-baseline docs vs reference-only examples.

## Current-baseline flow docs

- `00-data-example.md` — quick runtime snapshot for orientation
- `01-definition-to-runtime.md` — compile-to-runtime path
- `02-default-runtime-lifecycle.md` — current controller/runtime lifecycle
- `03-plan-patch-and-safe-recompile.md` — current replan/adopt behavior
- `04-approval-and-watchdog.md` — current approval and watchdog semantics
- `05-mvp-builder-pack.md` — practical starter graph
- `06-max-complexity-workflow.md` — compact operator-facing summary of the supported complex flow

## Reference-only docs

- `06b-max-complexity-workflow-full.md` — exact/reference target render, not the default current-status read
- `07-controller-driven-implementation-loop.md` — next-stage or target-state note retained for context

## API surface note

- `/flows/{flow_id}/operator` is the compact operator summary view
- `/internal/flows/{flow_id}/audit` is the full audit/debug payload
- worker callback and low-level control paths intentionally live under `/internal/...`

## When to read architecture docs instead

If you need the contract rather than an example, use:

- `../architecture/README.md`
- `../api-route-trust-lanes.md`
- `../registry-definition-precedence.md`
