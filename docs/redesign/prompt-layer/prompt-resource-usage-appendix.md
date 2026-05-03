# Prompt resource and usage appendix

Status: Reference

This appendix collects implementation-detail reminders for the live v1 prompt layer.

It is a secondary reference. If it drifts from the owner docs in this folder, the owner docs win.

Use the owner pages for semantics:

- [contract.md](contract.md)
- [source-and-sections.md](source-and-sections.md)
- [field-renderers.md](field-renderers.md)
- [render-and-persistence.md](render-and-persistence.md)
- [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md)
- [prompt-pack/runtime-rule-blocks.md](prompt-pack/runtime-rule-blocks.md)

## Section inventory

The live section order is:

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

Static same-session continuation sections are:

- `operating_model`
- `task_identity`
- `node_purpose`

## Current read order

The prompt should teach this read order:

1. `_runtime/workflow-manifest.*`
2. `_runtime/attempts/<attempt_id>/assignment.*`
3. `_runtime/attempts/<attempt_id>/latest-checkpoint.*` when one is surfaced or when the current turn depends on prior checkpoint evidence
4. surfaced durable refs from `criteria` and `consumes`
5. optional `transient_refs`
6. `task_memory_search_hints`, then `context/wiki/` and other curated docs under `context/` if needed

## Filesystem guidance

The prompt layer should consistently teach:

- `workspace/` = mutable current-assignment work
- `context/criteria/` = explicit criteria files
- `context/wiki/` = curated task-memory pages
- other curated files under `context/` = source/reference material
- `outputs/artifacts/` = durable published outputs and evidence
- `tmp/transfers/` = optional transient carryover
- `_runtime/` = controller-generated projections and monitoring

## Render reminders

### Assignment

Render:

- `summary`
- `instruction`
- `criteria`
- `consumes`
- `produces`
- optional `transient_refs`
- optional `task_memory_search_hints`

### Checkpoint

Render:

- `checkpoint_kind`
- `outcome`
- `summary`
- `next_step`
- optional `blockers`
- optional `risks`
- optional surfaced compact refs

### Compact refs

Artifact refs surface only:

- `slot`
- `version`
- `path`
- `description`

Non-artifact durable refs surface only:

- `kind`
- optional `slot`
- `path`
- `description`

Transient refs surface only:

- `path`
- `description`

## Prompt artifact expectations

The prompt layer maintains these secondary implementation artifacts:

- [prompt-catalog.yaml](prompt-catalog.yaml)
- [generated/inventory.md](generated/inventory.md)
- [generated/rendered-examples.md](generated/rendered-examples.md)

They are useful for generation and validation, but if they drift from the live owner docs, the owner docs win and the artifacts must be regenerated.

## Exact Prompt Lookup Table

Use this quick table when you need the exact live page for one prompt-layer question.

| Need                                                              | Exact page                                                                                                                           |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| exact shared system block                                         | [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md)                                                 |
| exact provider continuity block                                   | [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md)                                                 |
| exact worker legality block                                       | [prompt-pack/runtime-rule-blocks.md](prompt-pack/runtime-rule-blocks.md)                                                             |
| exact parent/root legality block                                  | [prompt-pack/runtime-rule-blocks.md](prompt-pack/runtime-rule-blocks.md)                                                             |
| exact `same_session_continue` wrapper wording                     | [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md)                                                 |
| exact worker full prompt example                                  | [generated/rendered-examples.md](generated/rendered-examples.md)                                                                     |
| exact parent/root full prompt example                             | [generated/rendered-examples.md](generated/rendered-examples.md)                                                                     |
| exact `same_session_continue` wrapper                             | [generated/rendered-examples.md](generated/rendered-examples.md)                                                                     |
| exact `full_prompt` / `same_session_continue` request composition | [composition-example.md](composition-example.md)                                                                                     |
| exact authored task title / summary / instruction launch shape    | [../workflows/task-compose-schema.md](../workflows/task-compose-schema.md)                                                           |
| exact generated section order                                     | [generated/inventory.md](generated/inventory.md)                                                                                     |
| exact prompt-layer validation/reject wording                      | [prompt-pack/validation-and-reject-blocks.md](prompt-pack/validation-and-reject-blocks.md)                                           |
| exact API reject carrier fields                                   | [../interfaces/api-schema-appendix.md](../interfaces/api-schema-appendix.md)                                                         |
| exact boundary-precondition rule                                  | [../architecture/runtime-boundary-and-controller-loop-contract.md](../architecture/runtime-boundary-and-controller-loop-contract.md) |

## Searchability note

Live exact-query intents should route as live prompt-layer questions:

- `exact system prompt` [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md)
- `exact validation message` [prompt-pack/validation-and-reject-blocks.md](prompt-pack/validation-and-reject-blocks.md)
- `exact reject payload` [prompt-pack/validation-and-reject-blocks.md](prompt-pack/validation-and-reject-blocks.md) and [../interfaces/api-schema-appendix.md](../interfaces/api-schema-appendix.md)
- `exact same-session wrapper` [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md) and [generated/rendered-examples.md](generated/rendered-examples.md)
- `exact request composition` [composition-example.md](composition-example.md)

Historical search terms remain:

- old dispatch families
- packet or bundle prose
- flow/scope manifest prompt inputs
- `WorkerContext`
- `instruction_text`

Those historical terms should route to compatibility pages only. The live exact-query intents above are part of the current prompt contract.
