# Current definitions, compiler, and launch baseline

Status: Current

Last verified: 2026-04-25

Current authoring and launch behavior is still `skill_refs`-based and OpenClaw-shaped.

For the exact current role, policy, workflow, and task-compose YAML contract, see `definition-and-task-compose-yaml-contract.md`.

## Current definition sources

Current definitions live in:

- `autoclaw-main/definitions/**`
- `autoclaw-main/apps/api/app/resources/definitions/**`

Current examples still use:

- `skill_refs`
- OpenClaw-shaped runtime names
- flagship flow shapes that do not yet match the redesign target

## Current compiler facts

Current compiler responsibilities include:

- workflow seed parsing
- inheritance and merge behavior
- effective-node merge semantics
- `skill_refs` merge and resolution into `skill_bindings`
- graph and resource validation

Current compiler pipeline is:

1. YAML and registry definitions are read into workflow seed content
2. the workflow is resolved against role, policy, and skill definitions
3. the resolved workflow is validated
4. the resolved workflow is normalized into a compiled plan
5. the compiled plan is persisted as:
   - `CompiledPlan`
   - `CompiledPlanNode`
   - `CompiledPlanEdge`

Current compiled nodes carry fields such as:

- `node_key`
- `parent_node_key`
- `role_version_id`
- `policy_version_id`
- `mode`
- `order_index`
- `skill_bindings`
- `effective_payload`

Primary files:

- `autoclaw-main/apps/api/app/compiler/resolve.py`
- `autoclaw-main/apps/api/app/compiler/validate.py`
- `autoclaw-main/apps/api/app/compiler/nesting.py`
- `autoclaw-main/apps/api/app/compiler/normalize.py`
- `autoclaw-main/apps/api/app/compiler/lower.py`
- `autoclaw-main/apps/api/app/services/compiler_service.py`

## Current launch facts

Task compose is a current public launch surface.

Primary files:

- `autoclaw-main/apps/api/app/api/routes/tasks.py`
- `autoclaw-main/apps/api/app/runtime/runner.py`
- `autoclaw-main/apps/api/app/cli.py`

Current launch behavior:

- validates task-compose YAML
- creates task and task-resource records
- initializes task roots from compose defaults and materialization helpers
- compiles or loads the current compiled plan
- materializes runtime graph rows as:
  - `Flow`
  - `FlowRevision`
  - `FlowNode`
  - `FlowEdge`
- starts flows through current compiled-plan/runtime semantics

Current runtime uses full active-revision graph loading, not subtree-only runtime materialization.

Current replan also creates a new candidate full revision and swaps the active revision pointer instead of patching active nodes in place.

## Unsafe old-doc warning

Do not reuse these repo-local historical docs as canonical current semantics without rewrite:

- `../../../autoclaw-main/docs/flows/06-max-complexity-workflow.md`
- `../../../autoclaw-main/docs/flows/06b-max-complexity-workflow-full.md`
- `../../../autoclaw-main/docs/decisions/ADR-0003-parent-supervisor-main-loop-kernel.md`

They still teach stale parent semantics such as `can_spawn_children`.

## Redesign pointer

For the current precedence rules, see `definition-precedence-and-skill-version-defaults.md`.

For the current definition lifecycle, ingest, and API/CLI surfaces, see `definition-registry-and-publish-lifecycle.md`, `current-definition-bootstrap-and-task-upload.md`, `api-surface-and-route-map.md`, and `cli-surface-and-config-precedence.md`.

For the exact current schema and shipped-subset split, see `definition-and-task-compose-yaml-contract.md`.

For the target authoring/compiler model, see `../../redesign/workflows/compiler-contract-and-launch-materialization.md`, `../../redesign/workflows/workflow-definition-schema.md`, `../../redesign/workflows/task-compose-schema.md`, and `../../execution/maps/current-to-target-mapping.md`.

## Evidence

- inspected code in `autoclaw-main/apps/api/app/compiler/resolve.py`, `validate.py`, `nesting.py`, `normalize.py`, `lower.py`, and `services/compiler_service.py`
- inspected current launch entrypoints in `autoclaw-main/apps/api/app/api/routes/tasks.py`, `autoclaw-main/apps/api/app/runtime/runner.py`, and `autoclaw-main/apps/api/app/cli.py`
- inspected source-pack docs in `../../archive/source-packs/old_version_docs/architecture/02-authoring-compiler-runtime.md`, `../../archive/source-packs/old_version_docs/flows/01-definition-to-runtime.md`, and `../../archive/source-packs/old_version_docs/flows/03-plan-patch-and-safe-recompile.md`
- did not execute tests for this page
