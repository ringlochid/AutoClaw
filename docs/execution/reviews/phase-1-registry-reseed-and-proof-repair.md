# Phase 1 Registry Reseed and Shipped-Path Proof Repair Review

Status: Reference

selected phase: Phase 1
current phase page: docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md
selected work packages: P1-WP1, P1-WP2, P1-WP3
summary-only: no
delegated slices: listed
slice id: registry-suite-narrowing
slice type: edit
owned surfaces: apps/api/tests/integration/test_definition_registry_db.py
touched surfaces: apps/api/tests/integration/test_definition_registry_db.py
slice id: dotted-id-opacity-regression
slice type: edit
owned surfaces: apps/api/tests/unit/test_workflow_compiler.py
touched surfaces: apps/api/tests/unit/test_workflow_compiler.py
slice id: phase-1-gate-audit
slice type: review-only
owned surfaces: none
touched surfaces: none

## Slice identity

- selected phase: Phase 1
- work package or slice: authoritative review refresh for `P1-WP1`, `P1-WP2`, and `P1-WP3`
- review scope: registry reseed semantics, registry-backed schema parity,
  compiler dotted-id opacity, and shipped-path `init` / `db upgrade` /
  `db reset` proof
- artifact-rescope scope: correct the authoritative review wording so it
  matches the landed slice instead of a generic documentation-refresh frame
- date: 2026-05-06

## Phase-local contract

- current phase page: `docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`

## Scope

- reviewed plan: `../plans/phase-1-registry-reseed-and-proof-repair.md`
- reviewed evidence: `../evidence/phase-1-registry-reseed-and-proof-repair.md`

## Verdict

- pass/fail: pass
- summary: the authoritative Phase 1 review now matches the landed
  `P1-WP1`..`P1-WP3` slice. Registry reseed/currentness and shipped-path proof
  remain validated, compiler dotted-id opacity remains validated, and
  schema-parity claims are limited to the behaviors exercised by the retained
  tests rather than overstating full Phase 1 schema completeness.

## Findings

- `P1-WP1`: stable seed-source identity, append-or-reuse immutable revision
  behavior, currentness-preserving reseed semantics, and the shipped-path
  SQLite `init`, `db upgrade`, and `db reset` proof remain the validated Phase
  1 registry truth in the evidence artifact.
- `P1-WP2`: the retained schema-parity proof is limited to the
  registry-backed validation and revision-pinning behavior exercised in
  `test_definition_registry_db.py` and `test_registry_seed_authority.py`.
  This review does not claim exhaustive workflow, role, or policy schema
  completeness beyond that coverage.
- `P1-WP3`: dotted node ids remain directly covered as opaque strings in the
  compiler unit suite, and the focused compiler lane reran at `10 passed`.
- Ownership containment is restored in the authoritative Phase 1 closure
  artifact set because the removed runtime bootstrap/control proofs no longer
  reappear as Phase 1 evidence.
- Broader docs, lint, type, and Postgres or Docker proof lanes are relied on
  only as recorded in the evidence artifact; they support closure without
  expanding this review into `P1-WP4` or later-phase ownership.

## Delegated-slice compliance

- delegated-wave summary:
  - the underlying implementation used two `edit` slices on the owned test
    files plus one `review-only` audit slice, and this artifact rescope did
    not add a new delegated wave
- owned-surface compliance:
  - the `edit` slices stayed inside their single owned test files, and this
    artifact repair stayed inside the two owned execution-record files
- review-only compliance:
  - the `phase-1-gate-audit` slice returned no edits
- wave integration proof:
  - the parent waited for the full delegated wave, reviewed ownership
    boundaries, integrated the kept diffs, and relied on the focused proof
    reruns and broader carried-forward lanes recorded in the evidence artifact
- authoritative proof link:
  - `../evidence/phase-1-registry-reseed-and-proof-repair.md`

## Proof lanes relied on

- proof lane:
  - `./.venv/bin/pytest -q apps/api/tests/unit/test_workflow_compiler.py` ->
    `10 passed in 0.25s` on 2026-05-06
- proof lane:
  - `./.venv/bin/pytest -q apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/integration/test_registry_seed_authority.py apps/api/tests/integration/test_db_reset_db.py apps/api/tests/unit/test_cli.py` ->
    `17 passed in 21.53s` on 2026-05-06
- proof lane:
  - `./.venv/bin/pytest --collect-only -q apps/api/tests/integration/test_definition_registry_db.py apps/api/tests/integration/test_registry_seed_authority.py apps/api/tests/integration/test_db_reset_db.py apps/api/tests/unit/test_cli.py` ->
    `17 tests collected`, confirming the current aggregate count
- proof lane:
  - broader gates and strong-verification lanes are relied on only as recorded
    in `../evidence/phase-1-registry-reseed-and-proof-repair.md`, including
    `ruff format --check`, `ruff check`, `mypy`, `make pyright-api`,
    `./.venv/bin/python scripts/docs/docs_freeze_validate.py`, and
    `make test-api-db`

## Stale-logic search proof

- commands or search terms:
  - `rg -n 'authored \`edges\`|dotted-id parent inference|generic authored \`skill_refs\`|obsolete flat flagship workflow teaching model|top-level \`skill_refs\`|node-level \`skill_refs\`|flat \`skill_refs\`-driven authoring' docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md docs/redesign/workflows/workflow-definition-schema.md docs/redesign/workflows/workflow-schema-appendix.md docs/current/interfaces/definition-and-task-compose-yaml-contract.md docs/current/interfaces/definitions-compiler-and-launch.md apps/api/tests/unit/test_workflow_compiler.py`
- outcome:
  - stale Phase 1 vocabulary now appears only in the kill-list definition, the
    forbidden-field lists, or the current unsafe-old-doc warning; the active
    workflow schema docs and compiler tests do not teach those shapes as live
    target semantics

## Kill-list proof

- phase kill-list source:
  - `docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md`
- terms checked:
  - `authored \`edges\` as canonical workflow authoring`
  - `dotted-id parent inference as core semantics`
  - `generic authored \`skill_refs\` as target schema`
  - `obsolete flat flagship workflow teaching model`
- outcome:
  - `authored \`edges\`` appears only as a kill-list term and as a forbidden
    authored field in `workflow-definition-schema.md`
  - dotted-id parent inference is contradicted by the explicit opaque-id
    compiler coverage in `apps/api/tests/unit/test_workflow_compiler.py`
  - generic authored `skill_refs` appear only in rejected-field and
    unsafe-old-doc warning contexts, not as accepted schema
  - the obsolete flat flagship teaching model appears only in the Phase 1
    kill-list and the current unsafe-old-doc warning, not as live guidance

## Docs answer-sourcing proof

- redesign owners relied on:
  - `docs/redesign/workflows/workflow-definition-schema.md`
  - `docs/redesign/interfaces/role-and-policy-definition-schema.md`
- supporting redesign reads or appendix owners relied on:
  - `docs/redesign/workflows/workflow-schema-appendix.md`
- current-contrast pages relied on:
  - `docs/current/interfaces/definition-registry-and-publish-lifecycle.md`
  - `docs/current/interfaces/definitions-compiler-and-launch.md`
- code or tests inspected:
  - `apps/api/tests/integration/test_definition_registry_db.py`
  - `apps/api/tests/integration/test_db_reset_db.py`
  - `apps/api/tests/unit/test_cli.py`
  - `apps/api/tests/unit/test_workflow_compiler.py`
- canon gap or explicit `none`:
  - none

## Phase-bounded STYLE exceptions

- `none`

## Reset-gate outcome

- pass: the review relies on the evidence artifact's positive shipped-path
  SQLite `init`, `db upgrade`, and `db reset` proof plus its recorded broader
  Postgres or Docker strong-verification lane. This is sufficient for the
  landed `P1-WP1`..`P1-WP3` slice and does not claim wider package or example
  completeness.

## Remaining exact blockers

- none inside this authoritative `P1-WP1`..`P1-WP3` review scope
- any broader example or fixture closure belongs to `P1-WP4`, which this slice
  does not claim
- no newer repo-local proof beyond what the evidence artifact records was
  required for this artifact rescope

## Remaining fixes before later phases can close

- Phase 2 still needs surfaced checkpoint, Task Memory, transient-index,
  field-renderer, and truthful same-session closure repair
- Phase 3 still needs runtime DB/control-state/replan/API contract repair and
  stronger exact contract tests

## Cross-links

- aggregate historical summary: `./phase-0-3-closeout.md`
- companion exceptions page, if any: `none`
