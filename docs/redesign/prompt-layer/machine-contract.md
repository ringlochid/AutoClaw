# Prompt Machine Contract

Status: Target

This page defines the simplified machine-readable prompt contract for the frozen v1 prompt layer.

## Owner Docs And Machine Artifacts

Canonical owner docs:

- `contract.md`
- `source-and-sections.md`
- `machine-contract.md`
- `prompt-pack/runtime-rule-blocks.md`

Secondary machine artifacts:

- `prompt-catalog.yaml`
- `generated/rendered-examples.md`
- `apps/api/app/runtime/prompt/assets/catalog.json`

If any generated or catalog artifact still teaches flow/scope manifests, callback legality, final durable ref metadata inside semantic assignment handoff, or checkpoint `control_effects`, it is stale and must not overrule the canonical owner docs.

## Top-Level Catalog Shape

The catalog must expose:

- `version`
- `owner_docs`
- `section_order`
- `static_sections`
- `send_modes`
- `prompt_families`
- `exact_blocks`
- `generated_artifacts`
- `generated_examples`
- `validation_references`
- `rules`
- `validator_checks`

Rules:

- `version` is fixed to `1`
- `section_order` is exactly the canonical section order from [contract.md](contract.md)
- `static_sections` is exactly:
  - `operating_model`
  - `task_identity`
  - `node_purpose`
- `send_modes` is exactly:
  - `full_prompt`
  - `same_session_continue`
- `prompt_families` freezes exactly two canonical dispatch prompt families
- `exact_blocks` registers reusable exact wording blocks, not extra prompt families
- shipped exact block bytes come from `apps/api/app/runtime/prompt/assets/**`, while the prompt-pack docs mirror those bytes for human review
- each `exact_blocks` entry must declare whether it is a live `live_instruction_block` consumed by runtime instruction assembly or a `reference_only` exact block

## Prompt Family Registry

The live v1 family registry contains exactly:

- `worker_dispatch_prompt`
- `parent_root_dispatch_prompt`

All adapter/provider variants are wrappers or generated examples over these two families, not separate canonical prompt families.

## Semantic Assignment And Checkpoint Rules

Machine artifacts must keep these splits explicit:

- `current_assignment` is the runtime-projected assignment surface derived from child-definition durable contract plus parent semantic staging handoff surface
- `current_assignment.summary` plus optional `instruction` are handoff prose
- `current_assignment.criteria` and `current_assignment.consumes` are reduced durable claims only
- `current_assignment.produces` are `assignment_produce_requirement` values, not published refs
- `consumed_durable_refs` carries the exact current durable refs the runtime resolved for this turn
- `latest_checkpoint_context` mirrors durable handoff written through `record_checkpoint`
- `latest_checkpoint_context` must not teach or surface `control_effects`

## Exact Block Registry

The catalog must register these exact reusable prompt blocks:

- `autoclaw_system_block_v1`
- `autoclaw_provider_continuity_block_v1`
- `autoclaw_parent_worker_split_v1`
- `autoclaw_same_session_continue_wrapper_v1`
- `runtime_legality_block_worker_v1`
- `runtime_legality_block_parent_v1`
- `runtime_boundary_rule_block_v1`
- `retry_handover_rule_v1`
- `runtime_read_order_rule_v1`
- `current_task_state_frame_v1`
- `artifact_render_rule_v1`
- `task_memory_rule_v1`
- `monitoring_not_task_truth_v1`
- `same_session_continue_rule_v1`
- `worker_runtime_opening_example_v1`
- `parent_root_runtime_opening_example_v1`

## Generated Artifact Registry

The catalog should register these secondary prompt-layer artifacts:

- `generated/rendered-examples.md`

## Generated Example Registry

The generated example registry should currently identify:

- `parent_root_dispatch_prompt_full_prompt`
- `worker_dispatch_prompt_full_prompt`
- `worker_dispatch_prompt_same_session_continue`
- `parent_root_dispatch_prompt_same_session_continue`
- `worker_dispatch_prompt_blocked_ending_sketch`

## Prompt Family Coverage

### `worker_dispatch_prompt`

Required sections:

- `operating_model`
- `task_identity`
- `node_purpose`
- `current_dispatch`
- `workflow_manifest`
- `current_assignment`
- `consumed_durable_refs`
- `allowed_actions_now`
- `publication_rule`

Conditionally required sections:

- `latest_checkpoint_context` when a prior relevant checkpoint is part of the current execution or retry handover
- `transient_refs` when explicit transient carryover is surfaced
- `task_memory` when task-memory hints are surfaced

### `parent_root_dispatch_prompt`

Required sections:

- `operating_model`
- `task_identity`
- `node_purpose`
- `current_dispatch`
- `workflow_manifest`
- `current_assignment`
- `allowed_actions_now`
- `publication_rule`

Conditionally required sections:

- `latest_checkpoint_context` when the current decision depends on surfaced checkpoint evidence
- `consumed_durable_refs` when surfaced durable evidence is part of the current decision
- `transient_refs` when explicit transient carryover is surfaced
- `task_memory` when task-memory hints are surfaced

## Validator Rules

Catalog, renderer, and generated examples must agree on:

- prompt family ids
- section order
- static sections
- send modes
- semantic `current_assignment`
- runtime-resolved `consumed_durable_refs`
- `record_checkpoint` durable handoff semantics
- `produces` as requirements
- no checkpoint `control_effects`
- `yield` after exactly one staged child assignment only

Machine validation should reject live catalog/examples that:

- render exact durable `path` or `version` metadata inside `current_assignment.criteria` or `current_assignment.consumes`
- render published artifact refs inside `current_assignment.produces`
- omit `consumed_durable_refs` from worker prompts
- register parent/root terminal closure modes outside `yield | green | blocked`
- omit any non-static section from a `same_session_continue` example
- teach `yield` after `release_green` or root `release_blocked`
- teach `release_blocked` or terminal `blocked` as a non-root parent path
- surface checkpoint `control_effects`
- route live prompt-layer owner or generated surfaces to legacy source packs instead of current owner docs
- register a third canonical dispatch prompt family

Concrete validator failures:

```text
Reject:
- a worker example that omits `consumed_durable_refs`
- a current-assignment render that includes `path` for `findings_report`
- a current-assignment render that turns `patch` into a published artifact path
- a parent/root catalog family that still includes `retry` as a closure mode
- a same-session example that omits `Transient Refs` or `Task Memory`
- a checkpoint render that includes `control_effects`
- a root example that teaches `yield` after `release_green` or root `release_blocked`
- a non-root parent example that teaches `release_blocked` or terminal `blocked`
```

## Completeness Rule

The prompt layer is complete when:

- every dispatchable runtime phase maps to one of the two prompt families
- semantic assignment handoff and runtime-resolved durable refs are rendered as separate prompt surfaces
- reusable `record_checkpoint` and boundary wording stays registered through the exact blocks
- generated examples derive from the same section order and send-mode rules

## Related Contracts

- [Prompt contract](contract.md)
- [Prompt source and sections](source-and-sections.md)
- [Rendered examples](generated/rendered-examples.md)
