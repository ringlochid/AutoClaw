# Current registry bootstrap ingest and task file upload

Status: Current

Last verified: 2026-04-25

This page owns two different current file-entry behaviors:

- registry bootstrap ingest
- task-owned file upload into task roots

They are not the same surface.

## Ownership rule

Use this page for the current split between:

- registry/bootstrap definition ingest
- task-owned uploads under a task root

Use `definition-registry-and-publish-lifecycle.md` for current draft, validate, publish, and registry lifecycle behavior.

## Current registry bootstrap ingest

Current definition ingest is primarily bootstrap/import from discovered YAML files.

Current real implementation includes:

- packaged definitions
- filesystem override root
- internal bootstrap route

## Current task file upload

Current task file upload lives in `upload_task_file(...)` and the `/tasks/{task_id}/uploads` routes.

This is a task-owned content placement surface, not a registry definition ingest surface.

## Current upload alias table

Current supported task upload target aliases are:

- `workspace_docs`
- `primary_workspace`
- `context_docs`
- `primary_context`
- `manifest_bundle`
- `manifest_root`

These resolve onto current task-owned materialized roots:

- `workspace/`
- `context/`
- `manifests/`

## Current path-safety rules

Current upload path handling enforces:

- relative path only
- no absolute path
- no empty, `.`, or `..` segments
- destination must stay under the task-owned root
- destination must stay under the allowed binding root

Current upload therefore rejects path escape and root escape.

## Current upload result

Current task upload returns:

- task id
- canonical target slot
- binding role
- relative path
- storage URI
- content type
- size bytes
- sha256

Current upload also refreshes task-compose materialization state through `ensure_task_compose_for_task(...)`.

## Non-owner standalone import/export note

Repository scripts `autoclaw-main/scripts/import_definitions.py` and `autoclaw-main/scripts/export_definitions.py` exist as implementation helpers only.

They do not define a supported current product surface and should not be cited as the current interface contract.

## Current write ownership

Current task uploads are a task/operator content surface.

They are not equivalent to:

- publishing a `ContextItem`
- projecting a manifest
- writing runtime truth directly
- importing registry definitions

## Minimal example

```text
definition ingest today
  -> packaged/filesystem discovery
  -> internal bootstrap

task file upload today
  -> POST /tasks/{task_id}/uploads
  -> target_slot=context_docs
  -> write file under task-owned context root
```

## Expanded example

```text
upload task file
  -> resolve target alias to binding role and directory
  -> normalize relative path
  -> reject absolute or escaping paths
  -> write file into workspace/context/manifests
  -> return storage_uri + sha256
  -> refresh task compose materialization
```

## Evidence

- inspected code in `autoclaw-main/apps/api/app/services/task_service.py`
- inspected code in `autoclaw-main/apps/api/app/api/routes/tasks.py`
- inspected code in `autoclaw-main/apps/api/app/runtime/resources.py`
- inspected scripts in `autoclaw-main/scripts/import_definitions.py` and `autoclaw-main/scripts/export_definitions.py`

## Related current pages

- `../architecture/task-roots-and-materialized-paths.md`
- `definition-registry-and-publish-lifecycle.md`
- `api-surface-and-route-map.md`

## Redesign pointer

For the target file-bundle-first definition ingest contract and the separate target upload surface, see `../../redesign/interfaces/definition-ingest-and-upload-contract.md`.
