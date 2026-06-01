# Current definition registry and publish lifecycle

Status: Current

Last verified: 2026-05-12

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

The packaged resource mirror is the shipped bootstrap input. The repo-root `definitions/**` tree is a repo-local authored fixture and example mirror. Neither tree outranks the DB-backed registry after seeding.

## Current discovery and seed

Current seeding behavior:

- choose the seed root using the precedence rules in `definition-precedence-and-skill-version-defaults.md`
- parse seed YAML into role, policy, and workflow definition models
- create revision `1` for new definition keys
- for existing definition keys, reuse an existing revision when the candidate content hash already exists
- for existing definition keys, append a new immutable revision when the candidate content hash is new
- advance `current_revision_no` only when the current revision is still on the same seed track

Normal shipped init/reset/upgrade paths seed from the packaged mirror. The repo-root mirror matters only as an explicit override. Missing packaged seeds fail the shipped path instead of triggering repo fallback.

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

Current shipped API routes do not expose registry draft, publish, validate, or bootstrap endpoints.

The current router has no shipped registry route family and no public definition authoring routes.

Registry lifecycle is currently an internal service plus CLI/init concern.

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

- inspected code in `apps/api/app/registry/seeds.py`
- inspected code in `apps/api/app/registry/current.py`
- inspected code in `apps/api/app/registry/upsert.py`
- inspected code in `apps/api/app/cli.py`
- inspected tests in `apps/api/tests/integration/definition_registry/test_registry_db.py`
- inspected tests in `apps/api/tests/unit/test_cli.py`

## Related current pages

- `definition-and-task-compose-yaml-contract.md`
- `definitions-compiler-and-launch.md`
- `definition-precedence-and-skill-version-defaults.md`

## Design pointer

For the target definition registry and guarded publish contract, see `../../../design/v1/interfaces/definition-registry-and-upload-contract.md` and `../../../design/v1/interfaces/guarded-registry-and-runtime-writes.md`.
