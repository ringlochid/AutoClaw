# Phase 2 Prompt, Manifest, Artifact, and Bootstrap Contract Repair Review

Status: Reference

selected phase: Phase 2
current phase page: docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md
selected work packages: P2-WP1, P2-WP2, P2-WP3
summary-only: no
delegated slices: listed
slice id: phase-2-runtime-code-and-tests
slice type: edit
owned surfaces: apps/api/app/runtime/contracts.py, apps/api/app/runtime/resources.py, apps/api/app/runtime/projection/state.py, apps/api/app/runtime/projection/materialize.py, apps/api/app/runtime/prompt/bundle.py, apps/api/app/runtime/prompt/instructions.py, apps/api/app/runtime/prompt/sections.py, apps/api/app/runtime/launch/projection.py, apps/api/tests/unit/test_runtime_prompt_rendering.py, apps/api/tests/integration/test_phase2_runtime_bootstrap.py
touched surfaces: apps/api/app/runtime/contracts.py, apps/api/app/runtime/resources.py, apps/api/app/runtime/projection/state.py, apps/api/app/runtime/projection/materialize.py, apps/api/app/runtime/prompt/bundle.py, apps/api/app/runtime/prompt/instructions.py, apps/api/app/runtime/prompt/sections.py, apps/api/app/runtime/launch/projection.py, apps/api/tests/unit/test_runtime_prompt_rendering.py, apps/api/tests/integration/test_phase2_runtime_bootstrap.py
slice id: phase-2-docs-examples-and-prompt-validation
slice type: edit
owned surfaces: docs/redesign/prompt-layer/source-and-sections.md, docs/redesign/prompt-layer/field-renderers.md, docs/redesign/prompt-layer/prompt-resource-usage-appendix.md, docs/redesign/prompt-layer/composition-example.md, docs/redesign/prompt-layer/generated/rendered-examples.md, docs/redesign/prompt-layer/prompt-catalog.yaml, docs/current/interfaces/prompt-layer-and-worker-delivery.md, scripts/docs/prompt_catalog_tools.py
touched surfaces: docs/redesign/prompt-layer/source-and-sections.md, docs/redesign/prompt-layer/field-renderers.md, docs/redesign/prompt-layer/prompt-resource-usage-appendix.md, docs/redesign/prompt-layer/composition-example.md, docs/redesign/prompt-layer/generated/rendered-examples.md, docs/redesign/prompt-layer/prompt-catalog.yaml, docs/current/interfaces/prompt-layer-and-worker-delivery.md, scripts/docs/prompt_catalog_tools.py
slice id: phase-2-artifact-audit
slice type: review-only
owned surfaces: none
touched surfaces: none
slice id: phase-2-correctness-audit
slice type: review-only
owned surfaces: none
touched surfaces: none

## Slice identity

- selected phase: Phase 2
- work package or slice: authoritative review refresh for `P2-WP1`, `P2-WP2`, and `P2-WP3`

## Phase-local contract

- current phase page: `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`

## Scope

- reviewed plan: `../plans/phase-2-prompt-bootstrap-contract-repair.md`
- reviewed evidence: `../evidence/phase-2-prompt-bootstrap-contract-repair.md`
- Reviewed refresh scope: the three owned execution artifacts only.

## Verdict

- pass/fail: pass
- summary: this authoritative artifact refresh now matches the execution pack grammar, the real Phase 2 work-package ids, and the current Phase 2 proof truth without overwriting non-owned surfaces.

## Findings

- The authoritative artifacts now use the required parseable labels: `selected phase:`, `current phase page:`, `selected work packages:`, `summary-only:`, `delegated slices:`, `slice id:`, `slice type:`, `owned surfaces:`, and `touched surfaces:`.
- The fake Phase 2 ids `P2-WP4`, `P2-WP5`, and `P2-WP6` were removed; the records now map only to `P2-WP1`, `P2-WP2`, and `P2-WP3`.
- The records now encode the current Phase 2 behavior truth: live localization is on the production path, `artifact-index.json` publications include `owner_node_key`, and prompt render legality is checked against node kind.
- The records now encode the current validation truth: `prompt_catalog_tools.py validate` passed and semantically audits prompt-family versus node-kind mapping.
- Prompt-block drift is recorded as closed by canon reconciliation instead of being left as an open or ambiguous drift state.
- The focused Phase 2 prompt/bootstrap lane is recorded as `26 passed`.
- Docs-freeze proof is no longer overclaimed; the artifacts state precisely that the parent will rerun it after all artifact refreshes.
- Reset proof is no longer mislabeled as `not applicable`; it remains required for the Phase 2 task-root or manifest truth.

## Delegated-slice compliance

- The historical delegated edit and review-only slices remain in-bounds for the underlying Phase 2 work and are now represented with parseable slice labels.
- The 2026-05-06 authoritative artifact refresh itself used no subagents and stayed inside the three owned execution artifacts.
- No review-only slice is recorded as editing files.

## Proof lanes relied on

- focused Phase 2 prompt/bootstrap lane: `26 passed`
- `prompt_catalog_tools.py validate`: passed and semantically audits prompt-family versus node-kind mapping
- prompt-block drift closure: passed by canon reconciliation
- docs-freeze proof now includes the final parent rerun after all artifact refreshes

## Stale-logic search proof

- checked for stale `P2-WP4`..`P2-WP6` references, stale docs-freeze pass claims, and stale reset `not applicable` wording
- outcome: those stale claims were removed from the authoritative Phase 2 artifact chain

## Kill-list proof

- checked for `redesign docs treated as the shipped prompt source`, `prompt rules that rely on hidden transcript memory`, `filesystem-primary truth for generated roots`, and `runtime persistence truth split across both Phase 2 and Phase 3`
- outcome: the authoritative Phase 2 artifacts now describe the landed controller-owned/task-root-localized behavior without reintroducing those kill-list terms as live truth

## Docs answer-sourcing proof

- Required execution canon read and applied:
  - `AGENTS.md`
  - `STYLE.md`
  - `docs/execution/README.md`
  - `docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md`
  - `docs/execution/maps/file-priority-map.md`
- Required redesign owners read and applied:
  - `docs/redesign/architecture/manifest-contract.md`
  - `docs/redesign/architecture/artifact-ref-and-storage-contract.md`
- Current artifact set read and reconciled:
  - `docs/execution/plans/phase-2-prompt-bootstrap-contract-repair.md`
  - `docs/execution/evidence/phase-2-prompt-bootstrap-contract-repair.md`
  - `docs/execution/reviews/phase-2-prompt-bootstrap-contract-repair.md`

## Phase-bounded STYLE exceptions

- `none`

## Reset-Gate Outcome

- Reset proof remains required for the Phase 2 task-root or manifest truth changed in the underlying lane.
- Final retained proof now includes the shipped SQLite trio at `3 passed`, so the reset requirement is satisfied and not waived.

## Remaining Exact Follow-Up

- Final parent rerun completed: `./.venv/bin/python scripts/docs/docs_freeze_validate.py` -> passed.
- Final retained reset proof: shipped SQLite trio -> `3 passed`.

## Residual Risk

- None inside the owned artifact wording after this refresh.

## Cross-Links

- Aggregate historical summary, if any: `./phase-0-3-closeout.md`
- Companion exceptions page, if any: `none`
