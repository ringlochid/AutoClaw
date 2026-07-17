# Claude support and compatibility

Status: Target

This page owns the local managed support contract for the `claude` route.

## Support status and packaging

Claude is a managed target provider. The supported base AutoClaw distribution includes the tested official Agent SDK integration and its compatible bundled Claude Code runtime; a separately installed global `claude` CLI is not required.

An explicit custom runtime may be added only as an advanced override that passes the same pinned adapter conformance. Installation alone does not configure or authenticate Claude.

## Authentication boundary

The supported product setup uses an Anthropic API credential or a supported cloud provider such as Bedrock or Vertex. AutoClaw stores no raw credential.

An externally managed Claude.ai login may be observable through native diagnostics, but AutoClaw does not offer or broker Claude.ai Free, Pro, or Max subscription authentication without Anthropic approval.

Status, check, and runtime must resolve the same service identity, `HOME`, `CLAUDE_CONFIG_DIR`, and cloud-provider environment.

## Configuration inheritance

The adapter explicitly loads supported Claude user, project, and local setting sources. It preserves the native `claude_code` system-prompt preset and applies current AutoClaw instructions through the supported ephemeral instruction override.

AutoClaw's nonpersistent dispatch overlay contains:

- exact task workspace/cwd;
- exact separate instruction and input lanes;
- one private managed Node MCP connection with a fresh bearer credential;
- the exact role-scoped Node tool allowlist;
- noninteractive native question/permission behavior;
- resolved provider-native tool/network policy; and
- optional sparse model/effort override.

It never writes the managed MCP credential or dispatch policy into native user/project configuration.

## Dynamic MCP attachment

Each provider-start attempt creates the supported programmatic Streamable HTTP MCP server configuration from the current managed binding and supplies a server-scoped allowed-tool set.

The exact SDK fields are pinned-version conformance details. The attachment remains per invocation, nonpersistent, semantic-only at the tool schema, role-scoped, and independently credentialed for concurrent dispatches.

## Start, continuity, and stop

One dispatch issues one new or continuity-assisted Claude query. A session ID/client may remain provider-private, but it is never controller authority or Node authentication.

Every start receives the complete current instruction and input lanes. If continuity cannot accept that exact request safely, the adapter starts a fresh session.

`start()` returns when the provider accepts responsibility. SDK messages, hooks, native tool events, output, and final response never advance controller state.

When supported, `stop(dispatch_id)` makes one bounded interrupt attempt. If the SDK requires an interrupted response to be consumed before client reuse, the adapter either discards that client or drains it privately as resource cleanup. Runtime does not wait for drain, does not hold a dispatch fence, and proceeds when stop is unsupported, fails, or times out.

## Noninteractive policy

`AskUserQuestion` and unresolved provider-native approvals must not wait for a UI AutoClaw does not consume. The adapter denies or resolves them under the declared machine policy. Intentional human direction uses AutoClaw `open_human_request` only.

Full native-tool access does not imply Node role elevation, controller command-run permission, or human-request capability.

## Status and check

Passive status may report enabled/default state, installed SDK/runtime versions, custom runtime path, effective config directory/setting sources, and credential-source presence without secret contents.

`autoclaw providers check claude` may perform documented non-agent installation, configuration, authentication/reachability, policy, and deterministic MCP prerequisite checks. It creates no session/query, task, dispatch, binding, or Node call.

## Required proof

- dynamic programmatic MCP attachment with a server-scoped role allowlist;
- exact two-lane delivery for fresh and continuity-assisted starts;
- no hidden `AskUserQuestion` or approval wait;
- supported API/cloud authentication boundary;
- acceptance and definite/uncertain failure classification;
- bounded interrupt without a runtime drain gate or client reuse violation;
- service-identity/native-home consistency; and
- no credential, provider-output, or private-binding leakage.

## External basis

- [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)
- [Claude Agent SDK Python reference](https://code.claude.com/docs/en/agent-sdk/python)
- [Claude Agent SDK MCP](https://code.claude.com/docs/en/agent-sdk/mcp)
- [Claude Agent SDK user input](https://code.claude.com/docs/en/agent-sdk/user-input)

## Related contracts

- [Provider support and compatibility](provider-support-and-compatibility.md)
- [Provider CLI and check](provider-cli-and-check.md)
- [Claude Agent SDK adapter](../architecture/adapters/claude-agent-sdk.md)
- [Managed Node MCP binding](../architecture/managed-node-mcp-binding.md)
