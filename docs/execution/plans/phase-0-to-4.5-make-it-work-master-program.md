# Phase 0 To 4.5 Make-It-Work Master Program

Status: Reference

selected phase: none
current phase page: none
selected work packages: none
summary-only: yes
delegated slices: listed
slice id: phase45-docs-execution
slice type: edit
owned surfaces: docs/execution/**, docs/redesign/prompt-layer/**, docs/redesign/prompt-layer/generated/*, docs/redesign/prompt-layer/prompt-catalog.yaml, docs/current/interfaces/api-trust-lanes.md, docs/current/architecture/openclaw-dispatch-and-session-contract.md, docs/current/architecture/runtime-control-plane.md
touched surfaces: docs/execution/**, docs/redesign/prompt-layer/**, docs/redesign/prompt-layer/generated/*, docs/redesign/prompt-layer/prompt-catalog.yaml, docs/current/interfaces/api-trust-lanes.md, docs/current/architecture/openclaw-dispatch-and-session-contract.md, docs/current/architecture/runtime-control-plane.md
slice id: phase45-authority-runtime-db
slice type: edit
owned surfaces: apps/api/app/runtime/**, apps/api/app/db/**, apps/api/app/schemas/**, apps/api/tests/integration/phase3/**, apps/api/tests/integration/phase4a/**, apps/api/tests/integration/runtime_schema_contract/**
touched surfaces: apps/api/app/runtime/**, apps/api/app/db/**, apps/api/app/schemas/**, apps/api/tests/integration/phase3/**, apps/api/tests/integration/phase4a/**, apps/api/tests/integration/runtime_schema_contract/**
slice id: phase45-node-mcp-callback
slice type: edit
owned surfaces: apps/api/autoclaw/openclaw/**, apps/api/app/api/routes/callback.py, apps/api/app/runtime/control/node_operations.py, apps/api/app/runtime/control/dispatch/authority.py, apps/api/tests/integration/phase4b/mcp/**
touched surfaces: apps/api/autoclaw/openclaw/**, apps/api/app/api/routes/callback.py, apps/api/app/runtime/control/node_operations.py, apps/api/app/runtime/control/dispatch/authority.py, apps/api/tests/integration/phase4b/mcp/**, apps/api/tests/e2e/phase4/**, apps/api/tests/helpers/parent_first_lane.py
slice id: phase45-watchdog-observability
slice type: edit
owned surfaces: apps/api/app/runtime/watchdog/**, apps/api/app/runtime/projection/**, apps/api/tests/integration/phase4b/**, apps/api/tests/integration/runtime_schema_contract/**, apps/api/tests/e2e/**
touched surfaces: apps/api/app/runtime/watchdog/**, apps/api/app/runtime/projection/**, apps/api/tests/integration/phase4b/**, apps/api/tests/integration/runtime_schema_contract/**, apps/api/tests/e2e/**
slice id: phase45-prompt-runtime-assets
slice type: edit
owned surfaces: apps/api/app/runtime/prompt/**, apps/api/app/runtime/contract_models/**, apps/api/app/runtime/projection/dispatch/prompt.py, apps/api/app/runtime/task_root/**, apps/api/tests/unit/runtime_prompt_rendering/**, apps/api/tests/integration/phase3/**
touched surfaces: apps/api/app/runtime/prompt/**, apps/api/app/runtime/contract_models/**, apps/api/app/runtime/projection/dispatch/prompt.py, apps/api/app/runtime/task_root/**, apps/api/tests/unit/runtime_prompt_rendering/**, apps/api/tests/integration/phase3/**
slice id: phase45-qa-gate-review
slice type: review-only
owned surfaces: apps/api/**, docs/redesign/**, docs/current/**, docs/execution/evidence/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md
touched surfaces: none
slice id: phase45-strict-closeout-review
slice type: edit
owned surfaces: docs/execution/reviews/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md
touched surfaces: docs/execution/reviews/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md

## Authoritative replacements

- `../plans/phase-0-phase45-execution-unblock-canon-fix.md`
- `../plans/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md`

## Historical status

This artifact is a summary-only cross-phase orchestration record. It must not be used as Phase 0 or Phase 4.5 closure authority. The authoritative closeout chain is the Phase 0 addendum triplet for the docs-first unblock step and the Phase 4.5 triplet for the code-bearing closure.

## Program goal

- land the Phase 0 addendum first so the deletion-heavy Phase 4.5 closure is legal
- land the Phase 4.5 code-bearing closure second as the only final closure phase
- keep the hard target fixed: `NodeSession.session_key` authority, explicit-arg node MCP, same-session `redispatch_same_attempt`, `full_prompt` live behavior, watchdog `redispatch_same_attempt | escalate`, redundant-state deletion, green repo proof, green host OpenClaw proof, and a strict independent closeout review

## Ordered program

1. Land the authoritative Phase 0 addendum chain under `phase-0-phase45-execution-unblock-canon-fix`.
2. Execute the authoritative Phase 4.5 closure chain under `phase-4.5-session-authority-simplification-and-runtime-debt-removal`.

## Dependency-critical path

1. patch canon first
2. land authority collapse before MCP/callback rewrite
3. land explicit-arg node MCP before rewriting stale MCP tests and local host proof config
4. land same-session redispatch before deleting prompt/send-mode continuity plumbing
5. land watchdog narrowing before deleting continuity/support-state fields it still reads
6. rewrite tests and e2e helpers after interfaces stabilize
7. run final expensive proof once at code freeze
8. run strict independent review last

## Wave plan

- Wave 1: `phase45-docs-execution`, `phase45-authority-runtime-db`, `phase45-node-mcp-callback`, and `phase45-watchdog-observability`
- Wave 2: parent integration plus `phase45-prompt-runtime-assets`
- Wave 3: parent targeted proving suite plus `phase45-qa-gate-review`
- Wave 4: parent final expensive proof lanes plus `phase45-strict-closeout-review`

## Closure authority

- the summary-only master triplet is routing context only
- the Phase 0 addendum triplet owns the docs-first unblock step
- the final closure authority remains the Phase 4.5 triplet

## Cross-links

- addendum plan: `../plans/phase-0-phase45-execution-unblock-canon-fix.md`
- Phase 4.5 plan: `../plans/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md`
