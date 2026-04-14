# Flow 00 — Data Model Snapshot

This example uses a task called `repair-bugfix`.

## Runtime snapshot

### task

- `task.id = task_repair_bf_001`
- `status = running`

### flow

- `flow.id = flow_repair_bf_001`
- `task_id = task_repair_bf_001`
- `seed_compiled_plan_id = cp_v5`
- `active_flow_revision_id = fr_002`
- `status = blocked`

### flow_revisions

- `fr_001` = initial compiled execution graph from `cp_v5`, `status = retired`
- `fr_002` = adopted replan from `cp_v7`, `status = active`, `parent_flow_revision_id = fr_001`

### flow_nodes

- `node_root` (`source_compiled_plan_node_id = cpn_root`, `state = running`)
- `node_impl_loop` (`source_compiled_plan_node_id = cpn_impl`, `state = waiting`)
- `node_validation` (`source_compiled_plan_node_id = cpn_val`, `state = ready`)

### node_attempts

- `na_impl_001` (`flow_node_id = node_impl_loop`, `number = 1`, `status = failed`)
- `na_impl_002` (`flow_node_id = node_impl_loop`, `number = 2`, `status = blocked`, `retry_of_node_attempt_id = na_impl_001`, `flow_id = flow_repair_bf_001`, `flow_revision_id = fr_002`)

### node_checkpoints

- for `na_impl_001`: `status = retry`
- for `na_impl_002`: `status = blocked`, `recommended_next_action = replan`, `wait_reason = approval`

### approvals

- `approval_001`: `flow_id = flow_repair_bf_001`, `flow_node_id = node_impl_loop`, `node_attempt_id = na_impl_002`, `status = pending`

### node_sessions

- `session_001`: `flow_node_id = node_impl_loop`, `node_attempt_id = na_impl_002`, `provider_session_key = ocl_abc123`, `status = active`

## Provenance chain

For `na_impl_002`, effective versions come from:

- `na_impl_002.flow_revision_id = fr_002`
- `fr_002.compiled_plan_id = cp_v7`
- `node_impl_loop.source_compiled_plan_node_id = cpn_impl`
- `cpn_impl.role_version_id = role_impl_v4`
- `cpn_impl.policy_version_id = policy_impl_v2`
- `cpn_impl.skill_bindings[*].skill_version_id = skill_debug_v8`, `skill_test_v3`

## Replan behavior

1. create `node_plan_revisions` proposal from `na_impl_002`
2. validate patch against the current graph
3. compile a new candidate `flow_revision`
4. adopt `fr_002` and retire `fr_001`
5. resume from a checkpoint boundary with history intact


Original flow seed lineage comes from:

- `flow.seed_compiled_plan_id = cp_v5`
- `cp_v5.workflow_version_id = wf_v3`
