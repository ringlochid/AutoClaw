# Phase 0 Phase 4.5 Simplification Canon-Fix Plan

Status: Reference

selected phase: Phase 0
current phase page: docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP2, P0-WP3
summary-only: no
delegated slices: none

## Purpose

Land one docs-only canon-fix that removes the remaining Phase 4.5 target
contradictions across execution docs, redesign owner docs, prompt-layer owner
docs, and the conflicting historical Phase 4B closure chain.

This slice exists to:

- make Phase 4.5 the single live target for simplified authority,
  parent/root same-attempt redispatch, static explicit-arg `node MCP`, and
  lineage-preserving watchdog recovery
- narrow or remove stale runtime/watchdog field families from live target canon
- keep `docs/current/**` truthful as shipped contrast without letting it
  redefine target truth
- reclassify older conflicting Phase 4B closure artifacts as historical

Concrete debt families to remove or narrow in canon:

- `DispatchTurn.phase` and `DISPATCH_PHASE_VALUES`
- `DispatchTurn.status` as a lifecycle shadow over stronger delivery/control truth
- `DispatchTurn.staged_continuation_kind` when `staged_child_assignment_id`
  already defines the live continuation basis
- persisted `send_mode` on `DispatchTurn` and `DispatchDeliveryState`
- `DispatchDeliveryState.controller_observation_state` as projection-only
  ballast rather than live target behavior truth
- `DispatchContinuityState.previous_response_id`
- broad `DispatchContinuityState.continuity_state` transport-catalog semantics
- `DISPATCH_OBSERVATION_STATE_VALUES`, especially
  `boundary_accepted_waiting_terminal`, as a target-facing field family
- `DispatchCallbackBindingModel`
- `NodeMcpBinding`
- schema/test/support ballast that freezes the old hidden-binding authority
  model as contract truth

## Owned surfaces

- affected execution pages under `docs/execution/**`
- affected redesign owner docs under `docs/redesign/**`
- affected current-contrast docs under `docs/current/**`
- docs-freeze marker surfaces under `scripts/docs/docs_freeze/**` when needed
  for truthful redesign routing

## Ordered work

1. Re-lock the execution pack and file-lock map around the real 4A/4B/4.5
   split.
2. Rewrite runtime/interface/watchdog owner docs to one simplified target.
   This includes explicitly demoting or removing stale field families such as
   dispatch `phase`, dispatch `status`, `staged_continuation_kind`,
   persisted `send_mode`, broad continuity-state catalogs,
   duplicated support-state observation fields, and callback-binding authority
   rows from live target canon.
3. Patch prompt-layer owner and generated-reference docs so explicit node-tool
   context is teachable and `same_session_continue` survives only as
   current/debt compatibility.
4. Reclassify conflicting Phase 4B plan/evidence/review artifacts as
   historical and point them at this Phase 0 canon-fix chain.

## Validation

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli generate`
- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate`
- contradiction grep over touched docs for:
  - live `same_session_continue`
  - watchdog `create_new_attempt`
  - hidden callback-binding authority
  - session-bound target node-MCP wording
  - dispatch `phase` or support `send_mode` treated as meaningful live target
    runtime behavior
  - dispatch `status`, `staged_continuation_kind`, or support-only
    `controller_observation_state` treated as behavior-defining target truth

## Stop conditions

- stop if the truthful fix requires repo code under `apps/**`
- stop if the truthful fix requires changing shipped current behavior rather
  than contrast wording
