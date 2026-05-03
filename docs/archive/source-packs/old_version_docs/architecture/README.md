# Architecture Index

Last verified: 2026-04-20

This folder holds the reference contracts for the AutoClaw control plane.
Use these docs when you need the intended boundary or canonical model, not just a current-status summary.

## Read in this order

- `01-system-overview.md` — top-level runtime identity and control boundaries
- `02-authoring-compiler-runtime.md` — authoring, compiler, and runtime boundary model
- `03-control-plane-and-query-model.md` — persistent/runtime data model and query contract
- `04-operator-console-model.md` — operator surface model
- `05-diagrams-and-mermaid.md` — diagrams and Mermaid-ready summaries
- `06-openclaw-runtime-bridge.md` — OpenClaw bridge contract and caveats

## Guidance

- Treat these docs as reference contracts, not as sprint plans.
- If a document says it is draft or partially stale, prefer `../../../../roadmap/current.md` plus the narrower current contract docs for the live-state read.
- If current code and a reference doc disagree in a touched area, update the doc in the same change.
