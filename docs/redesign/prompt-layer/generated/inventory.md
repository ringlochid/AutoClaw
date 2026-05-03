# Generated Prompt Inventory

Status: Generated reference

This page inventories the current generated prompt contract surfaces.

## Canonical Section Order

1. `operating_model`
2. `task_identity`
3. `node_purpose`
4. `current_dispatch`
5. `workflow_manifest`
6. `current_assignment`
7. `latest_checkpoint_context`
8. `consumed_durable_refs`
9. `transient_refs`
10. `task_memory`
11. `allowed_actions_now`
12. `publication_rule`

## Static Continuation Sections

- `operating_model`
- `task_identity`
- `node_purpose`

## Canonical Prompt Families

- `worker_dispatch_prompt`
- `parent_root_dispatch_prompt`

## Canonical Send Modes

- `full_prompt`
- `same_session_continue`

## Exact Block Registry

- `autoclaw_system_block_v1`
  - owner: `prompt-pack/system-and-provider-block.md`
  - role: `exact_system_block`
- `autoclaw_provider_continuity_block_v1`
  - owner: `prompt-pack/system-and-provider-block.md`
  - role: `provider_transport_rule`
- `autoclaw_parent_worker_split_v1`
  - owner: `prompt-pack/system-and-provider-block.md`
  - role: `dispatch_audience_split`
- `autoclaw_same_session_continue_wrapper_v1`
  - owner: `prompt-pack/system-and-provider-block.md`
  - role: `same_session_transport_wrapper`
- `runtime_legality_block_worker_v1`
  - owner: `prompt-pack/runtime-rule-blocks.md`
  - role: `worker_legality_rule`
- `runtime_legality_block_parent_v1`
  - owner: `prompt-pack/runtime-rule-blocks.md`
  - role: `parent_root_legality_rule`
- `runtime_boundary_rule_block_v1`
  - owner: `prompt-pack/runtime-rule-blocks.md`
  - role: `boundary_rule`
- `retry_handover_rule_v1`
  - owner: `prompt-pack/runtime-rule-blocks.md`
  - role: `retry_rule`
- `runtime_read_order_rule_v1`
  - owner: `prompt-pack/runtime-rule-blocks.md`
  - role: `read_order_rule`
- `current_task_state_frame_v1`
  - owner: `prompt-pack/runtime-rule-blocks.md`
  - role: `section_coverage_rule`
- `artifact_render_rule_v1`
  - owner: `prompt-pack/runtime-rule-blocks.md`
  - role: `artifact_render_rule`
- `task_memory_rule_v1`
  - owner: `prompt-pack/runtime-rule-blocks.md`
  - role: `task_memory_rule`
- `monitoring_not_task_truth_v1`
  - owner: `prompt-pack/runtime-rule-blocks.md`
  - role: `monitoring_rule`
- `same_session_continue_rule_v1`
  - owner: `prompt-pack/runtime-rule-blocks.md`
  - role: `same_session_rule`
- `worker_runtime_opening_example_v1`
  - owner: `prompt-pack/runtime-rule-blocks.md`
  - role: `runtime_opening_example`
- `parent_root_runtime_opening_example_v1`
  - owner: `prompt-pack/runtime-rule-blocks.md`
  - role: `runtime_opening_example`

## Generated Artifact Registry

- `rendered_examples`
  - file: `generated/rendered-examples.md`

## Generated Example Registry

- `parent_root_dispatch_prompt_full_prompt`
  - rendered heading: `parent_root_dispatch_prompt`
  - family: `parent_root_dispatch_prompt`
  - send mode: `full_prompt`
- `worker_dispatch_prompt_full_prompt`
  - rendered heading: `worker_dispatch_prompt`
  - family: `worker_dispatch_prompt`
  - send mode: `full_prompt`
- `worker_dispatch_prompt_same_session_continue`
  - rendered heading: `worker_dispatch_prompt same_session_continue`
  - family: `worker_dispatch_prompt`
  - send mode: `same_session_continue`
- `parent_root_dispatch_prompt_same_session_continue`
  - rendered heading: `parent_root_dispatch_prompt same_session_continue`
  - family: `parent_root_dispatch_prompt`
  - send mode: `same_session_continue`
- `worker_dispatch_prompt_blocked_ending_sketch`
  - rendered heading: `worker_dispatch_prompt blocked-ending sketch`
  - family: `worker_dispatch_prompt`
  - send mode: `full_prompt`
