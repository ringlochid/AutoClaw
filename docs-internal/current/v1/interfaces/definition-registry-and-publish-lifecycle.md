# Current definition registry and publish lifecycle

Status: Current

Last verified: 2026-06-27

This page defines the current DB-backed definition registry lifecycle for roles, policies, and workflows.

## Current definition truth

Current file discovery is only a seed source.

Current live definition truth after seeding or internal upsert is the DB-backed registry:

- definition rows
- revision rows
- `current_revision_no`
- revision `content_hash`
- revision `source_path`

Current compiler and runtime launch paths read current definition truth from those DB rows.

The packaged resource mirror is the committed authored and shipped bootstrap input. Explicit local override trees may be used only when selected by the caller. Neither source outranks the DB-backed registry after seeding.

## Current discovery and seed

Current seeding behavior:

- choose the seed root using the precedence rules in `definition-precedence-and-skill-version-defaults.md`
- parse seed YAML into role, policy, and workflow definition models
- create revision `1` for new definition keys
- for existing definition keys, reuse an existing revision when the candidate content hash already exists
- for existing definition keys, append a new immutable revision when the candidate content hash is new
- advance `current_revision_no` only when the current revision is still on the same seed track

Normal shipped init/reset/upgrade paths seed from the packaged mirror. Explicit override trees matter only when selected by the caller. Missing packaged seeds fail the shipped path instead of triggering repo fallback.

Current shipped entrypoints that seed the registry include:

- `autoclaw init`
- `autoclaw db upgrade`
- `autoclaw db reset`
- `seed_definition_registry()`

## Current write lifecycle

Current write lifecycle is internal-service-driven:

1. load the current definition row under lock when it exists
2. hash the candidate content
3. if the content is unchanged, return the current revision without creating a new one
4. otherwise allocate the next revision number
5. validate workflow candidates against current role/policy registry truth
6. insert the new revision and advance `current_revision_no`

Current internal write functions are:

- `upsert_role_definition()`
- `upsert_policy_definition()`
- `upsert_workflow_definition()`

Current shipped reseeding does not use that normal update path for existing keys. `seed_definition_registry()` calls the upsert functions with `allow_existing_update=False`, which means:

1. if a definition key is missing, create revision `1`
2. if a matching content hash already exists for that key, reuse the matching revision instead of creating a duplicate
3. if the packaged seed content is new for that key, append a new immutable revision
4. only advance `current_revision_no` when the current revision is still on the same seed track
5. preserve newer controller-selected currentness when reseed should not promote the packaged revision

## Current validation and currentness rules

Current workflow upserts can fail without advancing currentness when:

- the workflow references a missing role or policy
- the workflow violates node-kind compatibility
- the workflow violates dependency or schema rules

Current reseeding preserves controller-owned currentness by refusing to hijack a newer current revision that no longer belongs to the same seed track.

## Current HTTP surface fact

Current shipped API routes still keep registry truth under `/definitions` and task start under `/tasks/start`, but the tree now also exposes backend-owned authoring draft routes under `/authoring/definition-draft-sets/*`.

Current shipped authoring facts are:

- draft sets live under the configured data dir at `drafts/definitions/<draft_set_id>/`
- `GET /authoring/definition-draft-sets/{draft_set_id}` returns saved YAML bodies, saved normalized JSON shadows, saved baseline bodies, and saved preview task-compose state for the Definition Editor-style UI
- draft-set save/reset/re-materialize writes mutate only backend-owned local draft state, not registry truth
- once a draft set reaches `applied`, any later local draft mutation such as file save, preview-task-compose write, reset, materialize, or re-materialize-current reopens the draft set to `open`
- `POST /authoring/definition-draft-sets/{draft_set_id}/apply` publishes through the same DB-backed definition upsert truth used elsewhere and may optionally start a task from newly current registry truth after successful apply
- invalid saved preview task-compose input is warning-only authoring context unless that apply request also asks to start a task
- when the optional post-apply task start fails after publish committed, the route still returns `status=applied` plus task-start failure detail instead of surfacing a false apply failure
- mounted operator MCP exposes only read-only draft-set list/detail inspection; mutating draft authoring remains on the HTTP `/authoring` workbench API

Registry lifecycle is therefore no longer only an internal service plus CLI/init concern; current HTTP also exposes a local pending-authoring lane over that same registry truth.

## Current skill-specific rule

Current registry lifecycle does not include live skill registry rows or `skill_refs` writes in the shipped tree.

## Minimal example

```text
autoclaw init
  -> create schema
  -> seed the packaged definition mirror
  -> registry current_revision_no now points at revision 1 for shipped seeds

internal workflow update
  -> validate candidate
  -> insert revision 2
  -> advance workflow_definitions.current_revision_no to 2

later shipped reseed of that same workflow key
  -> reuse the matching revision if the hash already exists
  -> append a new packaged revision if the hash is new
  -> keep revision 2 current if controller currentness moved off the seed track
```

## Evidence

- inspected code in `apps/api/src/autoclaw/definitions/registry/seeds.py`
- inspected code in `apps/api/src/autoclaw/definitions/registry/current.py`
- inspected code in `apps/api/src/autoclaw/definitions/registry/upsert.py`
- inspected code in `apps/api/src/autoclaw/definitions/authoring/service.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/authoring.py`
- inspected code in `apps/api/src/autoclaw/interfaces/cli/__init__.py`
- inspected tests in `apps/api/tests/integration/definition_registry/test_registry_db.py`
- inspected tests in `apps/api/tests/integration/public_surfaces/test_definition_authoring_api.py`
- inspected tests in `apps/api/tests/unit/cli/**`

## Related current pages

- `definition-and-task-compose-yaml-contract.md`
- `definitions-compiler-and-launch.md`
- `definition-precedence-and-skill-version-defaults.md`

## Design pointer

For the target definition registry and guarded publish contract, see `../../../design/v1/interfaces/definition-registry-and-upload-contract.md` and `../../../design/v1/interfaces/guarded-registry-and-runtime-writes.md`.
