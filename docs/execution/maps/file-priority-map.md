# Implementation file lock map

Status: Target

Use this page as the canonical owned-surface map for redesign implementation.

Read it together with the current phase page before planning or editing.

## Rule

For each phase:

- `owned surfaces` are the primary files and directories the phase is expected to change
- `allowed collateral surfaces` may be changed only when the owned work cannot land cleanly without them
- `do not edit / defer surfaces` must stay untouched unless canon is patched first or the phase is re-scoped
- `required tests and validators` are the minimum evidence tied to those surfaces

If a needed edit falls outside the owned or allowed collateral surfaces, stop and either:

1. patch canon first
2. re-scope the work package
3. move the change into the owning phase

## Appendix-owner routing

Use the current phase page for authoritative appendix owners:

- `docs/redesign/interfaces/api-schema-appendix.md`
- `docs/redesign/workflows/workflow-schema-appendix.md`
- `docs/redesign/prompt-layer/prompt-resource-usage-appendix.md`

## Phase 0

### Phase 0 owned surfaces

- `AGENTS.md`, `STYLE.md`
- `docs/README.md`
- `docs/execution/gates/*`
- `docs/execution/phases/*`
- `docs/execution/how-to/*`
- execution router pages under `docs/redesign/*/README.md` when execution routing depends on them
- docs tooling and validation references under `scripts/docs/*`

### Phase 0 allowed collateral surfaces

- `docs/redesign/prompt-layer/*` when execution prompt-family ownership changes require prompt-layer alignment
- `README.md` when root execution routing changes

### Phase 0 do not edit / defer surfaces

- repo code under `apps/**`, `definitions/**`, `scripts/**`,
  `pyproject.toml`, and `Makefile`, except docs tooling under `scripts/docs/*`
- shipped current-behavior pages beyond router corrections

### Phase 0 required tests and validators

- `python scripts/docs/docs_freeze_validate.py`
- `python scripts/docs/prompt_catalog_tools.py validate` when prompt surfaces change
- `python scripts/docs/prompt_catalog_tools.py generate` before validation when prompt inputs or generated prompt pages change

## Phase 0.5

### Phase 0.5 owned surfaces

- `docs/execution/phases/phase-0.5-cleanup-and-salvage-baseline.md`
- `docs/execution/gates/cleanup-and-salvage-checklist.md`
- `docs/execution/maps/repo-salvage-matrix.md`
- `docs/execution/maps/current-schema-route-and-plugin-migration-appendix.md`
- reset and cleanup how-to pages under `docs/execution/how-to/*`

### Phase 0.5 allowed collateral surfaces

- `docs/execution/README.md`
- `docs/execution/phases/overview.md`
- root/router pages that must reflect the cleanup baseline

### Phase 0.5 do not edit / defer surfaces

- redesign implementation code beyond narrow reset/bootstrap smoke fixes
- target contract pages under `docs/redesign/` unless cleanup canon is genuinely incomplete

### Phase 0.5 required tests and validators

- `python scripts/docs/docs_freeze_validate.py`
- retained infra tests and smoke evidence for reset, reseed, bootstrap, and plugin skeleton viability

## Phase 1

### Phase 1 owned surfaces

- `apps/api/app/schemas/*`
- `apps/api/app/compiler/*`
- `definitions/**/*`
- `docs/redesign/workflows/workflow-definition-schema.md`
- `docs/redesign/workflows/task-compose-schema.md`
- `docs/redesign/workflows/compiler-contract-and-launch-materialization.md`
- `docs/redesign/workflows/examples/*`
- `docs/redesign/workflows/workflow-schema-appendix.md`

### Phase 1 allowed collateral surfaces

- compiler-facing tests under `apps/api/tests/*`
- narrow registry parsing surfaces when schema/compiler alignment requires them

### Phase 1 do not edit / defer surfaces

- runtime persistence and controller-loop behavior
- gateway, watchdog, operator, and plugin surfaces
- package/install/release surfaces

### Phase 1 required tests and validators

- schema validation unit tests
- compiler normalization and legality integration tests
- example or fixture validation for minimal, normal, and maximal authored workflows

## Phase 2

### Phase 2 owned surfaces

- `apps/api/app/schemas/runtime.py`
- `apps/api/app/db/models/runtime.py`
- `apps/api/app/runtime/resources.py`
- `apps/api/app/runtime/dispatcher.py`
- prompt, render, and materialization services under `apps/api/app/runtime/*`
- `docs/redesign/prompt-layer/*`
- `docs/redesign/architecture/manifest-contract.md`
- `docs/redesign/architecture/worker-context-contract.md`
- `docs/redesign/architecture/task-root-layout-and-generated-files.md`
- `docs/redesign/architecture/artifact-ref-and-storage-contract.md`

### Phase 2 allowed collateral surfaces

- prompt-generated example surfaces under `docs/redesign/prompt-layer/generated/*`
- prompt resource appendix and workflow schema appendix
- API presenters or runtime read models only where the prompt/runtime contract cannot otherwise be represented

### Phase 2 do not edit / defer surfaces

- parent/root review and structural replan semantics
- watchdog, operator, plugin, and support-state surfaces
- public ingest, package, and release behavior

### Phase 2 required tests and validators

- prompt/render unit tests
- manifest projection and bootstrap integration tests
- minimal e2e lane when viable
- prompt-catalog generate/validate when prompt-layer owner or generated surfaces change

## Phase 3

### Phase 3 owned surfaces

- runtime persistence and control services under `apps/api/app/runtime/*`
- runtime models under `apps/api/app/db/*`
- runtime schemas and presenters under `apps/api/app/schemas/*` and
  `apps/api/app/api/*`
- runtime/review/replan owner docs under `docs/redesign/architecture/*` and `docs/redesign/workflows/*`

### Phase 3 allowed collateral surfaces

- worker-context, artifact, and API appendix owners when review, closure, or replan payloads need exact updates
- targeted route shells when runtime closure/readback behavior changes

### Phase 3 do not edit / defer surfaces

- gateway/session/continuity implementation beyond narrow compatibility fixes
- operator/plugin and support-state readback surfaces
- public ingest/package/release surfaces

### Phase 3 required tests and validators

- runtime transition unit tests
- review, closure, and replan integration tests
- normal e2e lane when viable

## Phase 4A

### Phase 4A owned surfaces

- `apps/api/app/integrations/openclaw.py`
- `apps/api/app/services/openclaw_bridge.py`
- worker-lane gateway/session/continuity services under `apps/api/app/runtime/*`
- `docs/redesign/architecture/openclaw-worker-and-gateway-contract.md`
- `docs/redesign/architecture/openclaw-session-lifecycle.md`
- `docs/redesign/architecture/openclaw-continuity-and-send-modes.md`

### Phase 4A allowed collateral surfaces

- runtime presenters and API appendix surfaces for session and dispatch readbacks
- prompt resource appendix where session/continuation behavior affects worker delivery

### Phase 4A do not edit / defer surfaces

- watchdog/operator/plugin behavior and support-state readback freezing
- public ingest/API/CLI packaging surfaces

### Phase 4A required tests and validators

- session, continuity, and worker-lane integration tests
- viable minimal and normal e2e lanes

## Phase 4B

### Phase 4B owned surfaces

- watchdog and monitor services under `apps/api/app/runtime/*`
- the repo-local plugin source tree created during Phase 4B from a target-only
  rebuild boundary
- `docs/redesign/interfaces/plugin-tool-reference.md`
- `docs/redesign/interfaces/human-and-operator-control-surface.md`
- `docs/redesign/architecture/runtime-monitoring-and-watchdog-automation.md`
- `docs/redesign/architecture/runtime-observability-and-boundary-log.md`

### Phase 4B allowed collateral surfaces

- runtime database/support-state docs and API appendix owner pages
- narrow OpenClaw dispatch read models needed for watchdog or operator evidence

### Phase 4B do not edit / defer surfaces

- gateway/session core semantics except follow-on fixes discovered through watchdog work
- public ingest/API/CLI and packaging/release surfaces

### Phase 4B required tests and validators

- watchdog/operator/plugin integration tests
- support-state schema or example verification
- viable minimal, normal, and maximal e2e lanes

## Phase 5A

### Phase 5A owned surfaces

- definition ingest and upload services under `apps/api/app/registry/*` and
  `apps/api/app/services/*`
- public API route and presenter surfaces under `apps/api/app/api/*`
- root CLI entrypoints under `apps/api/app/cli.py`
- `docs/redesign/interfaces/definition-registry-and-upload-contract.md`
- `docs/redesign/interfaces/definition-ingest-and-upload-contract.md`
- `docs/redesign/interfaces/cli-surface-and-operator-workflows.md`
- `docs/redesign/interfaces/api-surface-and-trust-lane-map.md`
- `docs/redesign/interfaces/api-schema-appendix.md`

### Phase 5A allowed collateral surfaces

- compiler or schema surfaces when public ingest payloads require exact alignment
- onboarding examples that demonstrate the public CLI/API nouns

### Phase 5A do not edit / defer surfaces

- packaging, install/reset, release, and docs archive cutover surfaces
- gateway/watchdog/plugin contract pages except doc fixes needed for consistent public nouns

### Phase 5A required tests and validators

- ingest/API/CLI unit tests
- public-surface integration tests
- all viable e2e lanes

## Phase 5B

### Phase 5B owned surfaces

- `pyproject.toml`
- `Makefile`
- `scripts/*`
- install, release, onboarding, and cutover docs
- root/router docs that must point to the final canonical surfaces
- archive cleanup under `docs/archive/*`

### Phase 5B allowed collateral surfaces

- CLI docs/examples when package or reset behavior changes their invocation story
- current docs router pages when cutover needs them to point cleanly back to canon

### Phase 5B do not edit / defer surfaces

- core runtime, compiler, gateway, watchdog, plugin, and public API semantics except doc corrections required for cutover

### Phase 5B required tests and validators

- package, install, and reset smoke checks
- `python scripts/docs/docs_freeze_validate.py`
- repo link and router audit
- all viable e2e lanes when packaging or reset changes can invalidate prior evidence
