# Current definitions, compiler, and launch baseline

Status: Current

Last verified: 2026-05-12

Current authoring and launch behavior is tree-only, registry-backed, and runtime-service-driven.

For the exact current role, policy, workflow, and task-compose YAML contract, see `definition-and-task-compose-yaml-contract.md`.

## Current definition sources

Current committed authored and shipped bootstrap seeds live in the packaged resource tree:

- `apps/api/src/autoclaw/definitions/seeds/**`

A caller may still pass an explicit local `definitions_root` override into `seed_definition_registry()`. That override is not the shipped default, and no repo-root definitions mirror is required by shipped paths.

`seed_definition_registry()` uses the packaged resource tree on shipped paths. Missing packaged seed files fail the shipped seed path. The shipped init, upgrade, or reset path fails instead of falling back to the repo mirror.

## Current compiler facts

Current compiler responsibilities include:

- validating the tree-only workflow definition
- resolving current role and policy revisions from the DB-backed registry
- deriving dependency edges from `consumes.artifacts` and `consumes.criteria`
- normalizing the workflow into a compiled plan

Current compiler entrypoints include:

- `app.compiler.compile_workflow()`
- `app.registry.compile_current_workflow()`
- `app.registry.compile_current_workflow_launch_snapshot()`

Primary files:

- `apps/api/src/autoclaw/definitions/compiler/__init__.py`
- `apps/api/src/autoclaw/definitions/compiler/compile.py`
- `apps/api/src/autoclaw/definitions/compiler/normalize.py`
- `apps/api/src/autoclaw/definitions/registry/current.py`

Current compiled plans are persisted as:

- `CompiledPlanModel`
- `CompiledPlanNodeModel`
- `CompiledPlanEdgeModel`

Current compiled nodes pin current role and policy revision numbers at compile time.

## Current launch facts

Current launch is controller-owned runtime behavior exposed through the public task-start route plus internal runtime services.

Current public task-start route is:

- `POST /tasks/start`

Primary launch chain and entrypoints are:

- `apps/api/src/autoclaw/interfaces/http/routers/tasks.py::start_task()`
- `apps/api/src/autoclaw/definitions/registry/task_start.py::start_task_from_definition_service()`
- `apps/api/src/autoclaw/runtime/launch/service.py::launch_task_runtime()`
- `apps/api/src/autoclaw/runtime/launch/persistence/runtime.py::persist_bootstrap_runtime_from_precomputed()`
- `apps/api/src/autoclaw/runtime/launch/bootstrap/projection.py::build_bootstrap_runtime_projection_result()`

Current launch behavior:

- loads the current workflow revision plus current role/policy revisions from the registry
- compiles the current workflow snapshot
- persists task, task-compose, compiled-plan, flow, flow-node, flow-edge, assignment, attempt, dispatch, and binding rows
- materializes task-root projections such as the workflow manifest, assignment, and prompt artifact
- opens the first/root dispatch before returning task-start readback

Current launch input is:

- `TaskStartRequest` over the authored `TaskComposeInput` body on the public route
- `RuntimeLaunchInput`
- `TaskComposeInput`
- an explicit `task_id`
- an explicit `task_root`
- a `compiler_version`

The shipped router currently has no public registry validation route.

## Current runtime-materialization facts

Current runtime launch materializes the full current flow revision, not a lazy subtree-only slice.

Current launch also has one intentional limit:

- automatic assignment projection is only implemented for the launch/root path
- later non-root assignments are created explicitly by current parent/root tool calls

## Current DB truth

Current compiler and launch paths read current definition truth from the registry tables, not directly from repo-local YAML files, once the registry has been seeded.

Explicit seed override trees remain seed inputs only. Later compile and launch paths do not reread local YAML files as live currentness authority.

Current shipped reseeding is also intentionally conservative. When a seeded role, policy, or workflow key already exists in the registry, `seed_definition_registry()` reuses an existing matching revision when the content hash already exists, appends a new immutable revision when packaged seed content is new, and only advances `current_revision_no` when the current revision is still on the same seed track.

Current launch also pins:

- workflow definition revision
- role revision numbers
- policy revision numbers

into compiled-plan and flow-node runtime rows.

## Unsafe old-doc warning

Do not reuse older current docs that teach:

- flat `skill_refs`-driven authoring
- `/tasks/composes/start`
- launch through `runtime/runner.py`
- repo-file authority after registry bootstrap

Those shapes do not match the shipped tree anymore.

## Design pointer

For the target authoring/compiler model, see `../../../design/v1/workflows/compiler-contract-and-launch-materialization.md`, `../../../design/v1/workflows/workflow-definition-schema.md`, `../../../design/v1/workflows/task-compose-schema.md`, and `../../../execution/v1/maps/current-to-target-mapping.md`.

## Evidence

- inspected code in `apps/api/src/autoclaw/definitions/registry/seeds.py`
- inspected code in `apps/api/src/autoclaw/definitions/registry/current.py`
- inspected code in `apps/api/src/autoclaw/definitions/registry/upsert.py`
- inspected code in `apps/api/src/autoclaw/interfaces/cli/__init__.py`
- inspected code in `apps/api/src/autoclaw/runtime/launch/service.py`
- inspected code in `apps/api/src/autoclaw/runtime/launch/persistence/runtime.py`
- inspected code in `apps/api/src/autoclaw/runtime/launch/bootstrap/projection.py`
- inspected tests in `apps/api/tests/integration/definition_registry/test_registry_db.py`
- inspected tests in `apps/api/tests/integration/definition_registry/test_launch_snapshot.py`
- inspected tests in `apps/api/tests/integration/bootstrap/test_bootstrap.py`
