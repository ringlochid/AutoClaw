# Phase 4.5 Authority Collapse And Ballast Deletion Closeout V2 Plan

Status: Reference

selected phase: Phase 4.5
current phase page: docs-internal/execution/v1/phases/phase-4.5-session-authority-simplification-and-mcp-runtime-continuity-cleanup.md
selected work packages: P4.5-WP1, P4.5-WP2, P4.5-WP3, P4.5-WP4, P4.5-WP5, P4.5-WP6
summary-only: no
delegated slices: none

## Purpose

Create the fresh authoritative reopened Phase 4.5 plan artifact after the runtime-normalization Phase 0 canon-fix triplet landed. This plan is the live Phase 4.5 plan authority for the already-started authority-collapse, explicit-arg node-MCP and callback parity, same-session redispatch, prompt cleanup, watchdog narrowing, ballast-deletion, and closeout-proof work.

## Preconditions

- the authoritative Phase 0 runtime-normalization reopen canon-fix triplet is already landed
- the older `phase-4.5-session-authority-simplification-and-runtime-debt-removal.*` triplet stays summary-only historical background
- the worktree is already dirty with in-flight Phase 4.5 app, test, and current-doc edits, so this plan must describe remaining integration and closeout truth without pretending the repo is at a clean pre-implementation baseline

## Current repo state

- runtime, OpenClaw wrapper, and proof-lane edits are already in progress across the owned Phase 4.5 app and test surfaces
- current-doc truth repair is still required on the bridge-facing current boundary page so it teaches the explicit `session_key` + `task_id` callback and `node MCP` contract and demotes `bindings.py` to helper-only narration
- fresh authoritative reopened Phase 4.5 evidence and review artifacts do not exist yet and remain parent-owned follow-on work

## Subagents decision

- delegated slices: none
- this reopened plan does not define a new delegated-slice roster
- parent-owned integration, proof, and closeout work must proceed from the already-dirty tree and later authoritative evidence and review artifacts instead of reviving the historical delegated-slice packet as live authority

## Owned surfaces

- the Phase 4.5 owned and allowed-collateral surfaces named on the selected phase page and in `docs-internal/execution/v1/maps/file-priority-map.md`
- the bridge-facing current contrast page `docs-internal/current/v1/architecture/openclaw-and-bridge-plugin.md`
- this authoritative reopened Phase 4.5 plan artifact
- the reserved follow-on authoritative companion artifact basename `phase-4.5-authority-collapse-and-ballast-deletion-closeout-v2`

## Ordered work

1. Finish the remaining Phase 4.5 current-doc truth cleanup so the bridge-facing current page points at the explicit-arg callback and `node MCP` boundary and no longer teaches `bindings.py` as transport authority.
2. Integrate the already-started `P4.5-WP1` through `P4.5-WP5` runtime, wrapper, prompt, watchdog, and deletion work without reopening Phase 4A or Phase 4B ownership.
3. Run the targeted Phase 4.5 tests and validators that prove the unified authority path, explicit-arg node-MCP and callback parity, same-session redispatch, prompt cleanup, and watchdog narrowing after interface-stable integration.
4. Finish `P4.5-WP6` proof work, including the applicable unit, DB, e2e, and real OpenClaw host lanes required by the selected phase page.
5. Create the fresh authoritative Phase 4.5 evidence artifact using the reserved v2 basename.
6. Create the fresh authoritative Phase 4.5 review artifact using the reserved v2 basename and use the resulting v2 triplet as the only Phase 4.5 closeout authority for the reopened program.

## Expected outputs

- a live authoritative Phase 4.5 plan artifact that matches the reopened runtime-normalization program
- bridge-facing current-doc truth that teaches the explicit-arg callback and `node MCP` boundary and treats `bindings.py` as support glue only
- a clear v2 naming target for the follow-on authoritative Phase 4.5 evidence and review artifacts
- no renewed reliance on the historical summary-only Phase 4.5 plan as live closeout authority

## Validators

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli` when the parent bundles this plan with the follow-on execution-artifact chain or when current-doc and execution-link truth needs immediate proof in one pass

## Stop conditions

- stop if a truthful Phase 4.5 repair now requires edits under `apps/**`
- stop if a truthful repair now requires broader command-surface or Phase 0 canon edits outside the selected Phase 4.5 surfaces
- stop if this slice would need to create the authoritative Phase 4.5 evidence or review artifact instead of only the fresh plan artifact

## Cross-links

- prerequisite authoritative Phase 0 reopen plan: [phase-0-runtime-normalization-reopen-canon-fix](phase-0-runtime-normalization-reopen-canon-fix.md)
- summary-only runtime-normalization program router: [phase-0-to-4.5-runtime-normalization-reopen-program](../../../archive/execution/plans/phase-0-to-4.5-runtime-normalization-reopen-program.md)
- historical summary-only Phase 4.5 plan: [phase-4.5-session-authority-simplification-and-runtime-debt-removal](../../../archive/execution/plans/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md)
