# Redesign-to-code landing map

Status: Reference

Use this map when a redesign phase must prove that target owner docs,
companion examples or diagrams, current-contrast pages, code surfaces, and
proof gates all line up.

This map is implementation guidance only. The live target contract still lives
under `docs/redesign/`, the shipped-behavior contrast still lives under
`docs/current/`, and phase-local delivery still lives on the current phase page
plus the implementation file lock map.

## Rule

For each landing row below:

- read the named redesign owner pages first
- read any required supporting redesign reads named by the current phase page
  when secondary live target pages sharpen semantics, durable decisions, or
  teaching coverage for that row
- read the named companion examples or diagrams next when they define behavior,
  evidence flow, or generated-surface shape
- read the named current-contrast pages when migration truth, shipped routes,
  or shipped package or DB behavior matter
- update the named code surfaces for the owning phase only
- satisfy the named proof gates before claiming that landing row is complete

If a redesign owner page is not covered by a row here, add the row before
treating the landing plan as complete.

Record the approved phase plan under `docs/execution/plans/`, executed proof
under `docs/execution/evidence/`, and review outputs under
`docs/execution/reviews/`.

Any approved plan, evidence artifact, or review output used to close a phase
must name exactly one selected phase. Cross-phase summaries are historical
reference only and do not satisfy the proof requirements in this map.

## Coverage classes

Execution coverage is complete only when the selected phase accounts for all
relevant redesign pages in one of these classes:

- primary redesign owners listed on the current phase page
- required supporting redesign reads listed on the current phase page for
  secondary live target pages that sharpen semantics, authority boundaries, or
  teaching coverage
- required examples and diagrams listed on the current phase page
- appendix owners listed on the current phase page when exact API, schema,
  prompt, or payload detail matters
- current-contrast pages listed on the current phase page when migration truth
  or shipped behavior matters

Use these directory-level rules so the rest of `docs/redesign/` is never left
implicit:

- [Decisions front door](../../redesign/decisions/README.md) plus the relevant
  ADRs are required when a phase touches cross-cutting invariants,
  stale-vocabulary cleanup, controller-versus-adapter boundaries, or
  phase-boundary disputes
- [How-to front door](../../redesign/how-to/README.md) plus the relevant
  how-to pages are required when a phase changes onboarding, DB verification,
  debugging, recovery, install, or release behavior
- [Tutorials front door](../../redesign/tutorials/README.md) plus the relevant
  tutorial pages are required when a phase changes copy-safe teaching
  examples, public noun walkthroughs, or end-to-end tutorial proof
- [Findings](../../redesign/findings.md) is reference-only and is reread only
  when live owner docs plus accepted ADRs still leave a canon gap or
  stale-wording conflict unresolved

## Cross-cutting secondary coverage

- [Redesign overview](../../redesign/architecture/redesign-overview.md) and
  [Glossary and boundaries](../../redesign/architecture/glossary-and-boundaries.md)
  are required whenever a phase changes shared runtime nouns, public
  boundaries, or truth-versus-projection wording.
- [Runtime lane separation rationale](../../redesign/architecture/runtime-lane-separation-rationale.md)
  and [Provider, worker, and operator boundary](../../redesign/architecture/provider-worker-and-operator-boundary.md)
  are required whenever a phase changes worker, operator, observability,
  plugin, or adapter-lane separation.
- [Prompt-layer index](../../redesign/prompt-layer/INDEX.md),
  [Prompt field renderers](../../redesign/prompt-layer/field-renderers.md),
  [Generated prompt inventory](../../redesign/prompt-layer/generated/inventory.md),
  [Prompt catalog machine surface](../../redesign/prompt-layer/prompt-catalog.yaml),
  [System and provider block](../../redesign/prompt-layer/prompt-pack/system-and-provider-block.md),
  [Runtime rule blocks](../../redesign/prompt-layer/prompt-pack/runtime-rule-blocks.md),
  and [Validation and reject blocks](../../redesign/prompt-layer/prompt-pack/validation-and-reject-blocks.md)
  are required whenever a phase changes prompt assembly, prompt examples,
  prompt-family inventory, same-session wrapper behavior, or human-facing
  reject wording.
- [Historical prompt and artifact layers](../../redesign/prompt-layer/historical-prompt-and-artifact-layers.md),
  [historical dispatch-family packs](../../redesign/prompt-layer/prompt-pack/dispatch-family-packs.md),
  [historical packet prose examples](../../redesign/prompt-layer/prompt-pack/historical-packet-prose-examples.md),
  and [historical state and boundary overlays](../../redesign/prompt-layer/prompt-pack/state-and-boundary-overlays.md)
  are reference-only and must be reread when stale prompt, packet, bundle, or
  overlay vocabulary is part of the blocker or cleanup decision.

## Phase 0

| Landing row | Redesign owners | Companion examples and diagrams | Current contrast reads | Owning phase | Landing surfaces | Required proof |
| --- | --- | --- | --- | --- | --- | --- |
| execution authority and routing | `docs/redesign/README.md`, `docs/redesign/architecture/README.md`, `docs/redesign/prompt-layer/README.md`, `docs/redesign/workflows/README.md`, `docs/redesign/interfaces/README.md` | `docs/redesign/prompt-layer/composition-example.md`, `docs/redesign/prompt-layer/generated/rendered-examples.md` | `docs/current/interfaces/definition-precedence-and-skill-version-defaults.md`, `docs/current/interfaces/definitions-compiler-and-launch.md`, `docs/current/interfaces/definition-registry-and-publish-lifecycle.md`, `docs/current/architecture/runtime-control-plane.md` when Phase 0 canon repair must make shipped seed-authority, reseed-semantics, or cancel-behavior contrast truth explicit; `docs/current/architecture/current-architecture.md` and `docs/current/architecture/openclaw-dispatch-and-session-contract.md` only when stale path cleanup must be made explicit | Phase 0 | `docs/execution/**/*`, `docs/README.md`, redesign router pages, the six explicit Phase 0 current-doc unlocks named on the Phase 0 page, `scripts/docs/*` | docs freeze validate, prompt catalog validate or generate when touched, `ruff check scripts/docs`, and `mypy scripts/docs` when `scripts/docs/*` changed |

## Phase 1

| Landing row | Redesign owners | Companion examples and diagrams | Current contrast reads | Owning phase | Landing surfaces | Required proof |
| --- | --- | --- | --- | --- | --- | --- |
| internal definition identity, revision, and currentness truth | `docs/redesign/interfaces/definition-registry-and-upload-contract.md`, `docs/redesign/interfaces/guarded-registry-and-runtime-writes.md`, `docs/redesign/interfaces/role-and-policy-definition-schema.md` | none beyond the workflow and role or policy examples named on the phase page | `docs/current/interfaces/definition-registry-and-publish-lifecycle.md`, `docs/current/interfaces/definitions-compiler-and-launch.md` | Phase 1 | internal definition persistence and lookup surfaces under `apps/api/app/db/*`, `apps/api/app/registry/*`, or `apps/api/app/services/*` that stay internal and do not widen into public ingest routes, package-contained seed mirrors under `apps/api/app/resources/definitions/**`, narrow `pyproject.toml` package-data entries for those seed mirrors, and the existing shipped init/upgrade/reset shell under `apps/api/app/cli.py` when that persistence truth must be reachable through shipped paths without widening public CLI nouns | definition identity or revision persistence tests, registry-backed lookup tests, compiler-facing revision-pinning tests, shipped-path schema install, upgrade, and reset proof for SQLite when definition persistence truth changes, and Postgres + Docker strong verification when definition persistence truth changes and the lane is viable |
| authored workflow schema and legality | `docs/redesign/workflows/workflow-definition-schema.md`, `docs/redesign/workflows/task-compose-schema.md`, `docs/redesign/workflows/typed-dependency-selectors-and-produce-slots.md`, `docs/redesign/workflows/mode-contract-and-legality-matrix.md`, `docs/redesign/workflows/criteria-and-parent-verification.md`, `docs/redesign/workflows/workflow-schema-appendix.md`, `docs/redesign/interfaces/role-and-policy-definition-schema.md` | `docs/redesign/workflows/examples/minimal.md`, `docs/redesign/workflows/examples/normal.md`, `docs/redesign/workflows/examples/maximal.md`, `docs/redesign/workflows/criteria-projection-and-consumption-example.md` | `docs/current/interfaces/definition-and-task-compose-yaml-contract.md`, `docs/current/interfaces/definitions-compiler-and-launch.md`, `docs/current/interfaces/definition-precedence-and-skill-version-defaults.md` | Phase 1 | `apps/api/app/schemas/*`, `apps/api/app/compiler/*`, `definitions/**/*` | schema validation unit tests, compiler legality integration tests, example or fixture validation for minimal, normal, and maximal workflows |
| compiler launch normalization | `docs/redesign/workflows/compiler-contract-and-launch-materialization.md`, `docs/redesign/workflows/provider-direction-and-provider-native-capabilities.md`, `docs/redesign/workflows/role-and-policy-example-definitions.md` | worked compiler diagrams in `compiler-contract-and-launch-materialization.md` | `docs/current/interfaces/definitions-compiler-and-launch.md` | Phase 1 | `apps/api/app/compiler/*`, narrow registry parsing or lookup persistence surfaces when Phase 1 canon requires them | compile-time normalization tests, fixture-based role or policy resolution tests, revision-pinning tests against controller-owned definition truth |

## Phase 2

| Landing row | Redesign owners | Companion examples and diagrams | Current contrast reads | Owning phase | Landing surfaces | Required proof |
| --- | --- | --- | --- | --- | --- | --- |
| prompt contract and rendered delivery | `docs/redesign/prompt-layer/contract.md`, `docs/redesign/prompt-layer/source-and-sections.md`, `docs/redesign/prompt-layer/field-renderers.md`, `docs/redesign/prompt-layer/render-and-persistence.md`, `docs/redesign/prompt-layer/machine-contract.md`, `docs/redesign/prompt-layer/prompt-resource-usage-appendix.md`, `docs/redesign/prompt-layer/prompt-pack/README.md`, `docs/redesign/prompt-layer/generated/README.md`, `docs/redesign/prompt-layer/legality-and-coverage.md` | `docs/redesign/prompt-layer/composition-example.md`, `docs/redesign/prompt-layer/generated/rendered-examples.md`, `docs/redesign/prompt-layer/generated/inventory.md`, prompt-layer mermaid diagrams in `render-and-persistence.md` | `docs/current/interfaces/prompt-layer-and-worker-delivery.md`, `docs/current/interfaces/current-openclaw-bridge-prompt-strings.md` | Phase 2 | prompt or render services under `apps/api/app/runtime/*`, app-owned shipped prompt assets under `apps/api/app/runtime/prompt/assets/**`, prompt-layer owner pages as mirrors of that shipped source, generated prompt examples, targeted prompt validation tooling under `scripts/docs/*`, and narrow `pyproject.toml` package-data entries only when those prompt assets must ship through the existing package path | prompt render unit tests, prompt asset lookup tests, prompt catalog generate or validate when touched, package-install verification when prompt asset shipping changes, minimal e2e lane when viable |
| manifest, worker context, task-root, and artifact materialization | `docs/redesign/architecture/manifest-contract.md`, `docs/redesign/architecture/worker-context-contract.md`, `docs/redesign/architecture/task-root-layout-and-generated-files.md`, `docs/redesign/architecture/artifact-ref-and-storage-contract.md`, `docs/redesign/architecture/filesystem-layout-and-roots.md`, `docs/redesign/architecture/task-compose-root-binding-and-host-placement.md` | task-root layout diagram in `task-root-layout-and-generated-files.md` | `docs/current/architecture/manifest-projection-and-acknowledgement.md`, `docs/current/architecture/task-roots-and-materialized-paths.md` | Phase 2 | `apps/api/app/runtime/resources.py`, prompt/render/materialization helpers under `apps/api/app/runtime/*` that own manifest projection, task-root generation, artifact localization, or generated read-surface materialization | manifest projection and task-root bootstrap integration tests, minimal e2e lane when viable |
| explicit split from runtime persistence truth | `docs/redesign/architecture/runtime-records-and-lifecycle.md`, `docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md` | lifecycle diagrams used only as defer-boundary reference | none beyond Phase 2 current-contrast reads above | Phase 2 | phase docs and lock map only | review evidence that assignments, attempts, checkpoints, currentness rows, release precondition truth, and the foreground control-state handshake remain Phase 3-owned |

## Phase 3

| Landing row | Redesign owners | Companion examples and diagrams | Current contrast reads | Owning phase | Landing surfaces | Required proof |
| --- | --- | --- | --- | --- | --- | --- |
| runtime records, currentness, and projections | `docs/redesign/architecture/runtime-records-and-lifecycle.md`, `docs/redesign/architecture/runtime-database-and-object-contract.md`, `docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md`, `docs/redesign/architecture/runtime-lifecycle-overview.md`, `docs/redesign/architecture/assignment-contract.md`, `docs/redesign/architecture/checkpoint-contract.md`, `docs/redesign/architecture/worker-context-contract.md`, `docs/redesign/architecture/artifact-ref-and-storage-contract.md`, `docs/redesign/architecture/completion-checkpoint-and-evidence.md` | lifecycle and controller-loop mermaid diagrams in the owner pages above | `docs/current/architecture/runtime-control-plane.md`, `docs/current/architecture/runtime-read-models-and-operator-surfaces.md`, `docs/current/interfaces/api-surface-and-route-map.md`, `docs/current/interfaces/api-trust-lanes.md`, `docs/current/operations/run-docker-postgres-verification.md` | Phase 3 | `apps/api/app/db/*`, `apps/api/app/schemas/runtime.py`, runtime control and persistence services under `apps/api/app/runtime/*`, runtime presenters under `apps/api/app/api/*`, foreground control-state and replacement-dispatch handshake logic, plus the existing shipped init/upgrade/reset shell under `apps/api/app/cli.py` when Phase 3-owned runtime persistence truth must be reachable through shipped paths without widening public CLI nouns, and narrow task-scoped `/operator/tasks/{task_id}/snapshot`, `/operator/tasks/{task_id}/trace`, and `/observability/tasks/{task_id}/*` read shells plus the presenter/read-model wiring they need when Phase 3-owned runtime truth must surface through compatibility reads without taking ownership of watchdog recovery, plugin parity, or frozen support-state semantics | runtime transition unit tests, control-state handshake tests, integration tests for assignment or attempt or checkpoint flows, shipped-path schema install, upgrade, and reset proof for SQLite when runtime persistence truth changes, Postgres + Docker strong verification when runtime persistence truth changes and the lane is viable, normal e2e lane when viable |
| parent verification, review, closure, and replan | `docs/redesign/workflows/criteria-and-parent-verification.md`, `docs/redesign/workflows/parent-review-and-replan.md`, `docs/redesign/workflows/parent-root-release-and-closure.md`, `docs/redesign/workflows/runtime-structural-replan.md`, `docs/redesign/workflows/review-findings-contract.md`, `docs/redesign/workflows/parent-root-planning-surface.md`, `docs/redesign/workflows/parent-worker-review-model.md`, `docs/redesign/interfaces/guarded-registry-and-runtime-writes.md`, `docs/redesign/interfaces/definition-registry-and-upload-contract.md`, `docs/redesign/workflows/workflow-schema-appendix.md`, `docs/redesign/interfaces/api-schema-appendix.md` | `docs/redesign/workflows/examples/normal.md`, `docs/redesign/workflows/examples/maximal.md`, lifecycle and controller-loop diagrams from the runtime owner pages above | `docs/current/architecture/runtime-read-models-and-operator-surfaces.md`, `docs/current/interfaces/api-surface-and-route-map.md` | Phase 3 | review, closure, and replan services under `apps/api/app/runtime/*`, runtime schemas or presenters, owner docs when exhaustive payload detail changes | review or closure integration tests, replan adoption tests, callback or pause or boundary legality tests, normal e2e lane when viable, DB proof lanes when persistence changes |

## Phase 4A

| Landing row | Redesign owners | Companion examples and diagrams | Current contrast reads | Owning phase | Landing surfaces | Required proof |
| --- | --- | --- | --- | --- | --- | --- |
| OpenClaw gateway, session, and continuity | `docs/redesign/architecture/openclaw-worker-and-gateway-contract.md`, `docs/redesign/architecture/openclaw-session-lifecycle.md`, `docs/redesign/architecture/openclaw-continuity-and-send-modes.md`, `docs/redesign/architecture/watchdog-and-provider-recovery.md`, `docs/redesign/interfaces/guarded-registry-and-runtime-writes.md`, `docs/redesign/prompt-layer/prompt-pack/README.md`, `docs/redesign/prompt-layer/prompt-resource-usage-appendix.md` | same-session examples in `docs/redesign/prompt-layer/generated/rendered-examples.md` and `docs/redesign/prompt-layer/composition-example.md` | `docs/current/architecture/openclaw-dispatch-and-session-contract.md`, `docs/current/architecture/openclaw-and-bridge-plugin.md`, `docs/current/interfaces/current-openclaw-bridge-prompt-strings.md`, `docs/current/interfaces/api-trust-lanes.md` | Phase 4A | `apps/api/app/integrations/openclaw.py`, `apps/api/app/services/openclaw_bridge.py`, worker-lane gateway or continuity services under `apps/api/app/runtime/*` | session and continuity integration tests, minimal and normal e2e lanes when viable |

## Phase 4B

| Landing row | Redesign owners | Companion examples and diagrams | Current contrast reads | Owning phase | Landing surfaces | Required proof |
| --- | --- | --- | --- | --- | --- | --- |
| watchdog recovery, operator/plugin parity, and frozen support-state readback semantics | `docs/redesign/interfaces/plugin-tool-reference.md`, `docs/redesign/interfaces/human-and-operator-control-surface.md`, `docs/redesign/interfaces/operator-definition-and-role-boundary.md`, `docs/redesign/interfaces/guarded-registry-and-runtime-writes.md`, `docs/redesign/architecture/runtime-monitoring-and-watchdog-automation.md`, `docs/redesign/architecture/runtime-observability-and-boundary-log.md`, `docs/redesign/architecture/watchdog-and-provider-recovery.md` | watchdog or observability diagrams in the owner pages above | `docs/current/architecture/watchdog-and-runtime-monitoring.md`, `docs/current/architecture/watchdog-and-openclaw-bridge.md`, `docs/current/operations/use-the-openclaw-bridge-plugin.md`, `docs/current/interfaces/api-surface-and-route-map.md`, `docs/current/interfaces/api-trust-lanes.md` | Phase 4B | watchdog and monitor services under `apps/api/app/runtime/*`, repo-local plugin source tree, operator-facing runtime read models where Phase 4B canon allows them, and frozen support-state example or schema owners | watchdog or operator or plugin integration tests, support-state verification, minimal or normal or maximal e2e lanes when viable |

## Phase 5A

| Landing row | Redesign owners | Companion examples and diagrams | Current contrast reads | Owning phase | Landing surfaces | Required proof |
| --- | --- | --- | --- | --- | --- | --- |
| definition ingest, public API, and CLI nouns | `docs/redesign/interfaces/definition-registry-and-upload-contract.md`, `docs/redesign/interfaces/definition-ingest-and-upload-contract.md`, `docs/redesign/interfaces/cli-surface-and-operator-workflows.md`, `docs/redesign/interfaces/cli-api-and-package-shape.md`, `docs/redesign/interfaces/api-surface-and-trust-lane-map.md`, `docs/redesign/interfaces/guarded-registry-and-runtime-writes.md`, `docs/redesign/interfaces/operator-definition-and-role-boundary.md`, `docs/redesign/interfaces/api-schema-appendix.md`, `docs/redesign/interfaces/api-machine-catalog.yaml` | public CLI and ingest examples in the owner pages above | `docs/current/interfaces/api-surface-and-route-map.md`, `docs/current/interfaces/api-trust-lanes.md`, `docs/current/interfaces/cli-surface-and-config-precedence.md`, `docs/current/interfaces/current-definition-bootstrap-and-task-upload.md`, `docs/current/interfaces/definition-registry-and-publish-lifecycle.md` | Phase 5A | `apps/api/app/registry/*`, `apps/api/app/services/*`, `apps/api/app/api/*`, `apps/api/app/cli.py` | ingest or API or CLI unit and integration tests, all viable e2e lanes, SQLite smoke when viable, Postgres + Docker strong verification when viable |

## Phase 5B

| Landing row | Redesign owners | Companion examples and diagrams | Current contrast reads | Owning phase | Landing surfaces | Required proof |
| --- | --- | --- | --- | --- | --- | --- |
| package, install, DB lanes, and docs cutover | `docs/redesign/interfaces/testing-and-release-checklist.md`, `docs/redesign/interfaces/release-and-install-strategy.md`, `docs/redesign/interfaces/distribution-and-database-support-matrix.md`, `docs/redesign/interfaces/cli-surface-and-operator-workflows.md`, `docs/redesign/interfaces/cli-api-and-package-shape.md`, `docs/redesign/how-to/install-and-onboard.md`, `docs/redesign/how-to/use-postgres.md`, `docs/redesign/how-to/run-local-sqlite.md`, `docs/redesign/how-to/publish-a-release.md`, `docs/redesign/tutorials/onboard-locally.md`, `docs/redesign/tutorials/end-to-end-redesign-walkthrough.md` | release-architecture mermaid diagram and DB-lane how-to examples in the owner pages above | `docs/current/interfaces/cli-surface-and-config-precedence.md`, `docs/current/interfaces/packaging-cli-and-install.md`, `docs/current/operations/install-and-start-local.md`, `docs/current/operations/verify-current-install-and-runtime.md`, `docs/current/operations/run-docker-postgres-verification.md` | Phase 5B | `pyproject.toml`, `Makefile`, `scripts/*`, install or release or onboarding docs, archive cleanup, root or router docs that point to final canon | package and install smoke, reset smoke, docs routing and validation, SQLite local smoke, Postgres + Docker strong verification, all viable e2e lanes when packaging or reset can invalidate earlier proof |

## Stop rule

If a planned implementation slice cannot name:

- a redesign owner row here
- any required supporting redesign reads for the selected phase
- the companion examples or diagrams it must read
- the current-contrast pages it must check
- the code surfaces it may change
- the proof gates it must pass

stop and patch this map or the phase page before proceeding.
