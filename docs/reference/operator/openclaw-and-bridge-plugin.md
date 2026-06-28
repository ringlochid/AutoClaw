# OpenClaw and bridge integration baseline

Status: Reference

Last verified: 2026-05-23

This page captures the shipped OpenClaw boundary that bridge tooling and worker clients are expected to honor.

The current repo does not ship the older standalone bridge-plugin source tree or the old dedicated bridge transport modules. This page focuses on the controller-side dispatch, prompt, callback, and mounted MCP contract that AutoClaw exposes today.

## Keywords

- current OpenClaw boundary
- dispatch session binding
- callback lane
- node MCP mount
- explicit-arg node-tool boundary

## Transport boundary

Current shipped facts:

- the controller prepares and accepts dispatch turns before callback or node-tool writes are legal
- callback HTTP writes use the task-scoped path plus explicit `session_key`
- static `node MCP` writes use explicit `session_key` + `task_id` tool arguments
- callback HTTP and static `node MCP` both validate the same presented `session_key` plus `task_id` against live `NodeSession`, current dispatch, current assignment, and current attempt truth
- prompt bundles and persisted transport-request artifacts are materialized under `_runtime/dispatch/<dispatch_id>/`
- dispatch, node-session, delivery-state, continuity-state, watchdog-state, and provider-event rows remain controller truth; prompt files are derived projections

## Current callback and plugin lane baseline

The shipped repo proves the callback lane and the mounted MCP wrapper surfaces, not a separate bridge-plugin source tree.

Repo-visible callback HTTP surfaces are:

- `POST /callback/tasks/{task_id}/checkpoint`
- `POST /callback/tasks/{task_id}/boundary`
- `POST /callback/tasks/{task_id}/tools/{tool_name}`

These callback writes require explicit `session_key` input on the request. The current shipped tree does not use a separate callback-binding authority row or hidden callback-only binding secret as the write contract.

Repo-visible static `node MCP` surfaces are mounted under `/node/mcp` when the main app enables MCP mounts and expose:

- `search_definitions(session_key, task_id, ...)`
- `get_definition(session_key, task_id, ...)`
- `record_checkpoint(session_key, task_id, checkpoint)`
- `return_boundary(session_key, task_id, boundary)`
- `assign_child(session_key, task_id, payload, expected_structural_revision_id?)`
- `add_child(session_key, task_id, payload, expected_structural_revision_id?)`
- `update_child(session_key, task_id, payload, expected_structural_revision_id?)`
- `remove_child(session_key, task_id, payload, expected_structural_revision_id?)`
- `release_green(session_key, task_id, expected_structural_revision_id?)`
- `release_blocked(session_key, task_id, expected_structural_revision_id?)`

Current shipped helper note:

- local wrapper bootstrap can derive dispatch-local `task_id` and `session_key` for convenience
- that helper path does not replace the explicit-argument callback or `node MCP` boundary
- `x-session-key` and other hidden-binding paths are not the supported v1 `node MCP` interface taught by this tree

Current shipped wrapper facts:

- the mounted node-MCP wrapper surface now preserves the strict typed request and result shapes the runtime expects
- `assign_child`, `add_child`, `update_child`, and `remove_child` each keep their own typed `payload` contract, while `release_green` and `release_blocked` stay payload-free
- node-operation success is surfaced through typed `CheckpointRead`, `BoundaryRead`, `AssignChildSuccess`, `AddChildSuccess`, `UpdateChildSuccess`, `RemoveChildSuccess`, `ReleaseGreenSuccess`, and `ReleaseBlockedSuccess` wrapper contracts

That means the current tree locally proves:

- worker, parent, and root writes are session-rooted
- callback HTTP and static `node MCP` share one server-side authority path
- prompt and session continuity are dispatch-bound
- manifest and checkpoint lineage remain controller-owned prompt and runtime truth, not caller-authored write-envelope fields

The current repo does not contain the old bridge-plugin implementation, so exact plugin capability flags and raw plugin tool inventories are not revalidated here.

## Current prompt-source rule

The current runtime no longer ships one monolithic bridge-only prompt string.

Repo-owned prompt truth is split across:

- exact static blocks in `apps/api/src/autoclaw/runtime/prompt/assets/blocks/*.md`
- the asset catalog in `apps/api/src/autoclaw/runtime/prompt/assets/catalog.json`
- dynamic prompt assembly in `apps/api/src/autoclaw/runtime/prompt/instructions.py` and `apps/api/src/autoclaw/runtime/prompt/sections/rendering.py`
- persisted dispatch artifacts under `_runtime/dispatch/<dispatch_id>/`

The current prompt-source details are summarized in this page rather than split into a second public reference page.

## Documentation guardrails

This page must not imply that:

- the old bridge-plugin repository is present in this tree
- prompt files or dispatch observability files outrank controller-owned dispatch, node-session, or manifest rows
- a separate callback-binding table still owns callback authority in the shipped tree
- local wrapper bootstrap owns controller transport authority

## Related pages

- [Runtime read models and operator surfaces](runtime-read-models-and-operator-surfaces.md)
- [API trust lanes](../api/api-trust-lanes.md)
