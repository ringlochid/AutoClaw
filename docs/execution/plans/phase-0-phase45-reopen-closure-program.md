# Phase 0 Phase 4.5 Reopen Closure Program Plan

Status: Reference

selected phase: Phase 0
current phase page: docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP2, P0-WP3
summary-only: no
delegated slices: none

## Purpose

Reopen the Phase 4.5 closure program in execution canon without reopening
redesign owner docs, current owner docs, app code, or scripts. Retire the
pre-reopen master, Phase 0 addendum, and Phase 4.5 closeout chain as live
authority and make the reopened routing truthful across execution artifacts,
maps, and phase-local docs.

## Owned surfaces

- `docs/execution/plans/**`
- `docs/execution/evidence/**`
- `docs/execution/reviews/**`
- `docs/execution/phases/phase-4.5-session-authority-simplification-and-mcp-runtime-continuity-cleanup.md`
- `docs/execution/maps/file-priority-map.md`
- `docs/execution/maps/redesign-code-landing-map.md`

## Ordered work

1. Create the new summary-only master triplet under
   `phase-0-to-4.5-reopened-closure-program`.
2. Create this authoritative Phase 0 reopen triplet under
   `phase-0-phase45-reopen-closure-program`.
3. Reclassify the pre-reopen `phase-0-to-4.5-make-it-work-master-program.*`,
   `phase-0-phase45-execution-unblock-canon-fix.*`, and
   `phase-4.5-session-authority-simplification-and-runtime-debt-removal.*`
   chains as historical summaries with truthful replacement links.
4. Patch the Phase 4.5 page, file lock map, and landing map so the reopened
   closure program requires a fresh Phase 4.5 triplet before code-bearing work
   resumes.
5. Update the overlapping historical Phase 4A and Phase 4B summary artifacts so
   their replacement links route to current live execution authority without
   reopening Phase 4A transport truth or redesign owner docs.

## Expected outputs

- new summary-only master triplet
- new authoritative Phase 0 reopen triplet
- pre-reopen Phase 0 and Phase 4.5 chains reclassified as historical summaries
- Phase 4A and Phase 4B historical summary artifacts repointed to truthful live
  execution authority
- Phase 4.5 page, file-lock map, and landing-map wording aligned to the
  reopened closure program

## Validators

- parent may run `./.venv/bin/python -m scripts.docs.docs_freeze.cli` after
  integration
- prompt validators are not required unless a later docs wave reopens prompt
  inputs outside `docs/execution/**`

## Stop conditions

- stop if a truthful repair requires touching `docs/redesign/**`
- stop if a truthful repair requires touching `docs/current/**`
- stop if a truthful repair requires touching `apps/**`
- stop if a truthful repair requires touching `scripts/**`

## Cross-links

- summary-only reopened master plan:
  `../plans/phase-0-to-4.5-reopened-closure-program.md`
- pre-reopen master summary:
  `../plans/phase-0-to-4.5-make-it-work-master-program.md`
- pre-reopen Phase 0 addendum:
  `../plans/phase-0-phase45-execution-unblock-canon-fix.md`
- pre-reopen Phase 4.5 closeout:
  `../plans/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md`
