# Definition authoring API and draft-set contract

Status: Target

This page defines the Vnext backend and state contract for definition authoring.

## Core rule

Current registry revisions remain controller-owned reusable truth.

Draft sets are backend-owned local pending authoring state over that truth. They are not a second registry, a live-linked projection, or a hidden runtime lane.

Apply or import is the only path that changes current reusable definition truth.

For the first Vnext authoring lane, draft persistence lives in a dedicated host-side drafts area under AutoClaw's configured data dir rather than in registry tables or browser-owned state.

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

## Required authoring operations

The authoring API must own these operations:

- create, open, list, and delete draft sets
- materialize current stored revision(s) into draft files plus normalized JSON shadows inside the draft-set directory
- save draft body edits without publishing them
- validate a full draft set
- apply or import the draft set into current registry truth
- optionally validate preview task-compose input against the same draft set

The workbench may rename these actions for UX, but it must keep the lifecycle split between local draft save and published truth apply.

## Save versus publish rule

Save persists pending authoring state only.

Apply or import publishes reusable truth only after validation and stale checks pass.

Rules:

- saving a draft set must not mutate current registry truth
- applying a draft set must create new current registry revisions for the changed definitions
- the workbench should present saved draft state separately from current stored truth
- an applied draft set may remain inspectable as local history, but it does not become the source of truth
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

- final HTTP route names or exact transport encoding
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
