# `old_version_docs` disposition

Status: Reference

This page records how the retained `old_version_docs` source pack was absorbed into the canonical `..` root.

## File-level disposition

### Root files

| Source file | Disposition |
|---|---|
| `api-route-trust-lanes.md` | absorbed into `../current/interfaces/api-trust-lanes.md` |
| `README.md` | rewritten into `../current/README.md` and `source-packs/README.md` |
| `refactor-checklist-runtime-stabilization.md` | archive only |
| `registry-definition-precedence.md` | absorbed into `../current/interfaces/definition-precedence-and-skill-version-defaults.md` |

### `architecture/`

| Source file | Disposition |
|---|---|
| `architecture/01-system-overview.md` | mined partially into `../current/architecture/current-architecture.md`, `../redesign/architecture/runtime-records-and-lifecycle.md`, and `../redesign/decisions/ADR-0001-controller-first-relational-runtime-truth.md` |
| `architecture/02-authoring-compiler-runtime.md` | mined partially into `../current/interfaces/definitions-compiler-and-launch.md`, `../redesign/workflows/workflow-definition-schema.md`, `../redesign/workflows/task-compose-schema.md`, `../redesign/architecture/filesystem-layout-and-roots.md`, `../redesign/workflows/compiler-contract-and-launch-materialization.md`, and `../redesign/architecture/task-root-layout-and-generated-files.md` |
| `architecture/03-control-plane-and-query-model.md` | mined partially into `../redesign/architecture/runtime-records-and-lifecycle.md`, `../redesign/architecture/runtime-boundary-and-controller-loop-contract.md`, `../redesign/architecture/runtime-database-and-object-contract.md`, and `../redesign/decisions/ADR-0001-controller-first-relational-runtime-truth.md` |
| `architecture/04-operator-console-model.md` | mined partially into `../current/architecture/runtime-read-models-and-operator-surfaces.md`, `../redesign/interfaces/human-and-operator-control-surface.md`, `../redesign/interfaces/cli-surface-and-operator-workflows.md`, and `../redesign/interfaces/api-surface-and-trust-lane-map.md` |
| `architecture/05-diagrams-and-mermaid.md` | absorbed into `STYLE_GUIDE.md` |
| `architecture/06-openclaw-runtime-bridge.md` | mined partially into `../current/architecture/openclaw-and-bridge-plugin.md`, `../current/architecture/openclaw-dispatch-and-session-contract.md`, `../redesign/architecture/openclaw-worker-and-gateway-contract.md`, `../redesign/architecture/openclaw-session-and-continuity-contract.md`, and `../redesign/explanation/06-why-openclaw-is-the-worker-direction.md` |
| `architecture/README.md` | rewritten into `../current/README.md` and `../redesign/architecture/README.md` |

### `decisions/`

| Source file | Disposition |
|---|---|
| `decisions/ADR-0001-controller-first-db-truth.md` | rewritten into `../redesign/decisions/ADR-0001-controller-first-relational-runtime-truth.md` |
| `decisions/ADR-0002-deterministic-compiler-hybrid-planner.md` | rewritten into `../redesign/decisions/ADR-0002-deterministic-compiler-and-immutable-compiled-plans.md` |
| `decisions/ADR-0003-parent-supervisor-main-loop-kernel.md` | replaced by `../redesign/decisions/ADR-0003-parent-owned-execution-tree-and-boundary-advancement.md` |
| `decisions/ADR-0004-openclaw-owns-skill-packages.md` | rewritten into `../redesign/decisions/ADR-0004-openclaw-first-worker-boundary-and-skill-ownership.md` |
| `decisions/ADR-0005-relational-runtime-model-and-iteration-loops.md` | mined partially into `../redesign/decisions/ADR-0001-controller-first-relational-runtime-truth.md`, `../redesign/decisions/ADR-0003-parent-owned-execution-tree-and-boundary-advancement.md`, and `../redesign/architecture/runtime-database-and-object-contract.md` |
| `decisions/ADR-0006-async-first-python-stack.md` | mined partially into `AGENT.md`, `STYLE_GUIDE.md`, and `../execution/gates/code-quality-gate.md` |
| `decisions/ADR-0007-task-owned-resource-roots-and-flow-owned-manifests.md` | rewritten into `../redesign/decisions/ADR-0005-task-owned-roots-and-runtime-generated-projections.md` |
| `decisions/README.md` | rewritten into `../redesign/decisions/README.md` |

### `flows/`

| Source file | Disposition |
|---|---|
| `flows/00-data-example.md` | mined partially into `../current/architecture/runtime-control-plane.md` and `../current/architecture/current-architecture.md` |
| `flows/01-definition-to-runtime.md` | mined partially into `../current/interfaces/definitions-compiler-and-launch.md` and `../redesign/tutorials/create-a-definition-and-run-a-task.md` |
| `flows/02-default-runtime-lifecycle.md` | mined partially into `../current/architecture/runtime-control-plane.md` and `../current/architecture/openclaw-dispatch-and-session-contract.md` |
| `flows/03-plan-patch-and-safe-recompile.md` | mined partially into `../current/architecture/parent-retry-and-operator-control.md` and `../redesign/decisions/ADR-0006-revision-safe-replan-and-adopt.md` |
| `flows/04-approval-and-watchdog.md` | mined partially into `../current/architecture/watchdog-and-runtime-monitoring.md`, `../current/operations/inspect-approvals-and-watchdog.md`, and `../redesign/architecture/watchdog-and-recovery-contract.md` |
| `flows/05-mvp-builder-pack.md` | mined partially into `../redesign/workflows/examples/minimal.md` and `../redesign/tutorials/end-to-end-redesign-walkthrough.md` |
| `flows/06-max-complexity-workflow.md` | mined partially into `../current/architecture/parent-retry-and-operator-control.md` and `../redesign/workflows/examples/maximal.md` |
| `flows/06b-max-complexity-workflow-full.md` | mined partially into `../redesign/workflows/examples/maximal.md`; original archived |
| `flows/07-controller-driven-implementation-loop.md` | mined partially into `../redesign/architecture/runtime-boundary-and-controller-loop-contract.md` and `../redesign/decisions/ADR-0003-parent-owned-execution-tree-and-boundary-advancement.md` |
| `flows/README.md` | rewritten into `../current/README.md`, `../redesign/workflows/examples/minimal.md`, `../redesign/workflows/examples/normal.md`, and `../redesign/workflows/examples/maximal.md` |

### `e2e/`

| Source file | Disposition |
|---|---|
| `e2e/phase8-happy-path.md` | mined partially into `../current/architecture/openclaw-dispatch-and-session-contract.md` and `../current/operations/use-the-openclaw-bridge-plugin.md` |
| `e2e/fixtures/phase8-happy-path.start-flow.json` | archive only |

### `roadmap/`

| Source file | Disposition |
|---|---|
| `roadmap/00-principles.md` | archive only |
| `roadmap/01-phase-1-kernel-and-data-model.md` | archive only |
| `roadmap/02-phase-2-registry-and-compiler.md` | archive only |
| `roadmap/03-phase-3-runtime-and-openclaw-integration.md` | archive only |
| `roadmap/04-phase-4-operator-console.md` | archive only |
| `roadmap/05-phase-5-replan-watchdog-and-approval.md` | archive only |
| `roadmap/06-phase-6-advanced-hierarchy-and-packs.md` | archive only |
| `roadmap/06.5-phase-6.5-pre-phase-7-stabilization.md` | archive only |
| `roadmap/07-phase-7-controller-driven-looping-and-governance.md` | archive only |
| `roadmap/08-phase-8-production-openclaw-bridge-and-native-plugin-adapter.md` | archive only |
| `roadmap/09-phase-9-local-first-packaging-and-distribution.md` | archive only |
| `roadmap/10-phase-10-effective-node-compiler-semantics-and-authoring-safety.md` | archive only |
| `roadmap/11-phase-11-graph-operator-surfaces-and-definition-authoring.md` | archive only |
| `roadmap/12-phase-12-openclaw-operator-plugin-and-definition-automation.md` | archive only |
| `roadmap/13-phase-13-task-compose-launch-refactor-and-runtime-cleanup.md` | archive only |
| `roadmap/13-phase-13a-runtime-bundle-removal-and-persistence-truth.md` | archive only |
| `roadmap/13-phase-13b-task-compose-launch-refactor.md` | archive only |
| `roadmap/13-phase-13c-runtime-truth-policy-replan-and-verification.md` | archive only |
| `roadmap/backlog.md` | archive only |
| `roadmap/current.md` | archive only |
| `roadmap/next.md` | archive only |
| `roadmap/README.md` | archive only |
| `roadmap/suggestion.md` | archive only |

## Canon rule

The old pack remains a source input only.

It must not be treated as a second live canonical docs surface beside `..`.
