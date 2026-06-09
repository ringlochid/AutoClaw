# Use the OpenClaw bridge integration

Status: Reference

Last verified: 2026-05-21

This page describes the bridge-facing surfaces that are visible from this checkout and the limits of what this repo can verify on its own.

## Keywords

- current bridge plugin
- node MCP
- operator MCP
- callback lane
- task-scoped observability

## Current checkout boundary

This repo proves the API-side callback lane plus the mounted MCP surfaces that a bridge or plugin must target.

It does not include the separate bridge-plugin package or its manifest, so this page does not claim a revalidated plugin-local tool inventory.

## Repo-proven bridge-facing surfaces

Current callback lane:

- `POST /callback/tasks/{task_id}/checkpoint`
- `POST /callback/tasks/{task_id}/boundary`
- `POST /callback/tasks/{task_id}/tools/{tool_name}`

Current mounted node-tool surface, when MCP mounts are enabled:

- `/node/mcp`
- tools: `search_definitions`, `get_definition`, `record_checkpoint`, `return_boundary`, `assign_child`, `add_child`, `update_child`, `remove_child`, `release_green`, and `release_blocked`
- every node-tool call must carry explicit `session_key` and `task_id`

Current shipped facts:

- the mounted node-MCP wrapper surface now mirrors the strict surfaced wrapper contracts on both request and success bodies
- `assign_child`, `add_child`, `update_child`, and `remove_child` each keep their own typed `payload` contract, while `release_green` and `release_blocked` stay payload-free
- node-operation success is surfaced through typed `CheckpointRead`, `BoundaryRead`, `AssignChildSuccess`, `AddChildSuccess`, `UpdateChildSuccess`, `RemoveChildSuccess`, `ReleaseGreenSuccess`, and `ReleaseBlockedSuccess` wrapper contracts

Current operator and support HTTP reads that an external bridge can rely on:

- `GET /runtime/tasks/{task_id}`
- `GET /operator/tasks/{task_id}/snapshot`
- `GET /operator/tasks/{task_id}/trace`
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

- a separate bridge-plugin manifest or source tree
- plugin-local capability flags
- browser-console component wiring beyond the placeholder `apps/console/src/` tree
- packaging or publication metadata for a standalone bridge-plugin repo

## Configuration facts

- runtime and OpenClaw settings live in local AutoClaw configuration
- AutoClaw mounts `/node/mcp` and the operator MCP app when MCP mounts are enabled
- callback and operator auth are enforced at the API layer
- if you need plugin packaging or manifest truth, inspect the separate bridge-plugin repo outside this checkout

Use this page only for shipped current behavior.
