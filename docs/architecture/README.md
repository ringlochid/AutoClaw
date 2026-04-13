# Architecture

These files translate the current AutoClaw V2.1 design bundle into repo-local architecture notes.

Keep them concise and implementation-oriented.
The Notion pages are broader spec/docs; this directory should help contributors build the system.

## Reading order

1. `01-system-overview.md`
2. `02-authoring-compiler-runtime.md`
3. `03-control-plane-and-query-model.md`
4. `04-operator-console-model.md`
5. `05-diagrams-and-mermaid.md`

## File roles

- `01-system-overview.md` — product shape, fit, default runtime path
- `02-authoring-compiler-runtime.md` — authoring surfaces, compiler boundary, plan revision model
- `03-control-plane-and-query-model.md` — storage layers, IDs, query/scheduling split
- `04-operator-console-model.md` — observability and dashboard model
- `05-diagrams-and-mermaid.md` — Mermaid diagrams for the main runtime, storage, patch, and pack flows
