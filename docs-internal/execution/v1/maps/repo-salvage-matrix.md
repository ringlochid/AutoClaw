# Repo hard-reset matrix

Status: Reference

This matrix is the searchable owner for Phase 0.5 hard-reset decisions.

Use only these fixed labels:

- `delete now`
- `retain infra shell only`
- `plugin rebuild`

## Current workspace note

- the live backend source root in this checkout is `apps/api/app/*`
- the live backend test root in this checkout is `apps/api/tests/*`
- console, definitions, scripts, and packaging surfaces live under `apps/console/*`, `definitions/*`, `scripts/*`, `pyproject.toml`, and `Makefile`
- no `autoclaw-bridge-plugin-main/...` source tree exists in this checkout; plugin cleanup is a docs-driven inventory decision and Phase 4B starts from a target-only rebuild boundary

## Main application surfaces

| Subsystem | Current signal | Decision | Reason | Target owner phase |
| --- | --- | --- | --- | --- |
| API route shell and dependency wiring | repo-root `apps/api/app/api/*` still teaches stale route families and trust boundaries | `delete now` | no target-facing route shell survives unchanged | Phase 3-5A |
| public task routes | the legacy task-route family under `apps/api/src/autoclaw/interfaces/http/routers/*` still teaches old task upload and `/tasks/composes/start` launch | `delete now` | target task-start contract is incompatible | Phase 5A |
| public/internal flow routes | the legacy flow and runtime route shell under `apps/api/src/autoclaw/interfaces/http/routers/*` still teaches `/flows/*`, retry, raw slices, watchdog helpers, and mixed operator/debug reads | `delete now` | target runtime routes will be rebuilt from canon | Phase 3-5A |
| approval route family | legacy approval-facing route and runtime read shells under `apps/api/app/api/*` and `apps/api/src/autoclaw/runtime/*` preserve approval-era product nouns | `delete now` | frozen v1 removes approval runtime lanes from the standard surface | Phase 0.5 |
| runtime schemas and read models | `apps/api/app/schemas/*` and `runtime/read_models.py` still carry flow-first, approval, manifest-ack, and session-era shapes | `delete now` | stale contract shape dominates these surfaces | Phase 2-5A |
| runtime control services | `apps/api/src/autoclaw/runtime/*` includes approvals, callback bindings, checkpoints, packaging, replan, watchdog, and mixed truths | `delete now` | runtime behavior will be rebuilt from design canon | Phase 2-4B |
| runtime DB models | `apps/api/src/autoclaw/persistence/models/*` still encode old resource/task/runtime truth and stale enums | `delete now` | no target-facing schema survives the hard reset | Phase 2-5A |
| compiler core | `apps/api/src/autoclaw/definitions/compiler/*` is structurally useful, but stale edges, extends, task defaults, and skill-ref logic survive | `delete now` | current compiler behavior cannot be trusted | Phase 1 |
| registry services | `apps/api/src/autoclaw/definitions/registry/*` and `app/services/registry_service.py` keep old skill and draft/publish semantics alive | `delete now` | Phase 5A will rebuild public ingest from target canon | Phase 5A |
| definitions roots and packaged mirrors | repo-root `definitions/*` content and packaged mirrors still carry stale approval and skill-era assumptions | `delete now` | no definition content survives the hard reset | Phase 0.5 |
| migration roots and mirrors | `apps/api/alembic/*` and `apps/api/app/resources/alembic/*` are stale schema-history carriers | `delete now` | no migration history survives the hard reset | Phase 0.5 |
| CLI/config/init/package shell | repo-root `pyproject.toml`, `Makefile`, `scripts/*`, `apps/api/src/autoclaw/interfaces/cli/main.py`, and `apps/api/src/autoclaw/interfaces/cli/**` are needed to install, reset, and smoke the baseline | `retain infra shell only` | keep only the reset/package shell | Phase 0.5 and 5B |
| console | repo-root `apps/console/*` is tied to stale runtime and operator route families | `delete now` | current console cannot define target runtime shape | Later optional |

## Plugin surfaces

| Subsystem | Current signal | Decision | Reason | Target owner phase |
| --- | --- | --- | --- | --- |
| local plugin source tree | no repo-local `autoclaw-bridge-plugin-main` source tree exists in this checkout | `plugin rebuild` | no local implementation survives to salvage; Phase 4B starts near-greenfield | Phase 4B |
| plugin tool inventory | current docs still describe approval, raw-slice, skill-write, and runtime-bundle families | `plugin rebuild` | target plugin contract changed too much for safe incremental cleanup | Phase 4B |
| plugin test harness | no repo-local TS or plugin harness is present in this checkout | `plugin rebuild` | any future harness should land with the rebuild, not survive cleanup | Phase 4B |
| old plugin contract tests | no live plugin tests exist locally, but stale tool families still appear in docs and old expectations | `delete now` | keep stale plugin expectations out of the cleanup baseline | Phase 0.5 |

## Test inventory defaults

| Test family | Current signal | Decision | Reason | Target owner phase |
| --- | --- | --- | --- | --- |
| config, health, and package-entrypoint unit tests | `apps/api/tests/unit/test_config.py`, `test_health.py`, and `test_package_entrypoints.py` are design-agnostic infra smoke | `retain infra shell only` | valuable infra coverage survives cleanup | Phase 0.5 and 5B |
| console packaging smoke | the legacy console-packaging smoke in `apps/api/tests/integration/*` proves packaged assets and reserved-route handling, but names stale route families | `delete now` | current console behavior should not survive the hard reset | Phase 0.5 |
| CLI init, reset, and install smoke | parts of `apps/api/tests/unit/cli/**` cover config writing and install/reset shell behavior | `retain infra shell only` | preserve only reset/package smoke | Phase 0.5 and 5B |
| compiler schema and compile tests | compiler unit/integration tests are structurally useful | `delete now` | current compiler behavior cannot be trusted | Phase 1 |
| task-start and compiler API contract tests | `test_task_api.py` and `test_compiler_api.py` still assert `/tasks/composes/start`, task uploads, and skill dependencies | `delete now` | current public launch contract is wrong | Phase 1 and 5A |
| runtime and flow API contract tests | `test_runtime_api.py`, `test_flow_runtime_db.py`, and `test_phase456_runtime_db.py` encode old flow, approval, worker-bundle, and watchdog shapes | `delete now` | current runtime nouns and payloads are stale | Phase 2-4B |
| DB reset smoke | DB reset proof should reduce to empty-baseline reset smoke only | `retain infra shell only` | keep only DB reset smoke, delete registry-era expectations | Phase 0.5 |
| registry API and skill-binding tests | `test_registry_api.py` still asserts `/registry/*`, draft/publish writes, bootstrap routes, skills, and audit flows | `delete now` | standard public ingest is deferred to Phase 5A | Phase 5A |
| approval-era tests | runtime and DB tests still assert approval creation, resolve, and approval waits | `delete now` | target canon removes approval-era standard surfaces | Phase 0.5 |
| callback-binding lineage tests | `test_callback_bindings.py` asserts manifest/session/ack lineage binding input | `delete now` | target callback semantics remove those binding fields from live v1 | Phase 0.5 |
| skill-registry target tests | skill references and registry/compiled-plan skill binding coverage remain in compiler, registry, and runtime tests | `delete now` | target canon removed skills from the standard surface | Phase 0.5 |
| plugin tool inventory tests | no live plugin tests exist locally | `delete now` | Phase 4B will introduce new target-only plugin coverage | Phase 4B |
