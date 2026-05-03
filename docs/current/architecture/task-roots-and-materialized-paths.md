# Current task roots and materialized paths

Status: Current

Last verified: 2026-04-24

This page defines the current on-host task root behavior and the current materialized path model.

## Current default host root

Current code uses platformdirs-backed paths.

The default task data root is:

- `<platform user data dir>/tasks/`

Current path helpers live in `autoclaw-main/apps/api/app/paths.py`.

## Current task folder naming

Current task folders come from `task_slug(task_id, task_key)`.

Current behavior is:

- if a task key exists, use `<normalized-task-key>_<first-5-id-chars>`
- if no task key exists, fall back to the full task id string

This is current implementation truth, not the final redesign contract.

## Current materialized roots

Current code materializes these task roots:

- `workspace/`
- `context/`
- `manifests/`

These are created by `ensure_task_dirs(...)`.

Current code does not yet materialize the redesign's fuller root set such as:

- `artifacts/`
- `handoffs/`
- `review/`
- `logs/`
- `tmp/`
- `checklists/`

as canonical task roots.

## Current upload targets

Current upload target aliases in `task_service.py` include:

- `workspace_docs`
- `primary_workspace`
- `context_docs`
- `primary_context`
- `manifest_bundle`
- `manifest_root`

These map onto the current task-owned materialized directories.

## Current bootstrap behavior

Current task bootstrap and file upload logic does three important things:

- creates task-owned materialized directories
- ensures task resource bindings for workspace, context, and manifests
- keeps uploads inside the allowed task-owned root

Current code uses task-owned storage URIs such as:

- `task://{task_id}/workspace`
- `task://{task_id}/context`
- `task://{task_id}/manifests`

## Current dependency model

Current hard dependency authoring is still weak.

Current downstream dependency usually flows through:

- `ContextItem` publication
- green checkpoint summary publication
- `publish_context_item`
- manifest projection
- worker bundle visibility

Current authored workflow YAML does not yet define the redesign's strong typed named output slots and typed inputs contract.

## Minimal example

```text
<platform data dir>/tasks/<current-task-slug>/
  workspace/
  context/
  manifests/
```

## Expanded example

```text
task bootstrap
  -> ensure_task_dirs(...)
  -> materialize workspace/context/manifests
  -> ensure task resource bindings
  -> later file uploads target workspace_docs, context_docs, or manifest_bundle

dependency flow today
  -> publish ContextItem or checkpoint summary
  -> project visible slice into later manifest
  -> expose it through worker bundle and runtime read models
```

## Evidence

- inspected code in `autoclaw-main/apps/api/app/paths.py`
- inspected code in `autoclaw-main/apps/api/app/services/task_service.py`
- inspected code in `autoclaw-main/apps/api/app/runtime/resources.py`
- inspected code in `autoclaw-main/apps/api/app/runtime/checkpoints.py`

## Redesign pointer

For the target host layout and generated-file contract, see `../../redesign/architecture/task-root-layout-and-generated-files.md`, `../../redesign/workflows/typed-dependency-selectors-and-produce-slots.md`, and `../../redesign/workflows/criteria-and-parent-verification.md`.
