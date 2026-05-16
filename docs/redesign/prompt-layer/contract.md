# Prompt Contract

Status: Target

This page defines the canonical frozen v1 prompt contract for the current runtime model.

## Core Rule

The prompt is a derived execution brief over controller-owned truth.

The prompt must teach:

- `dispatch` is the only controller -> node ingress boundary
- `record_checkpoint` is the durable publication lane for what happened and what should happen next
- `yield | green | retry | blocked` are the only public node -> controller egress boundaries
- parent/root nodes use explicit control tools plus `record_checkpoint` during an open dispatch
- worker/leaf nodes use `record_checkpoint` plus terminal boundaries
- `assign_child` authors only semantic `assignment_intent`, `supplemental_durable_context`, and explicit `transient_surfaces` handoff, not final durable ref metadata
- runtime resolves exact current durable refs into `consumed_durable_refs`
- runtime authors final durable publication metadata after required outputs exist
- workflow definition YAML is hidden source material; manifest, assignment, checkpoint, and surfaced refs are the visible runtime contract
- worker reread is filesystem-first; callback is a write-only semantic lane

## Canonical Prompt Families

Freeze only two public base prompt surfaces:

1. `worker_dispatch_prompt`
2. `parent_root_dispatch_prompt`

All other provider, adapter, or recovery-specific variants are transport wrappers, secondary references, or generated examples over these two prompt families.

## Exact Prompt Assembly Route

Shipped exact prompt blocks live under `apps/api/app/runtime/prompt/assets/`. The prompt-pack markdown pages remain human-readable mirrors of those shipped assets and must stay byte-for-byte aligned with them, including trailing newline preservation.

If you need copy-ready prompt text instead of just the semantic contract, assemble it from these exact asset-backed owners in this order:

1. [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md) -> `autoclaw_system_block_v1`
2. [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md) -> `autoclaw_provider_continuity_block_v1` when send-mode wording is relevant; keep it aligned to the shipped Phase 4A truth that dispatch control emits `full_prompt` today
3. [prompt-pack/system-and-provider-block.md](prompt-pack/system-and-provider-block.md) -> `autoclaw_parent_worker_split_v1`
4. [prompt-pack/runtime-rule-blocks.md](prompt-pack/runtime-rule-blocks.md) -> `runtime_boundary_rule_block_v1`
5. [prompt-pack/runtime-rule-blocks.md](prompt-pack/runtime-rule-blocks.md) -> `runtime_legality_block_worker_v1` or `runtime_legality_block_parent_v1`
6. render current node kind, current node purpose/description, role description, role instruction, policy description, and policy instruction into the static provider-side `instructions` channel
7. render the canonical section order from this page into the dynamic prompt `input` body using the section-source rules in [source-and-sections.md](source-and-sections.md)
8. check the final assembled shape against [generated/rendered-examples.md](generated/rendered-examples.md)

The full provider dispatch request is therefore:

- `instructions` = static provider-side system/instructions channel
- `input` = dynamic rendered prompt body for this turn
- reserved internal transport metadata such as prior-provider response binding when a later owning phase explicitly activates it

## Canonical Section Order

Every full prompt renders sections in this order:

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

## Reserved Transport Continuity Note

Current code still persists an adapter-private `same_session_continue`
wrapper shape, but canonical parent/root same-session redispatch does not
depend on that send mode and Phase 4.5 treats that persistence as transitional
implementation debt.

Canonical consequence:

- every live dispatch sends the full canonical prompt package
- parent/root same-attempt redispatch still resends the full canonical prompt package on the same `sessionKey`
- no canonical live redispatch path omits static sections from the provider request
- the persisted full prompt artifact contains the whole section set in canonical order

If a later owning phase activates that reserved wrapper, it remains an adapter detail only and still does not redefine the canonical v1 dispatch/session/run control model.

## Common Prompt Rules

Every prompt should teach all of the following in ordinary language:

- controller/DB state owns runtime truth
- manifest, assignment, checkpoint, and published artifacts are generated shared surfaces derived from that truth
- monitoring files under `_runtime/dispatch/` are observability projections, not normal assignment truth
- the manifest is the whole-workflow visible contract
- task identity is global task input visible to every node
- the first/root assignment is generated at launch from task identity plus current node purpose and resolved role/policy wording
- assignment says what this node owns now
- assignment `summary` plus optional `instruction` are current mission prose:
  - generated by runtime/system for the first/root assignment
  - staged by parent/root for later child assignments
- assignment `criteria` and `consumes` are runtime-resolved read-now surfaces, not parent-authored durable ref metadata
- assignment `produces` are requirements, not already-published refs
- exact current durable refs live in `consumed_durable_refs`
- `record_checkpoint` writes the durable handoff through checkpoint `summary`, `next_step`, blockers, risks, surfaced artifact refs, surfaced transient refs, and task-memory hints
- parent -> child context comes from semantic assignment handoff
- child -> parent, parent -> parent, and same-node retry context comes from checkpoint plus surfaced refs
- child -> child is parent-mediated through the next assignment plus surfaced durable refs or optional `transient_refs`
- `yield` is legal only after exactly one staged child assignment exists for the open parent/root dispatch
- `release_green` and root `release_blocked` are terminal preconditions, not `yield` basis
- parent/root structural edits start from the compact `structural_edit_palette` already surfaced in the current prompt or manifest context; current-only `search_definitions` / `get_definition` reads are the legal read-only escalation path before commit when the palette is still insufficient, and runtime revalidates committed names on commit
- parent/root does not use definition revision history as a normal planning input
- if surfaced context is still insufficient after reread and hinted file search, publish the gap durably or choose a legal current-node boundary instead of guessing
- `context/wiki/` contains curated task-memory pages
- other curated files under `context/` are source/reference material such as user docs, PDFs, screenshots, and notes
- do not guess hidden files or scan arbitrary directories instead of the surfaced paths and curated search roots
- role/policy names for structural edits must come from the surfaced `structural_edit_palette` or, when the current dispatch explicitly surfaces that read-only lane, current-only definition lookup; do not guess them from transcript memory
- surfaced refs are path-only in v1
- non-artifact surfaced refs still keep `kind` in v1
- prompts should surface compact artifact refs only, not full pointer internals
- prompts must not teach or expect checkpoint `control_effects`
- v1 static `node MCP` may surface `task_id` and `session_key` in dispatch-local prompt state only
- prompt-visible context does not include callback header values, callback env var names, or auth-file paths
- prompt text must tell the worker not to print or persist `session_key` outside node tool calls unless unavoidable

## Read Order Rule

The prompt should teach this read order:

1. `_runtime/workflow-manifest.*`
2. current `_runtime/attempts/<attempt_id>/assignment.*`
3. current relevant `_runtime/attempts/<attempt_id>/latest-checkpoint.*` when one is surfaced or when the current turn depends on prior checkpoint evidence
4. surfaced `consumed_durable_refs`
5. optional `transient_refs`
6. `task_memory_search_hints`, then search `context/wiki/` and other curated docs under `context/` if needed

The prompt should also make the surfaced read roots explicit:

- stable manifest path
- current assignment path
- latest checkpoint path when present
- surfaced durable-ref paths
- surfaced transient-ref paths when present

## Family Matrix

| Prompt                        | Audience                                      | Core action surface                                                                                           | Must include                                                                                                                                                                          |
| ----------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `worker_dispatch_prompt`      | worker, review, QA, release, audit leaf nodes | do the current assignment, use `record_checkpoint`, close with `green`, `retry`, or `blocked`                 | manifest ref, assignment ref, latest relevant checkpoint ref when surfaced, consumed durable refs, optional transient refs, task-memory search hints, result/boundary reminder        |
| `parent_root_dispatch_prompt` | parent and root nodes                         | use control tools, use `record_checkpoint` when reasoning must persist, close non-terminal turns with `yield` | manifest ref, assignment ref, latest relevant checkpoint ref when surfaced, surfaced durable refs when relevant, task-memory search hints when relevant, tool list, boundary reminder |

## Worked Family Intent

### `worker_dispatch_prompt`

The worker version should read like:

```text
Here is the one assignment you own now.
Treat the assignment as the current mission surface: prose, runtime-resolved durable reads, produce requirements, and explicit transient carryover.
Read the latest checkpoint as durable handoff from `record_checkpoint`.
Read `consumed_durable_refs` for the exact current durable refs the runtime resolved for this turn.
When you finish, call `record_checkpoint` and then close with `green`, `retry`, or `blocked`.
```

### `parent_root_dispatch_prompt`

The parent/root version should read like:

```text
Here is the current workflow picture and the latest surfaced child evidence.
Use `assign_child` with semantic `assignment_intent`,
`supplemental_durable_context`, and explicit `transient_surfaces` only; do not
author final durable ref metadata for the child.
Read `consumed_durable_refs` before making child-assignment or release decisions.
If you use `add_child`, `update_child`, or `remove_child`, reread the current
manifest first, start with the surfaced `structural_edit_palette` in the
current prompt or manifest, use current-only definition lookup only when the
current dispatch explicitly surfaces that read-only lane and the palette is
still insufficient, then reread the regenerated manifest before deciding
whether one child assignment should be staged.
Do not use definition revision history as normal parent/root planning input.
If one child assignment is staged and the dispatch stays non-terminal, call `record_checkpoint` when later readers need the reasoning and then emit `yield`.
If you commit `release_green` or root `release_blocked`, later close with the matching terminal boundary instead of `yield`.
```

## Canonical Prompt Delivery

The canonical v1 prompt contract assumes full prompt regeneration for every dispatch.

Callback write authority is runtime/launcher-private and must not be rendered into prompt sections or provider `instructions`.

The shipped Phase 4A runtime also sends the regenerated prompt through `full_prompt` on every dispatch. Any reserved adapter-private same-session transport reuse remains below the core runtime contract and must not be treated as live run reuse until a later owning phase makes it real.

## Validation And Reject Alignment

This page does not own machine reject envelopes.

When prompt text tells a node to use a tool or emit a boundary, the exact validation and reject surfaces live here:

- [prompt-pack/validation-and-reject-blocks.md](prompt-pack/validation-and-reject-blocks.md) for exact prompt-layer reject wording and worked examples
- [../architecture/runtime-boundary-and-controller-loop-contract.md](../architecture/runtime-boundary-and-controller-loop-contract.md) for exact `dispatch`, `record_checkpoint`, `yield`, `green`, `retry`, and `blocked` meaning
- [../interfaces/api-surface-and-trust-lane-map.md](../interfaces/api-surface-and-trust-lane-map.md) for route/lane legality
- [../interfaces/api-schema-appendix.md](../interfaces/api-schema-appendix.md) for carrier names such as `AssignChildPayload`, `CheckpointWrite`, and boundary request shapes

## Removed From The Live V1 Prompt Contract

- flow/scope manifest split
- flow brief / scope brief dependency
- `WorkerContext` as the canonical prompt contract name
- old callback legality blocks
- `writable_roots`
- old child retry or reassignment control wording
- bundle / handoff / packet / scope-key prompt framing
- checkpoint `control_effects`
- internal `dispatch_id` as canonical node-facing prompt context

## Related Contracts

- [Prompt source and sections](source-and-sections.md)
- [Prompt machine contract](machine-contract.md)
- [Rendered examples](generated/rendered-examples.md)
