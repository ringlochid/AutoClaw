# Use the current OpenClaw bridge plugin

Status: Current

Last verified: 2026-04-26

This page describes the current bridge-plugin lanes and how to reason about them safely.

## Keywords

- current bridge plugin
- request_approval
- operatorQueries
- registryWrites
- raw operator query tools
- skill writes

## Worker-lane default

By default, the plugin exposes only bounded worker-lane tools needed for delegated execution:

- `record_checkpoint`
- acknowledge projected manifest
- `request_approval`
- `get_worker_bundle`
- `publish_context_item`
- `request_replan`

## Optional operator/query lanes

Optional capability flags expand the surface:

- `capabilities.operatorQueries=true`
- `capabilities.registryWrites=true`

Those flags add broader query and guarded write tools. They are not default worker-lane behavior.

They also do not make the delegated worker an operator by default.

Current raw operator/query tool names behind `capabilities.operatorQueries=true`:

- `get_flow_operator`
- `get_flow_runtime_slice`
- `get_flow_timeline_slice`
- `get_flow_audit`
- `get_registry_snapshot`
- `list_definition_versions`
- `validate_workflow_definition`

## Current optional registry-write tools

Current `capabilities.registryWrites=true` adds:

- `put_definition_draft`
- `publish_definition_version`
- `put_skill_draft`
- `publish_skill_version`

These are shipped current behavior, not target redesign truth.

## Current config facts

- `api.baseUrl` wins when explicitly set
- otherwise the plugin reads `api.configPath` or falls back to `~/.config/autoclaw/config.toml`
- that fallback path is current plugin-local behavior and can differ from the runtime's `platformdirs` default on Windows
- `api.internalApiKey` and `api.timeoutMs` can override config-derived values

## Current operator-write fact

Current browser/operator writes and deeper plugin writes are different surfaces.

- the bundled browser console can call public operator and registry mutation routes when the operator supplies a valid API key
- the bridge plugin keeps worker-lane tools as the default
- optional `capabilities.operatorQueries=true` and `capabilities.registryWrites=true` expand the plugin into deeper operator/support tooling lanes

## Target contrast

The redesign contract differs on purpose:

- target worker lane removes `request_approval`
- target standard operator-plugin reads collapse into operator-facing bundle surfaces instead of raw slice-by-slice names
- target standard operator-plugin writes exclude generic skill draft/publish

Use this page only for shipped current behavior. For the target contract, see [Plugin tool reference](../../redesign/interfaces/plugin-tool-reference.md).

## Evidence

- inspected code in `autoclaw-bridge-plugin-main/src/plugin-tools.ts`
- inspected code in `autoclaw-main/apps/console/src/App.tsx`
- inspected plugin manifest in `autoclaw-bridge-plugin-main/openclaw.plugin.json`
- inspected repo entry docs in `autoclaw-bridge-plugin-main/README.md`
