# Phase 7 proof pattern, leak cleanup, and test structure convergence

Status: Reference

selected phase: Phase 7
current phase page: docs-internal/execution/v1/phases/phase-7-test-structure-and-proof-convergence.md
selected work packages: P7-WP0, P7-WP1, P7-WP2, P7-WP3, P7-WP4, P7-WP5
summary-only: no
delegated slices: listed
slice id: P7-worker-template
slice type: edit
owned surfaces: bounded subset named by the selected work package
touched surfaces: bounded subset named by the selected work package and the exact allowed collateral named by the Phase 7 page

## Slice identity

- owner: controller parent
- date: 2026-06-05
- work package or slice: full Phase 7 reopen execution brief

## Subagents decision

- delegated slices:
  - `P7-WP0` may stay parent-owned or use one bounded docs worker
  - `P7-WP1` one worker for wait-pattern and timing-default convergence
  - `P7-WP2` one worker for shipped-source leak cleanup
  - `P7-WP3` one worker for shared helper and timing cleanup
  - `P7-WP4` one worker for tree migration and cross-lane import cleanup
  - `P7-WP5` one worker for runner and docs alignment
  - fresh `review-only` slices only after full `P7-WP3` and after final `P7-WP5`

## Delegated slice contract

- slice id: `P7-worker-template`
- slice type: `edit`
- owned surfaces: bounded subset named by the selected work package
- touched surfaces: bounded subset named by the selected work package and the exact allowed collateral named by the Phase 7 page

- do-not-edit surfaces: any source or docs surface outside the selected work package and allowed collateral of the Phase 7 page
- required reads:
  - `AGENTS.md`
  - `STYLE.md`
  - `.agents/standards/README.md`
  - `.agents/standards/structure/test-structure.md`
  - `.agents/standards/structure/repo-layout.md`
  - `.agents/standards/structure/source-layout.md`
  - `.agents/standards/structure/integration-boundaries.md`
  - `.agents/standards/code/naming.md`
  - `docs-internal/execution/v1/README.md`
  - `docs-internal/execution/v1/phases/overview.md`
  - `docs-internal/execution/v1/phases/phase-7-test-structure-and-proof-convergence.md`
  - `docs-internal/execution/v1/maps/file-priority-map.md`
  - the selected Phase 7 plan, evidence, and review artifacts
- expected outputs:
  - changed files list
  - exact leak, wait, or tree-owner issue fixed
  - commands run
  - focused proof results
  - blockers or follow-up debt
- required tests and validators:
  - exact focused pytest selectors for the owned slice
  - `make check-api` and `make pyright-api` when Python source changes
  - exact `style_audit --scan-root <owned path> --fail-on-findings` where viable
  - `./.venv/bin/python -m scripts.docs.docs_freeze.cli` when docs or standards change
- dependencies:
  - `P7-WP0` before any string or wait convergence
  - `P7-WP1` before broad helper or tree migration
- evidence to return:
  - exact searches before and after when leak cleanup is involved
  - exact helper or loop pattern removed when wait cleanup is involved
- parent-owned decisions:
  - legal historical or test-only term exceptions
  - neutral replacement names for persisted metadata
  - final wait-pattern rule
  - phase-close pass or fail
- stop conditions:
  - work escapes the owned slice
  - neutral rename would require external contract or protocol change
  - a required proof lane is failing for reasons outside the slice
  - command-matrix or package-authority changes are needed

## Wave integration rule

- parent no-edit during wave: `yes`
- full-wave wait rule: wait for the full slice result before integrating or patching
- ownership-boundary and slice-type review: required after every wave
- revert rule for out-of-scope or review-only edits: required
- validation and review before next wave: required

## Goal

- phase-local goal:
  - remove execution-roadmap leak language from shipped source
  - converge wait and timing helpers on one explicit proof model
  - then complete tree, runner, and proof-lane convergence

## Phase-local contract

- current phase page: `docs-internal/execution/v1/phases/phase-7-test-structure-and-proof-convergence.md`
- implementation file lock map: `docs-internal/execution/v1/maps/file-priority-map.md`
- required reads completed: `yes`

## Locked surfaces

- owned surfaces:
  - `apps/api/tests/**`
  - `scripts/testing/**`
  - `Makefile` when grouped runners or proof commands need alignment without renaming the public command matrix
  - maintainer or execution docs that describe the proof lanes
  - `apps/api/src/autoclaw/**` when removing shipped-source leak language or converging proof-seam wait ownership without intentional product-behavior change
- allowed collateral surfaces:
  - `docs/**`, `docs-internal/current/v1/**`, `docs-internal/execution/v1/**`, and `scripts/docs/**` when proof-lane routing, docs-freeze rules, or source-side teaching cleanup must stay aligned
  - narrow proof tests under `apps/api/tests/**` when source-side leak cleanup changes locked assertions
- do not edit or defer surfaces:
  - Phase 6 source-tree relayout or package-authority work
  - command-surface renames for the repo-wide test matrix
  - intentional public behavior changes beyond neutral wording, neutral metadata rename, or proof-seam wait cleanup

## Success criteria

- no illegal execution-phase or internal-doc leak strings remain in shipped source surfaces
- wait helpers use the documented steady-state pattern
- broad shared drain-time escalation is removed
- phase-numbered test families are no longer the long-term owner map
- grouped runners preserve coverage and readable progress

## Deliverables and milestones

- deliverables:
  - leak inventory and cleanup
  - wait-pattern target and helper convergence
  - tree, helper, and runner convergence
- milestones:
  - `P7-WP0` inventory lock
  - `P7-WP1` wait-pattern lock
  - `P7-WP2` shipped-source leak cleanup
  - `P7-WP3` helper cleanup and first review gate
  - `P7-WP4` test-owner migration
  - `P7-WP5` runner/docs alignment and final review gate

## Ordered work packages

- `P7-WP0` leak inventory and target lock
- `P7-WP1` wait-pattern and timing-default convergence
- `P7-WP2` shipped-source leak cleanup
- `P7-WP3` shared helper and timing cleanup
- `P7-WP4` tree migration and cross-lane import cleanup
- `P7-WP5` runner, docs, and final proof alignment

## Validation checkpoints

- checkpoint 1: searches prove the frozen leak set and legal exceptions
- checkpoint 2: wait-pattern docs and helper ownership agree
- checkpoint 3: shipped-source strings and default metadata are neutralized
- checkpoint 4: helper stacks no longer rely on redundant sleep and retry loops
- checkpoint 5: phase-numbered tree ownership is no longer primary
- checkpoint 6: grouped runners and docs match the final tree

## Required tests and validators

- `make check-api`
- `make pyright-api`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
- exact focused pytest selectors while iterating
- `make test-api`
- `make test-api-integration-local`
- `make test-api-db`
- all viable `make test-api-e2e-*` lanes
- `ruff check scripts/docs` and `mypy scripts/docs` when `scripts/docs/**` changes
- `./.venv/bin/python -m scripts.docs.docs_freeze.cli` when docs or standards change

## Required docs and examples

- Phase 7 phase page
- implementation file lock map
- testing and release checklist
- runtime lifecycle overview
- workflow lane matrix and minimal, normal, maximal examples

## Exit evidence

- evidence expected under `../evidence/`:
  - `phase-7-proof-pattern-and-leak-cleanup.md`

## Rollback or stop conditions

- stop conditions:
  - a leak rename requires external protocol or migration semantics beyond Phase 7
  - a wait-pattern change needs a behavior contract decision not covered by current canon
  - public command-matrix changes are required

## Cross-links

- evidence artifact:
  - `docs-internal/execution/v1/evidence/phase-7-proof-pattern-and-leak-cleanup.md`
- review artifact:
  - `docs-internal/execution/v1/reviews/phase-7-proof-pattern-and-leak-cleanup.md`
