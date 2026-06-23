# Prompt system vnext

Status: Target

This page defines the Vnext prompt-system direction.

## Core rule

Vnext keeps the current asset-backed prompt system and its render-and-persist model.

It does not replace that model with UI-owned preview text, adapter-owned wrapper text, support-file-derived summaries, or a separate prompt preview/diff/regression lane.

## Base prompt families

Unless a later owner page freezes additional families, Vnext keeps the same base prompt-family model as V1:

- worker dispatch prompt
- parent/root dispatch prompt

Vnext keeps prompt generation as one controller-derived render path that writes canonical dispatch artifacts for each dispatch or redispatch.

## Current-model preservation

Rules:

- prompt generation stays asset-backed and controller-truth-derived
- render still produces `instructions_text`, `input_text`, `full_markdown`, and `content_hash`
- dispatch-local prompt artifacts remain the canonical persisted prompt read surface
- prompt text must not fork into UI-owned shadow variants
- exact current render/persist paths remain defined by the V1 current prompt-layer contract until implementation deliberately changes them

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

## Provider independence rule

Prompt text is provider-independent.

Rules:

- the same stored role, policy, and workflow truth must render the same prompt content regardless of `openclaw`, `codex`, or `claude`
- requested or resolved provider is runtime provenance, not prompt content
- prompt text must not contain provider selection, default-provider resolution, or fallback explanation
- if control surfaces want to show provider provenance beside a task or prompt artifact, that provenance must stay outside the prompt text itself

## Capability overlay rule

Prompt text must surface whether the current node may:

- request human direction
- request human approval
- request human input
- request human review
- start a long-running command run

These capability overlays are derived from effective controller capabilities, not from raw UI toggles or adapter permissions.

## Truth boundary

Vnext prompt artifacts must not treat these as ordinary prompt truth:

- support-state files
- raw provider or adapter event streams
- machine-local provider-config file contents
- generic operator notes that were not normalized into controller truth
- provider choice, default-provider config, or fallback provenance

## Related contracts

- [Role and policy definition schema](../interfaces/role-and-policy-definition-schema.md)
- [Provider preference and runtime config](../interfaces/provider-selection-and-runtime-config.md)
- [Human request and approval contract](../interfaces/human-request-and-approval-contract.md)
- [Command run and long-running boundary](../architecture/command-run-and-long-running-boundary.md)
- [Capability, security, and audit](../interfaces/capability-security-and-audit.md)
- [Control UI runtime and authoring surfaces](../interfaces/control-ui-runtime-and-authoring-surfaces.md)
- [Controller contract and resumable execution](../architecture/controller-contract-and-resumable-execution.md)
- [V1 prompt-layer front door](../../v1/prompt-layer/README.md)
