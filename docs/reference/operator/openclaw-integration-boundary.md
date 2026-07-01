# OpenClaw integration boundary

This page captures the shipped OpenClaw integration boundary that worker clients and operator tooling must honor.

The current repo-owned contract is controller-side dispatch, prompt rendering, callback HTTP, mounted node MCP, mounted operator MCP, and runtime readbacks.

## Keywords

- OpenClaw integration boundary
- dispatch session binding
- callback lane
- node MCP mount
- operator MCP mount
- explicit-argument node-tool boundary

## Transport boundary

Current shipped facts:

- the controller prepares and accepts dispatch turns before callback or node-tool writes are legal
- callback HTTP writes use the task-scoped path plus explicit `session_key`
- static `node MCP` writes use explicit `session_key` + `task_id` tool arguments
- callback HTTP and static `node MCP` both validate the same presented `session_key` plus `task_id` against live `NodeSession`, current dispatch, current assignment, and current attempt truth
- prompt bundles and persisted transport-request artifacts are materialized under `_runtime/dispatch/<dispatch_id>/`
- dispatch, node-session, delivery-state, continuity-state, watchdog-state, and provider-event rows remain controller truth; prompt files are derived projections

## Callback and node MCP baseline

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
- `open_human_request(session_key, task_id, request)`
- `start_command_run(session_key, task_id, request)`
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

- the mounted node-MCP wrapper surface preserves the strict typed request and result shapes the runtime expects
- `assign_child`, `add_child`, `update_child`, and `remove_child` each keep their own typed `payload` contract, while `release_green` and `release_blocked` stay payload-free
- `open_human_request` and `start_command_run` each take a typed `request` body and create their external wait directly when the current dispatch authority and node capability allow it
- node-operation success is surfaced through typed `CheckpointRead`, `BoundaryRead`, `HumanRequestOpenResponse`, `CommandRunStartResponse`, `AssignChildSuccess`, `AddChildSuccess`, `UpdateChildSuccess`, `RemoveChildSuccess`, `ReleaseGreenSuccess`, and `ReleaseBlockedSuccess` wrapper contracts

That means the current tree locally proves:

- worker, parent, and root writes are session-rooted
- callback HTTP and static `node MCP` share one server-side authority path
- prompt and session continuity are dispatch-bound
- manifest and checkpoint lineage remain controller-owned prompt and runtime truth, not caller-authored write-envelope fields
- human-request waits and command-run waits are separate capability-driven node operations

## Current prompt-source rule

The current runtime no longer ships one monolithic integration prompt string.

Repo-owned prompt truth is split across:

- exact static blocks in `apps/api/src/autoclaw/runtime/prompt/assets/blocks/*.md`
- the asset catalog in `apps/api/src/autoclaw/runtime/prompt/assets/catalog.json`
- dynamic prompt assembly in `apps/api/src/autoclaw/runtime/prompt/instructions.py` and `apps/api/src/autoclaw/runtime/prompt/sections/rendering.py`
- persisted dispatch artifacts under `_runtime/dispatch/<dispatch_id>/`

## Documentation guardrails

This page must not imply that:

- prompt files or dispatch observability files outrank controller-owned dispatch, node-session, or manifest rows
- a separate callback-binding table owns callback authority in the shipped tree
- local wrapper bootstrap owns controller transport authority
- human-request capability and command-run capability are one bundled capability

## Related pages

- [Use the OpenClaw integration](use-openclaw-integration.md)
- [Runtime read models and operator surfaces](runtime-read-models-and-operator-surfaces.md)
- [API trust lanes](../api/api-trust-lanes.md)
