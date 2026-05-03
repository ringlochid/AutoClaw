# Documentation Index

Last verified: 2026-04-20

This directory is split into four doc layers:

1. front door docs
2. current status docs
3. reference contracts
4. historical notes

Use the current-status and reference docs first.
Treat historical phase notes as context, not as the default source of truth.

## Start here

- `../README.md` — repo overview and contributor orientation
- `../ROADMAP.md` — short public-facing roadmap
- `roadmap/current.md` — current implementation status and verified baseline
- `refactor-checklist-runtime-stabilization.md` — closure record for the completed runtime-stabilization pass

## Current truth docs

- `api-route-trust-lanes.md` — API trust-lane map and browser bootstrap contract
- `registry-definition-precedence.md` — packaged vs filesystem definition precedence
- `flows/README.md` — index of live runtime flow docs vs reference-only examples
- `architecture/README.md` — runtime/control-plane reference documents
- `decisions/README.md` — ADR index and current decision set

## Roadmap docs

- `roadmap/README.md` — roadmap index and classification
- `roadmap/current.md` — current status, verified baseline, and open work
- `roadmap/backlog.md` — true deferrals only
- `roadmap/next.md` — archived working note; not the current source of truth

## Historical docs

- `roadmap/01-*.md` through `roadmap/13*.md` — phase records and migration history
- `e2e/` — historical end-to-end notes and fixtures
- reference-only flow docs such as `flows/06b-max-complexity-workflow-full.md`

## Documentation standards

- Current-behavior docs should include a `Last verified` date.
- Separate current truth from historical notes explicitly.
- Prefer one doc per contract boundary over large narrative docs that mix status, design, and history.
- Use index docs to route readers to the right source instead of duplicating the same status in many places.
- If a doc is historical, say so near the top.
