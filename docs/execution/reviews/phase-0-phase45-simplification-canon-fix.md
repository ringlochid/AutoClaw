# Phase 0 Phase 4.5 Simplification Canon-Fix Review

Status: Reference

selected phase: Phase 0
current phase page: docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP2, P0-WP3
summary-only: no
delegated slices: none

## Slice identity

- work package or slice: mandatory review for the Phase 0 Phase 4.5
  simplification canon fix
- date: 2026-05-16

## Phase-local contract

- current phase page: `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`

## Scope

- reviewed plan: `../plans/phase-0-phase45-simplification-canon-fix.md`
- reviewed evidence: `../evidence/phase-0-phase45-simplification-canon-fix.md`

## Verdict

- pass/fail: pass
- summary: the live target canon now routes same-attempt redispatch,
  explicit-arg node authority, watchdog lineage preservation, prompt-layer
  dispatch-local tool context, and historical Phase 4B closeout truth through
  one consistent Phase 0 canon-fix chain.

## Findings

- finding: Phase 4.5 now owns the final authority collapse, prompt
  collateral, and watchdog lineage-preserving narrowing rather than leaving
  those concepts split across older Phase 4A/4B language
- finding: redesign owner docs now treat `same_session_continue`, hidden
  callback-binding authority, and watchdog `create_new_attempt` as
  current/debt compatibility only instead of live target truth
- finding: conflicting old Phase 4B closure artifacts are now historical and
  no longer read as the live target contract

## Delegated-slice compliance

- `no subagents` or delegated-slice summary: `delegated slices: none`
- owned-surface compliance: the docs-only canon fix stayed inside
  `docs/execution/**`, affected `docs/redesign/**`, truthful
  `docs/current/**` contrast repair, and docs-freeze marker collateral
- review-only compliance: not applicable
- wave integration proof: not applicable; no subagents wave ran
- authoritative proof link: `../evidence/phase-0-phase45-simplification-canon-fix.md`

## Proof lanes relied on

- proof lane: `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- proof lane: `./.venv/bin/python -m scripts.docs.prompt_catalog.cli generate`
- proof lane: `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate`

## Stale-logic search proof

- commands or search terms:
  - `rg -n 'same_session_continue|create_new_attempt|session-bound|hidden-binding|DispatchCallbackBindingModel|NodeMcpBinding|previous_response_id|send_mode' docs/redesign docs/execution docs/current`
- outcome:
  - live owner docs now route parent/root continuity through
    `redispatch_same_attempt` plus same-session `full_prompt`
  - watchdog automatic `create_new_attempt` is removed from live target canon
  - static explicit-arg node authority replaces session-bound hidden-binding
    target wording

## Kill-list proof

- phase kill-list source: `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- terms checked:
  - overlapping phase ownership
  - stale historical closure records that still read like live authority
  - prompt/current/target contradictions around same-session redispatch
- outcome:
  - the edited execution pages now state one 4A/4B/4.5 split
  - the conflicting Phase 4B closeout chain is historical only
  - same-session continuity no longer depends on transport-shaped live canon

## Docs answer-sourcing proof

- redesign owners relied on:
  - `docs/redesign/README.md`
  - `docs/redesign/architecture/openclaw-session-lifecycle.md`
  - `docs/redesign/architecture/openclaw-continuity-and-send-modes.md`
  - `docs/redesign/architecture/openclaw-worker-and-gateway-contract.md`
  - `docs/redesign/architecture/runtime-records-and-lifecycle.md`
  - `docs/redesign/architecture/runtime-database-and-object-contract.md`
  - `docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md`
  - `docs/redesign/architecture/watchdog-and-recovery-contract.md`
  - `docs/redesign/interfaces/mcp-plugin-and-cli-boundary.md`
  - `docs/redesign/interfaces/plugin-tool-reference.md`
  - `docs/redesign/interfaces/api-surface-and-trust-lane-map.md`
  - `docs/redesign/prompt-layer/contract.md`
  - `docs/redesign/prompt-layer/source-and-sections.md`
  - `docs/redesign/prompt-layer/render-and-persistence.md`
- supporting redesign reads or appendix owners relied on:
  - `docs/redesign/interfaces/api-schema-appendix.md`
  - `docs/redesign/prompt-layer/machine-contract.md`
  - `docs/redesign/prompt-layer/prompt-catalog.yaml`
  - `docs/redesign/architecture/runtime-observability-and-boundary-log.md`
  - `docs/redesign/architecture/watchdog-and-provider-recovery.md`
- current-contrast pages relied on: none
- code or tests inspected:
  - `apps/api/app/runtime/contract_models/prompt.py`
  - `apps/api/app/runtime/control/dispatch/gateway.py`
  - `apps/api/app/runtime/control/dispatch/gateway_launch_state.py`
  - `apps/api/app/runtime/watchdog/classification.py`
  - `apps/api/app/runtime/watchdog/recovery.py`
  - `apps/api/app/runtime/control/budgets.py`
  - `apps/api/app/db/models/runtime/dispatch/states.py`
  - `apps/api/app/db/models/runtime/dispatch/turns.py`
- canon gap or explicit `none`: none

## Phase-bounded STYLE exceptions

- `none`

## Reset-gate outcome

- not applicable

## Remaining exact blockers

- none

## Cross-links

- aggregate historical summary, if any:
  - `../reviews/phase-4b-session-bound-node-mcp-and-support-state-closeout.md`
  - `../reviews/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md`
- companion exceptions page, if any: none
