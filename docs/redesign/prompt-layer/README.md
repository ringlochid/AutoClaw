# Prompt Layer

Status: Owner index

This folder owns the canonical frozen v1 prompt contract for the current runtime model.

Read this folder with this mental model first:

- controller/DB state owns runtime truth
- prompts are derived execution briefs over manifest, assignment, checkpoint, and surfaced refs
- the manifest is the whole-workflow picture, the assignment is the current mission, and the checkpoint is the durable "what happened / what next" handoff
- semantic assignment handoff stays separate from exact runtime-resolved durable refs in `consumed_durable_refs`
- files under `_runtime/dispatch/` are observability projections, not ordinary assignment truth
- structural edits start from surfaced role/policy names in the compact `structural_edit_palette`, may use the current-only `search_definitions` / `get_definition` lookup lane when that palette is insufficient, and runtime revalidates committed names on commit
- if surfaced context is insufficient or conflicting, reread current truth, search hinted curated files, and use a legal checkpoint or current-node boundary instead of guessing
- `tool` is the canonical runtime term
- `plugin` is adapter-specific only
- v1 surfaced refs are path-only
- shipped exact prompt blocks are app-owned packaged text assets under `apps/api/app/runtime/prompt/assets/`
- prompt-pack markdown pages are audited mirrors of those shipped assets

## Start Here

Read in this order:

1. [INDEX.md](INDEX.md)
2. [contract.md](contract.md)
3. [source-and-sections.md](source-and-sections.md)
4. [field-renderers.md](field-renderers.md)
5. [render-and-persistence.md](render-and-persistence.md)
6. [machine-contract.md](machine-contract.md)
7. [prompt-pack/README.md](prompt-pack/README.md)
8. [generated/README.md](generated/README.md)

## Canonical Live Owners

- [contract.md](contract.md) overall prompt contract, section order, prompt
  families, and the live `full_prompt` redispatch model
- [source-and-sections.md](source-and-sections.md) source provenance and section ownership
- [field-renderers.md](field-renderers.md) exact compact render rules for assignments, checkpoints, and surfaced refs
- [render-and-persistence.md](render-and-persistence.md) persisted prompt artifacts and transport wrapper rules
- [machine-contract.md](machine-contract.md) machine-readable catalog and validation expectations
- [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md) exact shared system, provider, and parent/worker split blocks
- [prompt-pack/runtime-rule-blocks.md](prompt-pack/runtime-rule-blocks.md) exact worker/parent legality blocks plus shared runtime wording fragments
- [prompt-pack/validation-and-reject-blocks.md](prompt-pack/validation-and-reject-blocks.md) exact prompt-layer reject wording and boundary-precondition examples

## Secondary Live References

These pages are live supporting references and readback aids. They must not override the canonical owners above, but they are not historical migration stubs:

- [composition-example.md](composition-example.md) exact `full_prompt` composition
- [generated/rendered-examples.md](generated/rendered-examples.md) generated or canonicalized rendered prompt body readback for worker and parent/root
- [generated/README.md](generated/README.md) generated artifact routing and authority rule
- [legality-and-coverage.md](legality-and-coverage.md) coverage summary and cross-check reference
- [prompt-resource-usage-appendix.md](prompt-resource-usage-appendix.md) implementation reminders and exact-query routing appendix

## Exact Text And Validation Routes

Use these routes when the question is "what exact text do I send or expect?"

| Need                                                                                    | Exact owner                                                                                                                                                                                                                         |
| --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----- | -------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| exact shared system block                                                               | [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md) -> `autoclaw_system_block_v1`                                                                                                                  |
| exact provider continuity block                                                         | [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md) -> `autoclaw_provider_continuity_block_v1`                                                                                                     |
| exact boundary wording reused by every prompt family                                    | [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md) -> `autoclaw_system_block_v1` and [prompt-pack/runtime-rule-blocks.md](prompt-pack/runtime-rule-blocks.md) -> `runtime_boundary_rule_block_v1` |
| exact parent/worker split block                                                         | [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md) -> `autoclaw_parent_worker_split_v1`                                                                                                           |
| exact worker legality block                                                             | [prompt-pack/runtime-rule-blocks.md](prompt-pack/runtime-rule-blocks.md) -> `runtime_legality_block_worker_v1`                                                                                                                      |
| exact parent/root legality block                                                        | [prompt-pack/runtime-rule-blocks.md](prompt-pack/runtime-rule-blocks.md) -> `runtime_legality_block_parent_v1`                                                                                                                      |
| exact rendered worker or parent/root prompt                                             | [generated/rendered-examples.md](generated/rendered-examples.md)                                                                                                                                                                    |
| exact `full_prompt` request composition                                                | [composition-example.md](composition-example.md)                                                                                                                                                                                    |
| exact role/policy instruction assembly                                                  | [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md) and [../interfaces/role-and-policy-definition-schema.md](../interfaces/role-and-policy-definition-schema.md)                                   |
| exact authored task-intent launch shape                                                 | [../workflows/task-compose-schema.md](../workflows/task-compose-schema.md)                                                                                                                                                          |
| exact generated section order and family inventory                                      | [generated/inventory.md](generated/inventory.md) and [machine-contract.md](machine-contract.md)                                                                                                                                     |
| exact prompt-layer reject wording examples                                              | [prompt-pack/validation-and-reject-blocks.md](prompt-pack/validation-and-reject-blocks.md)                                                                                                                                          |
| exact API reject carrier fields such as `code`, `field_path`, and `suggested_next_step` | [../interfaces/api-schema-appendix.md](../interfaces/api-schema-appendix.md)                                                                                                                                                        |
| exact boundary-precondition meaning for `yield`, `green`, `retry`, and `blocked`        | [../architecture/runtime-boundary-and-controller-loop-contract.md](../architecture/runtime-boundary-and-controller-loop-contract.md)                                                                                                 |
| exact route/lane legality for checkpoint, boundary, and tool calls                      | [../interfaces/api-surface-and-trust-lane-map.md](../interfaces/api-surface-and-trust-lane-map.md)                                                                                                                                  |

## Search-First Questions

- "What does the prompt always teach?" [contract.md](contract.md)
- "What is the exact system block to paste into the runtime prompt?" [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md)
- "What is the exact worker or parent legality block?" [prompt-pack/runtime-rule-blocks.md](prompt-pack/runtime-rule-blocks.md)
- "Where does each section come from?" [source-and-sections.md](source-and-sections.md)
- "How should refs and artifacts render?" [field-renderers.md](field-renderers.md)
- "What is persisted versus inline transport?" [render-and-persistence.md](render-and-persistence.md)
- "What are the machine-readable prompt families and section ids?" [machine-contract.md](machine-contract.md)
- "Where is the machine-readable generated catalog?" [prompt-catalog.yaml](prompt-catalog.yaml)
- "Where are the exact worker and parent/root prompt examples?" [generated/rendered-examples.md](generated/rendered-examples.md)
- "Where is the exact `full_prompt` request composition?" [composition-example.md](composition-example.md)

Compatibility note:

- canonical v1 runtime control keeps same-session continuity only for parent/root same-attempt redispatch, still opens a fresh live run, and still resends the full regenerated prompt package
- canonical v1 static `node MCP` uses explicit `task_id` + `session_key` in dispatch-local prompt state; hidden/plugin/header binding is deferred to v2
- "Where is role/policy description and instruction assembly defined?" [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md) and [../interfaces/role-and-policy-definition-schema.md](../interfaces/role-and-policy-definition-schema.md)
- "Where is the authored task title / summary / instruction launch shape?" [../workflows/task-compose-schema.md](../workflows/task-compose-schema.md)
- "What wording should be reused verbatim?" [prompt-pack/README.md](prompt-pack/README.md)
- "Where are the exact validation and reject wording blocks?" [prompt-pack/validation-and-reject-blocks.md](prompt-pack/validation-and-reject-blocks.md)
- "Where are generated examples and inventories?" [generated/README.md](generated/README.md)
- "Where is the exact validation or reject payload shape?" [prompt-pack/validation-and-reject-blocks.md](prompt-pack/validation-and-reject-blocks.md) and [../interfaces/api-schema-appendix.md](../interfaces/api-schema-appendix.md)
- "Where is the exact boundary-precondition rule that prompt closure text must match?" [../architecture/runtime-boundary-and-controller-loop-contract.md](../architecture/runtime-boundary-and-controller-loop-contract.md)

## Historical And Compatibility Material

These pages remain for migration/search compatibility and must not overrule the canonical owners above:

- [historical-prompt-and-artifact-layers.md](historical-prompt-and-artifact-layers.md)
- historical prompt-pack compatibility pages called out in [prompt-pack/README.md](prompt-pack/README.md)

Treat those pages as:

- `Reference` = secondary explanation or coverage summary
- `Generated reference` = generated inventory or rendered example
- `Generated reference index` = generated/readback routing page
- `Historical` = migration/search router only

## Generated Material Rule

`prompt-catalog.yaml` and the files under `generated/` are implementation artifacts and secondary references.

The shipped exact block source is the app-owned asset catalog under
`apps/api/app/runtime/prompt/assets/`. The prompt-pack docs mirror those assets
for human routing and validation.

They are useful for validation and examples, but if they drift from the live owner docs, the live owner docs win and the generated artifacts must be regenerated.

For prompt-driven runtime validation and reject wording, the prompt layer must stay aligned with:

- [../architecture/runtime-boundary-and-controller-loop-contract.md](../architecture/runtime-boundary-and-controller-loop-contract.md)
- [../interfaces/api-surface-and-trust-lane-map.md](../interfaces/api-surface-and-trust-lane-map.md)
- [../interfaces/api-schema-appendix.md](../interfaces/api-schema-appendix.md)
