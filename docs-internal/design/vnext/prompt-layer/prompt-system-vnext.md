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

## Dispatch capability overlay

When the controller opens a dispatch, the prompt must surface the effective capability set for that execution as controller-derived truth.

The instructions layer must teach:

- the controller-owned effective capability set for this dispatch is authoritative
- `human_request` and `command_run` are controller capabilities, not generic adapter approval prompts
- adapter, local-tool, or UI restrictions may narrow the effective set further, but they must not silently widen it

The rendered prompt must expose a compact `Capabilities Now` block that includes:

- `human_request.direction`
- `human_request.approval`
- `human_request.input`
- `human_request.review`
- `command_run`
- a stable deny explanation string when a capability is denied or narrowed
- the next legal action when one exists

Rules:

- omitted or denied capabilities render explicitly as `deny`; they do not disappear silently from the prompt
- `Allowed Actions Now` remains the bounded next-step lane; `Capabilities Now` explains capability authority and restrictions rather than replacing that action section
- controller may materialize dispatch-local capability readbacks such as `_runtime/dispatch/<dispatch_id>/capabilities.json` or `_runtime/dispatch/<dispatch_id>/capabilities.md`, but those files are read-only projections over the same controller-owned effective capability snapshot
- prompt text must not ask the node to infer capability from tool absence, adapter wording, or missing UI controls

## Human request redispatch prompt

When a human request reaches a terminal resolution and the controller continues the same task lineage, the redispatch must use a full regenerated canonical prompt package.

The prompt must include the normalized human-request context as controller-derived truth:

- original request title, summary, kind, and requester node
- request items, each item prompt, each item's options and recommended option
- item-scoped selected option or freeform answer when provided
- item-scoped extra notes and validated response payload when provided
- timeout/default behavior when the request timed out
- evidence refs
- current assignment, latest checkpoint context, effective capability set, and allowed actions now

Rules:

- provider chat continuation may be reused as transport continuity, but the prompt must not depend on provider memory to recover human-request truth
- timeout redispatch uses the same prompt path as answered redispatch, with `resolution_kind: timed_out` and the request's timeout/default behavior included
- raw logs, support files, or provider histories stay out of the ordinary prompt unless represented as deliberate refs or compact summaries
- full canonical prompt here means the full semantic prompt package for the dispatch, not raw dumping every artifact or log

## Command-run terminal redispatch prompt

When a command run reaches a terminal state and the controller continues the same task lineage, the redispatch must also use a full regenerated canonical prompt package.

The prompt must include the normalized command-run context as controller-derived truth:

- original command and description
- run id
- terminal state
- workdir when present
- created, started, and ended timestamps
- timeout when declared
- latest bounded progress/update summary when persisted
- normalized terminal summary
- exit code or signal when present
- log ref when surfaced
- current assignment, latest checkpoint context, effective capability set, and allowed actions now

Rules:

- the prompt must tell the next dispatch what command ran and why it existed, not only how it ended
- command-like jobs such as `pytest` must carry exit status in normalized controller fields rather than forcing the model to inspect raw logs
- raw logs stay out of ordinary prompt truth by default
- the prompt may include a deliberate `log_ref` when the controller intentionally surfaces it
- redispatch correctness depends on normalized controller truth plus surfaced refs, not provider-native history or runner-local state

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
- start a long-running command run

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
- [Control UI runtime and authoring surfaces](../interfaces/control-ui-runtime-and-authoring-surfaces.md)
- [Controller contract and resumable execution](../architecture/controller-contract-and-resumable-execution.md)
- [V1 prompt-layer front door](../../v1/prompt-layer/README.md)
