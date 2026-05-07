# Prompt Pack

Status: Target

This folder holds mirror docs for reusable wording blocks plus compatibility pages for the prompt layer.

The shipped exact wording blocks live under `apps/api/app/runtime/prompt/assets/`.
The exact-block sections in this folder must stay byte-aligned with those assets.
The prompt catalog classifies each exact block as either a live
`live_instruction_block` consumed by runtime instruction assembly or a
`reference_only` exact block kept for search, validation, or example routing.

## Canonical Live Prompt-Pack Pages

Read these first:

1. [runtime-rule-blocks.md](runtime-rule-blocks.md)
2. [system-and-provider-block.md](system-and-provider-block.md)
3. [validation-and-reject-blocks.md](validation-and-reject-blocks.md)

These are the live reusable wording owners for:

- controller/DB truth versus generated projections
- public boundary model
- tool usage and closure rules
- retry wording
- filesystem/task-memory wording
- provider transport wording
- reject wording and worked `boundary_precondition_failed` examples

## Exact Block Ownership

Use these exact block ids when you need copy-ready shared wording. Load the
shipped bytes from `apps/api/app/runtime/prompt/assets/`; use these docs as the
human-readable mirror and routing surface:

| Need                                          | Exact owner block                                                                                           |
| --------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| shared system/runtime block                   | [system-and-provider-block.md](system-and-provider-block.md) -> `autoclaw_system_block_v1`                  |
| provider continuity / transport block         | [system-and-provider-block.md](system-and-provider-block.md) -> `autoclaw_provider_continuity_block_v1`     |
| parent-versus-worker split block              | [system-and-provider-block.md](system-and-provider-block.md) -> `autoclaw_parent_worker_split_v1`           |
| same-session wrapper block                    | [system-and-provider-block.md](system-and-provider-block.md) -> `autoclaw_same_session_continue_wrapper_v1` |
| reusable boundary stanza                      | [runtime-rule-blocks.md](runtime-rule-blocks.md) -> `runtime_boundary_rule_block_v1`                        |
| worker legality block                         | [runtime-rule-blocks.md](runtime-rule-blocks.md) -> `runtime_legality_block_worker_v1`                      |
| parent/root legality block                    | [runtime-rule-blocks.md](runtime-rule-blocks.md) -> `runtime_legality_block_parent_v1`                      |
| current-task-state framing block              | [runtime-rule-blocks.md](runtime-rule-blocks.md) -> `current_task_state_frame_v1`                           |
| artifact compact-render reminder              | [runtime-rule-blocks.md](runtime-rule-blocks.md) -> `artifact_render_rule_v1`                               |
| task-memory guidance block                    | [runtime-rule-blocks.md](runtime-rule-blocks.md) -> `task_memory_rule_v1`                                   |
| monitoring-is-not-task-truth reminder         | [runtime-rule-blocks.md](runtime-rule-blocks.md) -> `monitoring_not_task_truth_v1`                          |
| exact reject wording and stale-guard examples | [validation-and-reject-blocks.md](validation-and-reject-blocks.md)                                          |

Pair these exact blocks with:

- [../generated/rendered-examples.md](../generated/rendered-examples.md) for secondary rendered prompt body readback
- [../field-renderers.md](../field-renderers.md) for section-level render rules
- [../source-and-sections.md](../source-and-sections.md) for section provenance

This folder owns reusable prompt wording blocks. It does not own machine reject envelopes or generated rendered prompt body readback.

## Historical Compatibility Pages

These pages remain searchable for migration/background only and must not overrule the live owner docs:

- [dispatch-family-packs.md](dispatch-family-packs.md)
- [state-and-boundary-overlays.md](state-and-boundary-overlays.md)
- [historical-packet-prose-examples.md](historical-packet-prose-examples.md)

## Search-First Routing

- "Where is the canonical runtime wording?" [runtime-rule-blocks.md](runtime-rule-blocks.md)
- "Where is the canonical system/provider wording?" [system-and-provider-block.md](system-and-provider-block.md)
- "Where is the exact same-session wrapper wording?" [system-and-provider-block.md](system-and-provider-block.md)
- "Where is the exact worker or parent/root legality text?" [runtime-rule-blocks.md](runtime-rule-blocks.md)
- "Where is the exact system block to paste into a runtime prompt?" [system-and-provider-block.md](system-and-provider-block.md)
- "Where is the exact rendered prompt body example that uses these blocks?" [../generated/rendered-examples.md](../generated/rendered-examples.md)
- "Where is the exact prompt-layer reject wording page?" [validation-and-reject-blocks.md](validation-and-reject-blocks.md)
- "Where are the exact prompt-layer reject wording and the current API reject carrier fields?" [validation-and-reject-blocks.md](validation-and-reject-blocks.md) and [../../interfaces/api-schema-appendix.md](../../interfaces/api-schema-appendix.md)
- "Where is the exact boundary-precondition rule the wording must match?" [../../architecture/runtime-boundary-and-controller-loop-contract.md](../../architecture/runtime-boundary-and-controller-loop-contract.md)
- "Where did old dispatch-family prompt packs go?" [dispatch-family-packs.md](dispatch-family-packs.md)
- "Where did packet or bundle prose examples go?" [historical-packet-prose-examples.md](historical-packet-prose-examples.md)
