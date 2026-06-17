# Prompt system vnext

Status: Target

This page defines the Vnext prompt-system direction.

## Core rule

Vnext extends the current asset-backed prompt system. It does not replace it with UI-owned preview text, adapter-owned wrapper text, or support-file-derived summaries.

## Base prompt families

Unless a later owner page freezes additional families, Vnext keeps the same base prompt-family model as V1:

- worker dispatch prompt
- parent/root dispatch prompt

Vnext adds capability-aware overlays and preview surfaces around those base families instead of replacing them with a new unrelated prompt taxonomy.

## New first-class surfaces

Vnext adds these prompt-system surfaces:

- rendered preview for current stored truth
- rendered preview for draft definitions plus preview task-compose input
- prompt diff between stored truth and draft preview
- role and policy preview showing how resolved metadata contributes to prompt assembly
- regression fixtures that lock expected prompt shape across capability and role/policy changes

## Human request redispatch prompt

When a human request reaches a terminal resolution and the controller reopens the same task lineage, the redispatch must use a full regenerated canonical prompt package.

The prompt must include the normalized human-request context as controller-derived truth:

- original request title, summary, kind, requester node, and risk level
- options and recommended option
- selected option or freeform answer when provided
- extra notes and validated response payload when provided
- timeout/default behavior when the request timed out
- evidence refs
- current assignment, latest checkpoint context, and allowed actions now

Rules:

- provider chat continuation may be reused as transport continuity, but the prompt must not depend on provider memory to recover human-request truth
- timeout redispatch uses the same prompt path as answered redispatch, with `resolution_kind: timed_out` and the request's timeout/default behavior included
- raw logs, support files, or provider histories stay out of the ordinary prompt unless represented as deliberate refs or compact summaries
- full canonical prompt here means the full semantic prompt package for the dispatch, not raw dumping every artifact or log

## Preview provenance rule

Every preview must name its source basis explicitly:

- `stored_truth`
- `draft_truth`
- `mixed_compare`

Rules:

- stored-truth preview reads current controller truth only
- draft preview may combine draft definitions with preview task-compose input
- mixed compare is preview-only and must not be confused with launchable runtime truth

## Capability overlay rule

Prompt preview must surface whether the current node may:

- request human direction
- request human approval
- request human input
- request human review
- start an async job

These capability overlays are derived from effective controller capabilities, not from raw UI toggles or adapter permissions.

## Diff rule

Prompt diff is a first-class Vnext read surface.

Rules:

- diff compares rendered prompt output, not only raw definition YAML
- diff must preserve preview provenance so readers know whether they are comparing stored truth or draft content
- diff must not hide changes in resolved role, policy, or capability wording

## Truth boundary

Vnext prompt previews and diffs must not treat these as ordinary prompt truth:

- support-state files
- raw provider or adapter event streams
- machine-local deployment-binding file contents
- generic operator notes that were not normalized into controller truth

## Related contracts

- [Prompt regression suite](prompt-regression-suite.md)
- [Role and policy definition schema](../interfaces/role-and-policy-definition-schema.md)
- [Definition authoring workbench](../interfaces/definition-authoring-workbench.md)
- [Controller contract and resumable execution](../architecture/controller-contract-and-resumable-execution.md)
- [V1 prompt-layer front door](../../v1/prompt-layer/README.md)
