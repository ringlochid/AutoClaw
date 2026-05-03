# Repo salvage matrix

Status: Reference

This matrix is the searchable owner for Phase 0.5 keep/rewrite/delete decisions.

Use only these fixed labels:

- `keep`
- `rewrite in place`
- `delete`
- `quarantine support-only`
- `plugin rebuild`

## Current workspace note

- the live backend source root in this checkout is `apps/api/app/*`
- the live backend test root in this checkout is `apps/api/tests/*`
- console, definitions, scripts, and packaging surfaces live under `apps/console/*`, `definitions/*`, `scripts/*`, `pyproject.toml`, and `Makefile`
- historical `autoclaw-main/...` labels in execution docs refer to those repo-root surfaces until Phase 0 router cleanup realigns the shared map
- no `autoclaw-bridge-plugin-main/...` source tree exists in this checkout; plugin cleanup is a docs-driven inventory decision and Phase 4B starts from a target-only rebuild boundary

## Main application surfaces

| Subsystem                               | Current signal                                                                                                             | Decision                  | Reason                                                                                   | Target owner phase |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------- | ---------------------------------------------------------------------------------------- | ------------------ |
| API route shell and dependency wiring   | repo-root `apps/api/app/api/*` keeps useful FastAPI router, presenter, auth, and dependency shell                         | `rewrite in place`        | route structure is reusable, but target nouns and trust-lane boundaries are different    | Phase 3-5A         |
| public task routes                      | `apps/api/app/api/routes/tasks.py` still teaches old task upload and `/tasks/composes/start` launch                       | `delete`                  | target task-start contract is incompatible                                               | Phase 5A           |
| public/internal flow routes             | `apps/api/app/api/routes/flows.py` still owns `/flows/*`, retry, raw slices, watchdog helpers, and mixed operator/debug reads | `rewrite in place`        | shell may remain, but contract must be replaced aggressively                             | Phase 3-5A         |
| approval route family                   | `apps/api/app/api/routes/approvals.py` and approval-facing runtime reads preserve approval-era product nouns              | `delete`                  | frozen v1 removes approval runtime lanes from the standard surface                       | Phase 0.5          |
| runtime schemas and read models         | `apps/api/app/schemas/*` and `runtime/read_models.py` still carry flow-first, approval, manifest-ack, and session-era shapes | `rewrite in place`        | too much target-incompatible contract shape survives                                     | Phase 2-5A         |
| runtime control services                | `apps/api/app/runtime/*` includes approvals, callback bindings, checkpoints, packaging, replan, watchdog, and mixed truths | `rewrite in place`        | useful shell exists, but major runtime semantics are stale                               | Phase 2-4B         |
| runtime DB models                       | `apps/api/app/db/models/*` still encode old resource/task/runtime truth and stale enums                                   | `rewrite in place`        | infra patterns are useful, contract shape is not                                         | Phase 2-5A         |
| compiler core                           | `apps/api/app/compiler/*` is structurally useful, but stale edges, extends, task defaults, and skill-ref logic survive   | `rewrite in place`        | keep compiler shell, replace contract logic                                              | Phase 1            |
| registry services                       | `apps/api/app/registry/*` and `app/services/registry_service.py` keep useful persistence/query shell, but old skill and draft/publish surfaces survive | `rewrite in place`        | definitions lifecycle remains, stale skill and publish semantics do not                  | Phase 1 and 5A     |
| definitions roots and packaged mirrors  | repo-root `definitions/*` and `apps/api/app/resources/definitions/*` are useful discovery/package shells, but still carry approval and skill-era content | `rewrite in place`        | keep discovery/package shell, replace target definition content and mirrored resources   | Phase 1 and 5B     |
| Alembic roots and migration mirrors     | both `apps/api/alembic/*` and `apps/api/app/resources/alembic/*` exist today                                              | `keep`                    | Phase 0.5 freezes one live migration authority while keeping the packaged mirror bounded | Phase 0.5 and 5B   |
| CLI/config/init/package shell           | repo-root `pyproject.toml`, `Makefile`, `scripts/*`, and `apps/api/app/cli.py` have strong infra value                   | `keep`                    | config, install, doctor, serve, and packaging scaffolding are worth preserving           | Phase 0.5 and 5B   |
| console                                 | repo-root `apps/console/*` is tied to stale runtime and operator route families                                           | `quarantine support-only` | do not let current console behavior define target runtime shape during cleanup           | Later optional     |
| historical subrepo path references      | current docs still cite `autoclaw-main/...` and `autoclaw-bridge-plugin-main/...` even though the checkout is repo-root  | `quarantine support-only` | canonical docs pack owns target truth; cleanup docs must normalize these references      | Phase 0.5          |

## Plugin surfaces

| Subsystem                 | Current signal                                                                 | Decision         | Reason                                                                 | Target owner phase |
| ------------------------- | ------------------------------------------------------------------------------ | ---------------- | ---------------------------------------------------------------------- | ------------------ |
| local plugin source tree  | no repo-local `autoclaw-bridge-plugin-main` source tree exists in this checkout | `plugin rebuild` | no local implementation survives to salvage; Phase 4B starts near-greenfield | Phase 4B           |
| plugin tool inventory     | current docs still describe approval, raw-slice, skill-write, and runtime-bundle families | `plugin rebuild` | target plugin contract changed too much for safe incremental cleanup   | Phase 4B           |
| plugin test harness       | no repo-local TS or plugin harness is present in this checkout                  | `delete`         | there is no local harness to preserve; new harness should land with the rebuild | Phase 4B           |
| old plugin contract tests | no live plugin tests exist locally, but stale tool families still appear in docs and old expectations | `delete`         | keep stale plugin expectations out of the cleanup baseline             | Phase 0.5          |

## Test inventory defaults

| Test family                                | Current signal                                                                 | Decision                | Reason                                                                  | Target owner phase |
| ------------------------------------------ | ------------------------------------------------------------------------------ | ----------------------- | ----------------------------------------------------------------------- | ------------------ |
| config, health, and package-entrypoint unit tests | `apps/api/tests/unit/test_config.py`, `test_health.py`, and `test_package_entrypoints.py` are redesign-agnostic infra smoke | `keep with small edits` | valuable infra coverage survives cleanup                                | Phase 0.5 and 5B   |
| console packaging smoke                     | `apps/api/tests/integration/test_console_packaging.py` proves packaged assets and reserved-route handling, but names stale route families | `keep with small edits` | keep packaging shell coverage while updating reserved route expectations | Phase 0.5 and 5B   |
| CLI init, service, and install smoke        | much of `apps/api/tests/unit/test_cli.py` covers init, config writing, and service rendering | `keep with small edits` | preserve install/bootstrap shell coverage, update frozen CLI nouns later | Phase 0.5 and 5A   |
| compiler schema and compile tests           | compiler unit/integration tests are structurally useful                         | `rewrite in place`      | target authoring contract is different                                  | Phase 1            |
| task-start and compiler API contract tests  | `test_task_api.py` and `test_compiler_api.py` still assert `/tasks/composes/start`, task uploads, and skill dependencies | `rewrite in place`      | coverage shell is useful, but public launch contract is wrong           | Phase 1 and 5A     |
| runtime and flow API contract tests         | `test_runtime_api.py`, `test_flow_runtime_db.py`, and `test_phase456_runtime_db.py` encode old flow, approval, worker-bundle, and watchdog shapes | `rewrite in place`      | coverage shell is useful, but runtime nouns and payloads are stale      | Phase 2-4B         |
| registry bootstrap DB smoke                 | `test_registry_bootstrap_db.py` proves reseed/idempotence shape, but still counts skill-era content | `rewrite in place`      | keep reset/bootstrap shell, replace stale definition expectations       | Phase 0.5 and 5A   |
| registry API and skill-binding tests        | `test_registry_api.py` still asserts `/registry/*`, draft/publish writes, bootstrap routes, skills, and audit flows | `rewrite in place`      | useful harness exists, but standard public contract is changing         | Phase 5A           |
| approval-era tests                          | runtime and DB tests still assert approval creation, resolve, and approval waits | `delete`                | target canon removes approval-era standard surfaces                     | Phase 0.5          |
| callback-binding lineage tests              | `test_callback_bindings.py` asserts manifest/session/ack lineage binding input  | `delete`                | target callback semantics remove those binding fields from live v1      | Phase 0.5          |
| skill-registry target tests                 | skill references and registry/compiled-plan skill binding coverage remain in compiler, registry, and runtime tests | `delete`                | target canon removed skills from the standard surface                   | Phase 0.5          |
| plugin tool inventory tests                 | no live plugin tests exist locally                                              | `delete`                | Phase 4B will introduce new target-only plugin coverage                 | Phase 4B           |

## Migration history

| Subsystem                 | Current signal                                                                                      | Decision                       | Reason                                                             | Target owner phase |
| ------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------ | ------------------------------------------------------------------ | ------------------ |
| current Alembic history   | `apps/api/alembic/versions/*` is the current CLI upgrade path and still encodes old contract truth | `delete` as redesign authority | replace with one new redesign baseline migration                   | Phase 0.5          |
| packaged Alembic mirror   | `apps/api/app/resources/alembic/versions/*` duplicates migration content for distribution          | `keep`                         | keep the packaged mirror, but do not treat it as separate authority | Phase 0.5 and 5B   |
| Alembic plumbing          | `apps/api/alembic/env.py`, CLI upgrade wiring, and package-data hooks remain useful infra          | `keep`                         | migration framework still useful                                   | Phase 0.5          |
