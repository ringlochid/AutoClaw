# Prompt legality and coverage

Status: Reference

This page is a secondary coverage summary for the live v1 prompt model.

If this page drifts from the owner docs in this folder, the owner docs win.

## Canonical prompt families

The live prompt layer freezes exactly two base prompt families:

- `worker_dispatch_prompt`
- `parent_root_dispatch_prompt`

Provider, adapter, or watchdog-specific variants are wrappers or generated examples over these two families, not separate canonical families.

## Canonical send modes

- `full_prompt`
- `same_session_continue`

Rules:

- `full_prompt` is required for first dispatch and retry
- `same_session_continue` is a transport-only optimization inside the same attempt
- same-session continuation must not change prompt truth, only inline transport shape

## Coverage rule

Prompt coverage is complete in v1 when:

- every current dispatchable node turn maps to one of the two base prompt families
- the generated inventory and rendered examples follow the canonical section order
- prompts teach only the live boundary model:
  - ingress: `dispatch`
  - egress: `yield | green | retry | blocked`
- prompts use path-only surfaced refs
- prompts render `instruction`, not `instruction_text`
- prompts never teach flow/scope manifest split, packet families, or gate-era callback legality as live contract

## Family expectations

### `worker_dispatch_prompt`

Must support:

- current assignment execution
- durable publication
- optional task-memory search
- terminal closure by `green | retry | blocked`

### `parent_root_dispatch_prompt`

Must support:

- explicit parent/root tool use
- structural edit orientation
- surfaced child evidence review
- non-terminal closure through `yield`
- terminal closure through `green | blocked` when the parent/root node itself is closing its own current assignment

## Generated-artifact rule

`prompt-catalog.yaml`, [generated/inventory.md](generated/inventory.md), and [generated/rendered-examples.md](generated/rendered-examples.md) are generated or secondary artifacts and must match the live owner docs.

If they drift, the owner docs win and the generated artifacts are stale.

In particular:

- worker prompts must surface `latest_checkpoint_context` when retry or other prior checkpoint evidence is part of the current execution
- parent/root prompts must surface `latest_checkpoint_context` and `consumed_durable_refs` when the current decision depends on surfaced child or prior-attempt evidence
- `same_session_continue` may omit only static sections; every non-static section remains in scope in the example set

## Exact Validation And Reject Routes

Use these pages when the question is "what exact reject or legality message does the runtime emit after a prompt-driven action?"

- [prompt-pack/validation-and-reject-blocks.md](prompt-pack/validation-and-reject-blocks.md) for exact prompt-layer reject wording and worked examples
- [../architecture/runtime-boundary-and-controller-loop-contract.md](../architecture/runtime-boundary-and-controller-loop-contract.md) for exact `dispatch`, `yield`, `green`, `retry`, `blocked`, and `boundary_precondition_failed` meaning
- [../interfaces/api-surface-and-trust-lane-map.md](../interfaces/api-surface-and-trust-lane-map.md) for exact route/lane legality of checkpoint, boundary, and tool calls
- [../interfaces/api-schema-appendix.md](../interfaces/api-schema-appendix.md) for exact error payload carriers such as `code`, `field_path`, and `suggested_next_step`

Use this page when the question is "does the prompt family and example set cover the live model completely?"

## Exact Prompt Example Routes

Use these pages when the question is "show me the whole prompt exactly as a reader would see it":

- [generated/rendered-examples.md](generated/rendered-examples.md) for exact worker, parent/root, and `same_session_continue` examples
- [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md) for exact shared top-level blocks
- [prompt-pack/runtime-rule-blocks.md](prompt-pack/runtime-rule-blocks.md) for exact legality and support blocks

## Historical search terms

Do not treat any of these as the live v1 prompt-coverage model:

- `parent_gate_resume`
- `worker_retry` as a separate prompt family
- dispatch-family packs
- state/boundary overlay families as first-class prompt authorities
