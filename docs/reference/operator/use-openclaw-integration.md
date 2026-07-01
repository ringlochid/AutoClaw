# Use the OpenClaw integration

Use this page when you need the shipped OpenClaw-facing surfaces from this checkout. It covers callback HTTP, mounted node MCP, mounted operator MCP, operator reads, and task-scoped observability.

## Keywords

- OpenClaw integration
- node MCP
- operator MCP
- callback lane
- task-scoped observability

## Current checkout boundary

This repo proves the API-side callback lane plus the mounted MCP surfaces that OpenClaw worker and operator clients target.

Use this page for shipped AutoClaw behavior. Do not use it as proof for any external client package, publication metadata, or UI component outside this checkout.

The shipped adapter is OpenClaw Gateway. Model/provider routing belongs to OpenClaw for this path; controller-owned assignment, checkpoint, artifact, wait, replan, and closure truth belongs to AutoClaw.

## Repo-proven integration surfaces

Current callback lane:

- `POST /callback/tasks/{task_id}/checkpoint`
- `POST /callback/tasks/{task_id}/boundary`
- `POST /callback/tasks/{task_id}/tools/{tool_name}`

Current mounted node-tool surface, when MCP mounts are enabled:

- `/node/mcp`
- tools: `search_definitions`, `get_definition`, `record_checkpoint`, `return_boundary`, `open_human_request`, `start_command_run`, `assign_child`, `add_child`, `update_child`, `remove_child`, `release_green`, and `release_blocked`
- every node-tool call must carry explicit `session_key` and `task_id`

Current shipped facts:

- the mounted node-MCP wrapper surface mirrors the strict surfaced wrapper contracts on both request and success bodies
- `assign_child`, `add_child`, `update_child`, and `remove_child` each keep their own typed `payload` contract, while `release_green` and `release_blocked` stay payload-free
- `open_human_request` and `start_command_run` each use their own typed `request` body and are gated by separate node capabilities
- node-operation success is surfaced through typed `CheckpointRead`, `BoundaryRead`, `HumanRequestOpenResponse`, `CommandRunStartResponse`, `AssignChildSuccess`, `AddChildSuccess`, `UpdateChildSuccess`, `RemoveChildSuccess`, `ReleaseGreenSuccess`, and `ReleaseBlockedSuccess` wrapper contracts

Current operator and support HTTP reads:

- `GET /runtime/tasks/{task_id}`
- `GET /operator/tasks/{task_id}/snapshot`
- `GET /operator/tasks/{task_id}/trace`
- `GET /control/tasks/{task_id}/human-requests`
- `GET /control/tasks/{task_id}/command-runs`
- `GET /observability/tasks/{task_id}/delivery-state`
- `GET /observability/tasks/{task_id}/continuity-state`
- `GET /observability/tasks/{task_id}/watchdog-state`
- `GET /observability/tasks/{task_id}/provider-events`

Current auth and session facts visible in this repo:

- callback writes require explicit `session_key` together with the route `task_id`
- mounted node-tool calls resolve the same live authority from explicit `session_key` plus `task_id`
- operator HTTP reads are protected by `X-AutoClaw-API-Key`
- callback and node-tool writes are validated against live `NodeSession`, current dispatch, current assignment, and current attempt truth

## What this checkout does not prove

- external OpenClaw client packaging outside this repo
- browser-console component wiring beyond the placeholder `apps/console/src/` tree
- publication metadata outside the shipped package surface

## Configuration facts

- runtime and OpenClaw settings live in local AutoClaw configuration
- AutoClaw mounts `/node/mcp` and the operator MCP app when MCP mounts are enabled
- callback and operator auth are enforced at the API layer
- trusted operator agents should use operator MCP or equivalent operator-authorized backend surfaces
- humans can act as trusted operators, but their natural surface is the UI over the same operator-authorized backend controls
- when this page says operator without a qualifier, read it as a trusted external operator agent or operator-authorized client

## Related pages

- [OpenClaw integration boundary](openclaw-integration-boundary.md)
- [API route families and lane map](../api/api-surface-and-route-map.md)
- [API trust lanes](../api/api-trust-lanes.md)
