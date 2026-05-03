# Roadmap Index

Last verified: 2026-04-20

This folder is the implementation planning surface for AutoClaw.
It now separates current truth from historical phase records more explicitly.

## Start here

- `current.md` — current implementation status and verified baseline
- `00-principles.md` — cross-phase invariants
- `../refactor-checklist-runtime-stabilization.md` — closure record for the finished runtime-stabilization pass

## Historical phase records

These documents remain useful for migration context, but they are not the default source of truth for the current repo state.

- `01-phase-1-kernel-and-data-model.md`
- `02-phase-2-registry-and-compiler.md`
- `03-phase-3-runtime-and-openclaw-integration.md`
- `04-phase-4-operator-console.md`
- `05-phase-5-replan-watchdog-and-approval.md`
- `06-phase-6-advanced-hierarchy-and-packs.md`
- `06.5-phase-6.5-pre-phase-7-stabilization.md`
- `07-phase-7-controller-driven-looping-and-governance.md`
- `08-phase-8-production-openclaw-bridge-and-native-plugin-adapter.md`
- `09-phase-9-local-first-packaging-and-distribution.md`
- `10-phase-10-effective-node-compiler-semantics-and-authoring-safety.md`
- `11-phase-11-graph-operator-surfaces-and-definition-authoring.md`
- `12-phase-12-openclaw-operator-plugin-and-definition-automation.md`
- `13-phase-13-task-compose-launch-refactor-and-runtime-cleanup.md`
- `13-phase-13a-runtime-bundle-removal-and-persistence-truth.md`
- `13-phase-13b-task-compose-launch-refactor.md`
- `13-phase-13c-runtime-truth-policy-replan-and-verification.md`

## Working notes

- `backlog.md` — true deferrals only
- `next.md` — archived working note retained for context
- `suggestion.md` — engineering style and verification guidance

## Rules for this folder

- `current.md` is the current-status entry point.
- Historical phase docs should keep their historical framing explicit.
- `backlog.md` is for genuine deferrals, not active migration work.
- If a phase is no longer the active owner of unfinished work, `current.md` should say where that work moved.
