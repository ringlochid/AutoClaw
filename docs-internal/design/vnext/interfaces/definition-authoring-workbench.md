# Definition authoring workbench

Status: Target

This page defines the Vnext definition-authoring workbench contract.

## Core rule

The authoring workbench is a front door over existing controller-owned definition and task-start truth.

It must not become:

- a second definition truth owner
- a hidden runtime-dispatch surface
- a draft-only execution lane that bypasses guarded upload and task start

The workbench may share shell chrome with runtime control surfaces, but it remains a separate major surface from live task execution.

## Canonical workbench capabilities

The workbench may provide:

- registry inspection of current roles, policies, and workflows
- local draft editing of one or more definition files
- schema and legality validation
- prompt preview over draft content
- diff against current stored revisions
- guarded upload or import
- task-compose validation and task start

## Draft-set model

The workbench operates on a local draft set.

Canonical draft-set members are:

- one or more draft definition bodies
- optional task-compose preview input
- optional selected current registry revisions used as comparison baselines

Rules:

- draft-set contents are not controller truth
- draft-set contents may be saved locally or in browser/session state, but they must not be treated as active runtime truth
- prompt preview over drafts is preview-only and must say so explicitly

## Validation contract

Workbench validation must reuse the same canonical validators that back:

- guarded definition upload
- task start
- prompt rendering inputs where preview is requested

Validation output must distinguish:

- schema errors
- role/policy/workflow legality errors
- task-compose validation errors
- preview-only warnings that do not block guarded upload

## Upload and import rule

The workbench may batch user actions, but it must preserve controller-owned upload semantics.

Rules:

- successful upload changes stored registry truth, not the draft set itself
- guarded upload remains the only path that makes reusable definition truth current
- task start still runs from current controller truth, not from unsaved drafts

## Prompt preview rule

Prompt preview is a read surface over:

- draft definitions when present
- current controller truth when previewing stored revisions
- optional preview task-compose input

Rules:

- preview output is not controller truth
- preview output must name whether it came from stored truth, draft content, or a mixed draft-plus-current comparison
- preview should surface rendered prompt diff when comparing current stored truth to a draft set

## Non-goals

This contract does not define:

- final visual layout of the workbench
- browser-only local storage details
- a draft execution path that bypasses upload and task start

## Related contracts

- [Role and policy definition schema](role-and-policy-definition-schema.md)
- [Deployment binding and runtime profile map](deployment-binding-and-runtime-profile-map.md)
- [Prompt system vnext](../prompt-layer/prompt-system-vnext.md)
- [Control UI runtime and authoring surfaces](control-ui-runtime-and-authoring-surfaces.md)
- [V1 definition registry and upload contract](../../v1/interfaces/definition-registry-and-upload-contract.md)
- [V1 definition ingest and upload contract](../../v1/interfaces/definition-ingest-and-upload-contract.md)
