# Phase 2 Prompt, Manifest, Artifact, and Bootstrap Contract Repair Evidence

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
- work package or slice: authoritative evidence refresh for `P2-WP1`, `P2-WP2`, and `P2-WP3`

## Plan link

- approved plan: `../plans/phase-2-prompt-bootstrap-contract-repair.md`

## Bounded Slice

The 2026-05-06 work in this document is the authoritative artifact refresh only. It used no subagents and changed only the three owned execution artifacts.

## Repaired Phase 2 Truth

- `P2-WP1`, `P2-WP2`, and `P2-WP3` are the only valid Phase 2 work-package ids in this artifact set.
- Prompt-block drift is closed by the landed prompt catalog, prompt-doc, and generated-example reconciliation.
- Live surfaced-resource localization is on the production path.
- `artifact-index.json` publications now include `owner_node_key`.
- `prompt_catalog_tools.py validate` now semantically audits prompt-family versus node-kind mapping and still checks generated-example parity.
- The current focused Phase 2 prompt/bootstrap lane result is `26 passed`.
- Prompt catalog validation passed in the current lane.

## Recorded Proof Lanes

- Historical Phase 2 runtime proof retained from the implementation wave:
  - `./.venv/bin/pytest -q apps/api/tests/unit/test_runtime_prompt_rendering.py apps/api/tests/integration/test_phase2_runtime_bootstrap.py`
  - Earlier recorded outcomes in this artifact family advanced from `21 passed` to `24 passed`; the current lane truth to encode here is `26 passed`.
- Current prompt-catalog proof retained in current context:
  - `./.venv/bin/python scripts/docs/prompt_catalog_tools.py generate`
  - outcome: passed and kept `docs/redesign/prompt-layer/generated/rendered-examples.md` aligned with the live renderer.
- Current prompt-catalog validation retained in current context:
  - `./.venv/bin/python scripts/docs/prompt_catalog_tools.py validate`
  - outcome: passed after canon reconciliation; the validator now semantically audits prompt-family versus node-kind mapping and generated-example parity.
- Current-tree ownership sanity retained in current context:
  - `git diff --name-only -- pyproject.toml apps/api/app/runtime/resources.py docs/redesign/architecture/manifest-contract.md docs/redesign/architecture/worker-context-contract.md docs/redesign/architecture/task-root-layout-and-generated-files.md docs/redesign/architecture/artifact-ref-and-storage-contract.md`
  - outcome: no new bounded-refresh edits on those surfaces.

## Phase 2 Findings Captured By This Refresh

- Prompt render requests validate prompt-family legality against node kind and node-key context before rendering.
- `same_session_continue` remains transport-only and must not carry `instructions_text`.
- Worker prompts keep criteria or consumed durable refs in scope even when `current_relevant_paths` is empty.
- Parent and root prompts surface current decision criteria or artifact refs explicitly.
- Live localization now lands on the production task-root path instead of remaining a doc-only or planned behavior.
- Artifact-index publications carry `owner_node_key`, matching the artifact storage contract.

## Gate And Validator State

- Focused Phase 2 prompt/bootstrap lane: passed at `26 passed`.
- Prompt catalog validate: passed.
- Prompt-block drift closure: passed by canon reconciliation.
- Docs freeze: parent rerun completed and passed.
- Reset proof: required for the Phase 2 task-root or manifest truth and now explicitly recorded through the shipped SQLite trio at `3 passed`.
- Package-install smoke: historical only in this artifact family; not claimed here as a fresh rerun.

## Exact Scope Limits

- No prompt docs, generated examples, docs tooling, or code paths were edited in this bounded refresh.
- No `P2-WP4`, `P2-WP5`, or `P2-WP6` ids survive in the authoritative artifact wording.
- No `not applicable` reset verdict is used for the underlying Phase 2 task-root or manifest truth.

## Final Parent Follow-Up

- `./.venv/bin/python scripts/docs/docs_freeze_validate.py` -> passed after all artifact refreshes landed.
- `./.venv/bin/pytest -q apps/api/tests/unit/test_cli.py::test_init_writes_minimal_config_and_db_file apps/api/tests/unit/test_cli.py::test_db_upgrade_bootstraps_seeded_sqlite_database_on_shipped_path apps/api/tests/unit/test_cli.py::test_db_reset_recreates_sqlite_database` -> `3 passed`.

## Cross-Links

- approved plan: `../plans/phase-2-prompt-bootstrap-contract-repair.md`
- review artifact: `../reviews/phase-2-prompt-bootstrap-contract-repair.md`
