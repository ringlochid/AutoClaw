# Flows

Concrete examples for AutoClaw runtime behavior.

## Flow index and role

- **Current baseline**
  - `00-data-example.md` — baseline runtime snapshot for quick orientation
  - `01-definition-to-runtime.md` — baseline compile-to-runtime path
  - `02-default-runtime-lifecycle.md` — current baseline lifecycle
  - `03-plan-patch-and-safe-recompile.md` — current baseline replan patch flow
  - `04-approval-and-watchdog.md` — current baseline approval/watchdog semantics
  - `05-mvp-builder-pack.md` — current baseline starter graph example
  - `06-max-complexity-workflow.md` — current baseline full-surface flow example

- **Target/reference artifacts**
  - `06b-max-complexity-workflow-full.md` — reference render of max-complexity behavior

- **Next-stage (Phase 7) notes**
  - `07-controller-driven-implementation-loop.md` — next-stage target for gated controller progression

The index is intentionally split by implementation stage so you can distinguish what is live now from what is proposed.

## Live API surface note

- `/flows/{flow_id}/operator` is the compact operator summary view.
- `/internal/flows/{flow_id}/audit` is the full audit/debug payload.
- the console should use the operator surface by default; audit/debug access is intentionally separate.
- low-level control endpoints such as checkpoint writes, manifest ack, watchdog, compiler/bootstrap, and internal approval creation live under `/internal/...` on purpose.

For Mermaid summaries, see `../architecture/05-diagrams-and-mermaid.md`.
