# Definition authoring API and draft-set contract

Status: Target

This page defines the V2 backend and state contract for definition authoring.

## Core rule

Current registry revisions remain controller-owned reusable truth.

Draft sets are backend-owned local pending authoring state over that truth. They are not a second registry, a live-linked projection, or a hidden runtime lane.

Materialization captures the current stored revision as a point-in-time draft baseline. That captured baseline is the revision the draft is based on, even if the registry current pointer advances later.

Apply or import is the only path that changes current reusable definition truth.

For the first V2 authoring lane, draft persistence lives in a dedicated host-side drafts area under AutoClaw's configured data dir rather than in registry tables or browser-owned state.

## Draft-set model

The authoring API operates on one draft-set directory at a time.

Canonical draft-set directory shape:

```text
<data_dir>/drafts/definitions/<draft_set_id>/
  draft-set.json
  roles/
    <key>.yaml
  policies/
    <key>.yaml
  workflows/
    <key>.yaml
  _normalized/
    roles/
      <key>.json
    policies/
      <key>.json
    workflows/
      <key>.json
  task-compose.preview.yaml
```

Rules:

- one draft set represents one coherent authored change set
- related role, policy, and workflow edits that must validate together belong in the same draft set
- unrelated changes should use a different draft set
- the root drafts area follows AutoClaw's configured data dir rather than a hardcoded home-directory path
- the backend owns the draft-set directory and manifest file
- the browser is a client of that backend-owned draft state, not the draft-state authority
- materialized draft files are editable local copies of stored revisions, not live-linked projections
- each materialized file records a captured baseline: the stored revision number, content hash, optional source path, and enough baseline body or normalized data to support compare, reset, and stale checks
- the captured baseline is not refreshed by opening, saving, validating, previewing, or resetting a draft file
- `draft-set.json` is the authoritative saved draft-set manifest and baseline ledger for the local draft set
- the authored definition bodies stay as real YAML files rather than being embedded only inside the manifest
- per-definition normalized JSON files under `_normalized/` are backend-owned machine read models over the current draft body plus captured stored baseline; they are not a second editable truth surface

Canonical `draft-set.json` fields should include:

- `draft_set_id`
- `created_at`
- `updated_at`
- `files[]`
- `based_on.definitions[]`
- `preview_task_compose_path | null`
- optional local status metadata such as `saved`, `applied`, or `stale`

Minimum `files[]` entry fields should include:

- `kind`
- `key`
- `draft_path`
- `normalized_path`
- `based_on.revision_no`
- `based_on.content_hash`
- optional `based_on.source_path | null`

For files added locally instead of materialized from stored truth, `based_on.*` values are null and the draft set owns a local starter baseline for reset only.

## Required authoring operations

The authoring API must own these operations:

- create, open, list, and delete draft sets
- materialize current stored revision(s) into draft files plus normalized JSON shadows inside the draft-set directory
- save draft body edits without publishing them
- reset a draft file to its captured stored baseline or local starter baseline without consulting current registry truth
- explicitly re-materialize a draft file from the current stored revision when the operator chooses to discard local edits and update the baseline
- validate a full draft set
- apply or import the draft set into current registry truth
- optionally validate preview task-compose input against the same draft set

The workbench may rename these actions for UX, but it must keep the lifecycle split between local draft save and published truth apply.

## Canonical API families

V2 authoring uses an explicit authoring lane rather than overloading the current `/definitions` registry routes.

Canonical route families are:

- `GET /authoring/definition-draft-sets`
- `POST /authoring/definition-draft-sets`
- `GET /authoring/definition-draft-sets/{draft_set_id}`
- `DELETE /authoring/definition-draft-sets/{draft_set_id}`
- `POST /authoring/definition-draft-sets/{draft_set_id}/materialize`
- `PUT /authoring/definition-draft-sets/{draft_set_id}/files/{kind}/{key}`
- `POST /authoring/definition-draft-sets/{draft_set_id}/files/{kind}/{key}/reset`
- `POST /authoring/definition-draft-sets/{draft_set_id}/files/{kind}/{key}/rematerialize-current`
- `POST /authoring/definition-draft-sets/{draft_set_id}/validate`
- `POST /authoring/definition-draft-sets/{draft_set_id}/apply`
- `POST /authoring/definition-draft-sets/{draft_set_id}/preview-task-compose`

Rules:

- `/authoring` names local pending authoring state, not runtime control truth
- current registry reads and uploads may remain under `/definitions`, but draft-set writes do not mutate registry truth
- `kind` accepts only `role`, `policy`, or `workflow`
- `DELETE /authoring/definition-draft-sets/{draft_set_id}` may return `204 No Content`; the other draft-set write routes return the updated draft-set read model or a validation/apply result derived from it
- stale apply errors use the same controller stale or illegal-state family as other guarded writes

## Canonical API envelopes

The list/read split is explicit because the Definition Editor needs full saved draft bodies, normalized shadows, and saved preview-task-compose state, while the draft-set list only needs compact summaries.

Shared summary and detail shapes are:

```yaml
definition_draft_file_summary:
  kind: role | policy | workflow
  key: string
  draft_path: string
  normalized_path: string
  body_format: yaml
  content_hash: string
  based_on:
    revision_no: integer | null
    content_hash: string | null
    source_path: string | null
  status: clean | modified | added | stale | invalid

definition_draft_file_detail:
  kind: role | policy | workflow
  key: string
  draft_path: string
  normalized_path: string
  body_format: yaml
  content_hash: string
  based_on:
    revision_no: integer | null
    content_hash: string | null
    source_path: string | null
  status: clean | modified | added | stale | invalid
  body: string
  normalized_content: object | null
  baseline_body: string | null
  baseline_normalized_content: object | null

definition_draft_set_summary:
  draft_set_id: string
  title: string | null
  created_at: timestamp
  updated_at: timestamp
  state: open | applied | stale
  files:
    - definition_draft_file_summary
  preview_task_compose_path: string | null

definition_draft_set_detail:
  draft_set_id: string
  title: string | null
  created_at: timestamp
  updated_at: timestamp
  state: open | applied | stale
  files:
    - definition_draft_file_detail
  preview_task_compose_path: string | null
  preview_task_compose_body: string | null
```

List and create routes use:

```yaml
definition_draft_set_list_query:
  cursor: string | null
  limit: integer

definition_draft_set_list_response:
  items:
    - definition_draft_set_summary
  next_cursor: string | null

definition_draft_set_create_request:
  title: string | null
  materialize:
    - kind: role | policy | workflow
      key: string
  preview_task_compose: string | null

definition_draft_set_create_response:
  draft_set: definition_draft_set_detail
```

Materialize, file-save, reset, and re-materialize routes use:

```yaml
definition_draft_materialize_request:
  definitions:
    - kind: role | policy | workflow
      key: string

definition_draft_file_write_request:
  body: string
  body_format: yaml

definition_draft_file_reset_request:
  discard_local_changes: true

definition_draft_file_rematerialize_current_request:
  discard_local_changes: true

definition_draft_set_response:
  draft_set: definition_draft_set_detail
```

Validation, apply, and task-compose preview use:

```yaml
definition_draft_validation_response:
  draft_set_id: string
  status: valid | invalid | stale
  errors:
    - code: string
      message: string
      path: string | null
      kind: schema | cross_reference | stale | preview
  warnings:
    - code: string
      message: string
      path: string | null

definition_draft_apply_request:
  should_start_task_after_apply: boolean

definition_draft_task_start_failure:
  code: invalid_request_shape
    | illegal_caller
    | illegal_target_relation
    | illegal_state
    | stale_dispatch
    | stale_flow_revision
    | stale_assignment
    | stale_checkpoint
    | missing_resource
    | missing_required_publication
    | conflicting_continuation
    | cursor_reset_required
    | boundary_precondition_failed
    | capability_rejected
    | removed_surface
    | budget_exhausted
    | internal_error
  summary: string
  is_retryable: boolean
  suggested_next_step: string | null

definition_draft_apply_response:
  draft_set_id: string
  status: applied | stale | invalid
  published_revisions:
    - kind: role | policy | workflow
      key: string
      revision_no: integer
      content_hash: string
  started_task_id: string | null
  task_start_status: not_requested | started | failed
  task_start_failure: definition_draft_task_start_failure | null
  validation: definition_draft_validation_response

definition_draft_task_compose_preview_request:
  body: string
  body_format: yaml

definition_draft_task_compose_preview_response:
  status: valid | invalid
  validation: definition_draft_validation_response
```

Rules:

- `body` is YAML text for the canonical editable authored body
- `GET /authoring/definition-draft-sets/{draft_set_id}` is the canonical Definition Editor bootstrap read; it must return saved draft YAML bodies, saved normalized JSON shadows, saved baseline bodies, and saved preview-task-compose state
- normalized JSON shadows are produced by the backend and exposed through `normalized_path` plus `normalized_content`, not edited through the write envelope
- `materialize` may be empty only when creating a new draft set for new authored definitions
- `PUT /authoring/definition-draft-sets/{draft_set_id}/files/{kind}/{key}` may create a new local draft file only when current registry truth does not already own that key; otherwise the operator must materialize or re-materialize current first so stale checks stay meaningful
- apply reads stale baselines from `draft-set.json`; clients do not supply registry revision claims in the body
- `should_start_task_after_apply` starts a task only from newly current registry truth after successful apply
- apply remains successful once registry truth published; a later task-start failure returns `task_start_status=failed` plus `task_start_failure` detail rather than surfacing a false apply failure
- saved preview task-compose issues are non-blocking validation warnings unless `should_start_task_after_apply` is true for the current apply request
- `started_task_id` is set only when `task_start_status=started`
- reset and re-materialize requests are destructive local draft writes and require explicit discard intent rather than silently accepting accidental client actions
- preview-task-compose writes persist the supplied YAML body into the draft-set folder before validation so the authoring UI can reopen the same saved preview state later

## Reset and re-materialize rule

Reset is a local draft operation.

For a materialized file, reset replaces the current draft body and normalized shadow with the captured baseline recorded when the file was materialized. For a locally added file, reset restores the draft-set's local starter baseline.

Rules:

- reset does not read the registry current pointer
- reset does not update `based_on`
- reset does not publish or mutate registry truth
- if current stored truth moved after materialization, reset still restores the captured baseline rather than the newer stored revision

Re-materialize current is a separate explicit operation.

It reads the current stored registry revision for that definition, replaces the local draft body and normalized shadow, and updates `based_on.revision_no`, `based_on.content_hash`, and `based_on.source_path` to the newly captured baseline.

Rules:

- re-materialize current is valid only when stored registry truth exists for that definition
- re-materialize current must discard local edits only after explicit discard intent
- re-materialize current is not automatic on open, save, validate, preview, reset, or apply
- accepting a newer stored revision after a stale failure must happen through explicit re-materialize, rebase, or manual merge semantics rather than a silent overwrite

## Save versus publish rule

Save persists pending authoring state only.

Apply or import publishes reusable truth only after validation and stale checks pass.

Rules:

- saving a draft set must not mutate current registry truth
- applying a draft set must create new current registry revisions for the changed definitions
- the workbench should present saved draft state separately from current stored truth
- an applied draft set may remain inspectable as local history, but it does not become the source of truth
- once an applied draft set receives a later local draft mutation such as file save, preview-task-compose write, reset, materialize, or re-materialize-current, the draft-set state reopens to `open`
- save writes update the draft-set directory, `draft-set.json`, and any normalized JSON shadow files; they do not publish anything by themselves
- the minimum save contract does not invent a new registry-truth compare token or parallel publish lane
- multi-tab or multi-operator save-conflict handling may exist later as a local draft UX improvement, but it is outside the minimum reusable-truth contract

## Validation rule

Validation must reuse the same canonical legality rules that guard stored upload, task-start inputs, and authoring-side task-compose input checks.

Validation output must distinguish:

- schema errors
- authored cross-reference legality errors
- preview-only warnings
- stale-baseline failures

Rules:

- validation over a multi-definition draft set must evaluate the authored bundle as one change set
- if a draft set edits roles or policies together with workflows that reference them, workflow validation must read the draft-set versions rather than only the current stored registry versions
- normalized JSON shadows may help validation, compare, and stale-check paths consume the exact current draft structure without reparsing controller-owned DB rows directly
- arbitrary per-file validation against only current stored truth is not sufficient for bundle authoring

## Apply and import rule

Apply must preserve controller-owned registry semantics.

Rules:

- the controller decides the resulting current revisions
- apply must either commit the bundle atomically or preserve equivalent authored semantics through validated safe ordering
- when roles or policies and workflows change together, the system must validate the bundle first and then apply in a safe order that does not break referenced workflow legality
- a naive arbitrary file-order upload is not a legal apply contract
- publish truth still follows the ordinary controller-owned definition-registry revision model rather than a second draft-owned truth state machine

## Staleness rule

Each materialized baseline entry captures the stored revision id and content hash the draft started from.

Apply must fail stale when current stored truth changed after that baseline was captured.

Rules:

- stale failure is explicit and non-destructive
- the normalized JSON shadow for one materialized definition may mirror exact stored `content_json`, but draft truth still follows the current YAML body plus `draft-set.json` manifest rather than editing DB rows in place
- the system must not silently overwrite newer stored truth with an older draft-set basis
- rebase, re-materialize, or manual merge may exist as follow-up flows, but they are outside the minimum apply contract

## Task-compose preview and task-start rule

The authoring lane may validate preview task-compose input against a draft set before publish.

Task start still runs from current controller truth after apply.

Rules:

- unsaved drafts are not a launch surface
- preview task-compose input is optional authoring context, not reusable definition truth
- post-apply task start reads the newly current stored definitions through the ordinary controller start path

## Non-goals

This contract does not define:

- DB-backed draft persistence
- JSON-only definition authoring bodies in the minimum lane
- a runtime path that executes directly from unsaved drafts
- editing current registry truth in place through live projections
- collaborative save-conflict UX beyond basic backend-owned local draft persistence

## Related contracts

- [Definition authoring workbench](definition-authoring-workbench.md)
- [Control UI runtime and authoring surfaces](control-ui-runtime-and-authoring-surfaces.md)
- [Role and policy definition schema](role-and-policy-definition-schema.md)
- [V1 definition registry and upload contract](../../v1/interfaces/definition-registry-and-upload-contract.md)
