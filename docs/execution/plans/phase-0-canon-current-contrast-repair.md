# Phase 0 Canon and Current-Contrast Repair

Status: Reference

## Slice identity

- selected phase: Phase 0
- work package or slice: canon, current-contrast, validator, and closeout-summary repair
- owner: Codex
- date: 2026-05-05

## Delegated slices and return contract

- delegated slices:
  - execution canon and lock-map repair
    - slice type: `edit`
    - owned surfaces: `docs/execution/README.md`, `docs/execution/gates/phase-implementation-prompts.md`, `docs/execution/gates/supporting-prompts.md`, `docs/execution/plans/phase-plan-template.md`, `docs/execution/gates/mandatory-review-gate.md`, `docs/execution/gates/phase-done-gate.md`
    - do-not-edit surfaces: `scripts/docs/*`, `docs/current/**`, runtime or compiler code, and phase-scoped Phase 0 artifacts
    - required reads: `AGENTS.md`, `STYLE.md`, `docs/execution/README.md`, `docs/execution/phases/overview.md`, `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`, `docs/execution/maps/file-priority-map.md`, `docs/execution/maps/redesign-code-landing-map.md`
    - expected outputs: single-phase authority wording aligned across reusable prompts, templates, and gates; reusable subagent standard aligned to `AGENTS.md`
    - required validators/tests: parent-rerun Phase 0 docs gates after integration
    - dependencies: none
    - evidence to return: exact wording changed, owned surfaces touched, and residual concerns
    - parent-owned decisions: final wording arbitration if multiple execution surfaces compete
    - stop conditions: stop and report if a needed edit falls outside owned surfaces
  - current seed-authority doc repair
    - slice type: `edit`
    - owned surfaces: `docs/current/interfaces/definition-precedence-and-skill-version-defaults.md`, `docs/current/interfaces/definitions-compiler-and-launch.md`, `docs/current/interfaces/definition-registry-and-publish-lifecycle.md`
    - do-not-edit surfaces: runtime code, validator code, execution surfaces, and other `docs/current/**`
    - required reads: the Phase 0 page, the three named current pages, and the matching shipped seed behavior
    - expected outputs: shipped seed-authority and reseed-semantics wording aligned to current code
    - required validators/tests: parent-rerun `python scripts/docs/docs_freeze_validate.py`
    - dependencies: execution canon and lock-map repair
    - evidence to return: exact contrast bullets changed and validator expectation
    - parent-owned decisions: whether any additional current-doc unlock is needed
    - stop conditions: stop and report if any current doc outside the explicit Phase 0 unlock list must change
  - current runtime-control doc repair
    - slice type: `edit`
    - owned surfaces: `docs/current/architecture/runtime-control-plane.md`
    - do-not-edit surfaces: runtime code, execution gates/templates, validator code, and any other current docs
    - required reads: the Phase 0 page, the current runtime-control page, `docs/redesign/architecture/runtime-records-and-lifecycle.md`, `apps/api/app/db/models/runtime/shared.py`, and the Phase 3 control-state test
    - expected outputs: cancel and waiting or drain wording aligned to shipped control-state and observation semantics
    - required validators/tests: parent-rerun `python scripts/docs/docs_freeze_validate.py`
    - dependencies: execution canon and lock-map repair
    - evidence to return: exact bullets changed and any neighboring wording adjusted
    - parent-owned decisions: final wording arbitration if current vs redesign wording differs
    - stop conditions: stop and report if another current doc outside the explicit Phase 0 unlock list appears necessary
  - docs validator hardening
    - slice type: `edit`
    - owned surfaces: `scripts/docs/docs_freeze_validate.py`
    - do-not-edit surfaces: `AGENTS.md`, execution docs, current docs, runtime code, and tests
    - required reads: the Phase 0 page, `STYLE.md`, the current validator marker tables, `phase-implementation-prompts.md`, and `runtime-control-plane.md`
    - expected outputs: required and forbidden marker checks for Phase 0 authority wording and stale waiting/control-state wording
    - required validators/tests: `./.venv/bin/ruff check scripts/docs`, `./.venv/bin/mypy scripts/docs`, `./.venv/bin/python scripts/docs/docs_freeze_validate.py`
    - dependencies: authority wording and current-doc wording from sibling edit slices
    - evidence to return: exact marker tables/functions changed and command outcomes
    - parent-owned decisions: resolving any canon ambiguity beyond marker enforcement
    - stop conditions: stop and report if the fix needs doc edits instead of validator changes
  - aggregate closeout-summary normalization
    - slice type: `review-only`
    - owned surfaces: none
    - do-not-edit surfaces: all files
    - required reads: `AGENTS.md`, `STYLE.md`, `docs/execution/gates/mandatory-review-gate.md`, and the authoritative Phase 0 plan/evidence/review artifacts plus `phase-0-3-closeout-review-exceptions.md`
    - expected outputs: exact artifact additions needed for delegated-slice compliance and authoritative STYLE exception placement
    - required validators/tests: none
    - dependencies: sibling edit slices for the new AGENTS/gate/current-doc/validator wording
    - evidence to return: exact file or section references, authoritative exception wording, and a concise keep/fix checklist
    - parent-owned decisions: actual artifact edits and final review verdict
    - stop conditions: review only; do not edit or revert anything

## Wave integration rule

- the parent waits for the full delegated wave before integrating
- the parent does no repo-tracked-file edits while the wave is running
- the parent reviews every returned diff against owned surfaces and slice type
- the parent reverts any out-of-scope edits and any edits produced by review-only slices before integration
- the parent integrates, reruns validators, patches exact post-wave findings, and only then records evidence and review

## Goal

- make the docs, gates, execution-pack wording, current-contrast pages, and
  docs validator trustworthy enough that later Phase 1-3 work can be planned
  and closed against real canon

## Phase-local contract

- current phase page: `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`
- required reads completed: yes

## Locked surfaces

- owned surfaces: `AGENTS.md`, `STYLE.md`, `docs/README.md`, `docs/execution/**`, `scripts/docs/*`
- allowed collateral surfaces: `docs/redesign/prompt-layer/*`, `README.md`, `docs/current/interfaces/definition-precedence-and-skill-version-defaults.md`, `docs/current/interfaces/definitions-compiler-and-launch.md`, `docs/current/interfaces/definition-registry-and-publish-lifecycle.md`, `docs/current/architecture/runtime-control-plane.md`
- do not edit or defer surfaces: repo code, registry/runtime/compiler implementation, and `docs/current/**` beyond the four explicit unlock pages above

## Success criteria

- one selected phase per authoritative plan, evidence, and review artifact is explicit canon
- the four named current-contrast pages match shipped seed and cancel behavior
- `docs_freeze_validate.py` contains explicit assertions for those pages
- `phase-0-3-closeout*` is summary-only and no longer claims authoritative pass
- delegated-slice and per-wave evidence requirements are explicit

## Deliverables and milestones

- deliverables:
  - corrected execution-pack canon
  - corrected current-contrast pages
  - hardened docs validator
  - normalized aggregate closeout-summary artifacts
  - Phase 0-scoped plan, evidence, and review artifacts
- milestones:
  - execution canon aligned
  - current docs aligned
  - validator green
  - closeout summary demoted
  - Phase 0 review passed

## Ordered work packages

- `P0-WP1`: execution canon and lock-map repair
- `P0-WP2`: current seed-authority and cancel-behavior doc repair
- `P0-WP3`: explicit validator assertions for the named current docs and closeout summaries
- `P0-WP4`: aggregate closeout-summary normalization
- `P0-WP5`: Phase 0 evidence and mandatory review

## Validation checkpoints

- docs freeze validator passes with explicit current-doc assertions
- `ruff check scripts/docs` passes
- `mypy scripts/docs` passes
- aggregate closeout summaries no longer satisfy closure authority

## Required tests and validators

- `./.venv/bin/python scripts/docs/docs_freeze_validate.py`
- `./.venv/bin/python scripts/docs/prompt_catalog_tools.py validate` when prompt-layer owner or generated prompt surfaces move
- `./.venv/bin/ruff check scripts/docs`
- `./.venv/bin/mypy scripts/docs`

## Required docs and examples

- execution pack routers, gate pages, maps, and the Phase 0 page
- `docs/current/interfaces/definition-precedence-and-skill-version-defaults.md`
- `docs/current/interfaces/definitions-compiler-and-launch.md`
- `docs/current/interfaces/definition-registry-and-publish-lifecycle.md`
- `docs/current/architecture/runtime-control-plane.md`
- aggregate `phase-0-3-closeout*` artifacts

## Exit evidence

- evidence artifact: `../evidence/phase-0-canon-current-contrast-repair.md`

## Rollback or stop conditions

- stop if any additional `docs/current/**` page must change without canon unlock
- stop if a needed fix requires changing runtime/compiler/registry code to make docs true
- stop if prompt-layer wording would imply live runtime behavior changes instead of documentation repair

## Cross-links

- evidence artifact: `../evidence/phase-0-canon-current-contrast-repair.md`
- review artifact: `../reviews/phase-0-canon-current-contrast-repair.md`
