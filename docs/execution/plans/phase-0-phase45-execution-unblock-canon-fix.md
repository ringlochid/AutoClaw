# Phase 0 Phase 4.5 Execution-Unblock Canon-Fix Plan

Status: Reference

selected phase: Phase 0
current phase page: docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP2, P0-WP3
summary-only: yes
delegated slices: listed
slice id: phase45-docs-execution
slice type: edit
owned surfaces: docs/execution/phases/phase-4.5-session-authority-simplification-and-mcp-runtime-continuity-cleanup.md, docs/execution/maps/file-priority-map.md, docs/execution/maps/redesign-code-landing-map.md, docs/execution/plans/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md, docs/execution/plans/phase-0-to-4.5-make-it-work-master-program.md, docs/execution/evidence/phase-0-to-4.5-make-it-work-master-program.md, docs/execution/reviews/phase-0-to-4.5-make-it-work-master-program.md, docs/execution/plans/phase-0-phase45-execution-unblock-canon-fix.md, docs/execution/evidence/phase-0-phase45-execution-unblock-canon-fix.md, docs/execution/reviews/phase-0-phase45-execution-unblock-canon-fix.md
touched surfaces: docs/execution/phases/phase-4.5-session-authority-simplification-and-mcp-runtime-continuity-cleanup.md, docs/execution/maps/file-priority-map.md, docs/execution/maps/redesign-code-landing-map.md, docs/execution/plans/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md, docs/execution/plans/phase-0-to-4.5-make-it-work-master-program.md, docs/execution/evidence/phase-0-to-4.5-make-it-work-master-program.md, docs/execution/reviews/phase-0-to-4.5-make-it-work-master-program.md, docs/execution/plans/phase-0-phase45-execution-unblock-canon-fix.md, docs/execution/evidence/phase-0-phase45-execution-unblock-canon-fix.md, docs/execution/reviews/phase-0-phase45-execution-unblock-canon-fix.md

## Authoritative replacements

- `../plans/phase-0-phase45-reopen-closure-program.md`

## Historical status

This artifact is a summary-only pre-reopen Phase 0 addendum record. It must
not be used as current Phase 0 or Phase 4.5 closure authority after the Phase 0
reopen triplet landed.

## Purpose

Land the docs-only Phase 0 addendum that unblocks the deletion-heavy Phase 4.5 closure without reopening app code, redesign owner docs, or shipped current-behavior docs in this slice.

## Phase-local role

- `P0-WP2`: make the Phase 4.5 execution contract, wave plan, and strict closeout review shape explicit
- `P0-WP3`: update the lock map, landing map, and execution-record chain so the docs-first unblock step and the Phase 4.5 closure authority are routed cleanly

## Ordered work

1. Create the summary-only master orchestration triplet under `docs/execution/plans/`, `docs/execution/evidence/`, and `docs/execution/reviews/` with `selected phase: none`, `current phase page: none`, `selected work packages: none`, and truthful authoritative replacement links.
2. Create the authoritative Phase 0 addendum triplet under the same record homes with `selected phase: Phase 0`, `summary-only: no`, and explicit pending-proof language.
3. Patch the Phase 4.5 phase page, file lock map, landing map, and authoritative Phase 4.5 plan so Phase 4.5 may delete non-behavioral support-state/readback/prompt-compatibility debt, use test-surface collateral, and reserve the strict closeout review artifact as a single-file edit slice.
4. Line-normalize every touched markdown file and hand off final code-bearing closure authority to the updated Phase 4.5 chain.

## Delegated slice brief

### phase45-docs-execution

- do-not-edit surfaces:
  - `docs/redesign/**`
  - `docs/current/**`
  - `apps/**`
- required reads:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/README.md`
  - `docs/execution/phases/overview.md`
  - `docs/execution/phases/phase-4.5-session-authority-simplification-and-mcp-runtime-continuity-cleanup.md`
  - `docs/execution/maps/file-priority-map.md`
  - `docs/execution/maps/redesign-code-landing-map.md`
  - `docs/execution/plans/phase-0-phase45-simplification-canon-fix.md`
  - `docs/execution/plans/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md`
- required tests/validators:
  - parent-owned after integration: `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
  - parent-owned after later prompt-input changes: `./.venv/bin/python -m scripts.docs.prompt_catalog.cli generate`
  - parent-owned after later prompt-input changes: `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate`
- expected outputs:
  - master-program summary triplet created with truthful `summary-only: yes` grammar
  - Phase 0 addendum triplet created with truthful pending-proof language
  - Phase 4.5 phase page, lock map, landing map, and plan updated to allow deletion-heavy closure work
- dependencies:
  - none
- evidence to return:
  - changed execution-doc inventory
  - exact validator follow-up the parent still owes
- parent-owned decisions:
  - whether later docs waves reopen prompt inputs
  - whether any further canon repair is needed before code work
- stop conditions:
  - stop if the truthful fix requires touching `docs/redesign/**`
  - stop if the truthful fix requires touching `docs/current/**`
  - stop if the truthful fix requires touching `apps/**`

## Validation

- parent-owned after this slice: `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- parent-owned after this slice: `./.venv/bin/python -m scripts.docs.prompt_catalog.cli generate` and `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate` only if later docs waves reopen prompt inputs beyond the `docs/execution/**` work landed here
- parent-owned after this slice: final mandatory review update after validator proof

## Stop conditions

- stop if the truthful fix requires touching `docs/redesign/**`
- stop if the truthful fix requires touching `docs/current/**`
- stop if the truthful fix requires touching app code under `apps/**`

## Cross-links

- summary-only master plan: `../plans/phase-0-to-4.5-make-it-work-master-program.md`
- authoritative Phase 4.5 plan: `../plans/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md`
- predecessor canon-fix plan: `../plans/phase-0-phase45-simplification-canon-fix.md`
