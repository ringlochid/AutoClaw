# Claude support and compatibility

Status: Target

This page defines the local managed support contract for the `claude` provider.

## Support status

Claude is a targeted managed provider. AutoClaw uses the tested official Agent SDK and its bundled compatible Claude Code runtime by default.

The normal installation is:

```bash
pip install "autoclaw[claude]"
```

A separately installed global `claude` CLI is not required. An explicit custom runtime path may be supported as an advanced local override after it passes the same conformance suite.

## Authentication

The supported AutoClaw product setup uses an Anthropic API credential or a supported cloud provider such as Bedrock or Vertex:

```text
autoclaw claude setup
```

The command explains and validates the selected provider-owned environment or native Claude configuration. AutoClaw stores no raw credential.

Claude Code itself may have an externally managed Claude.ai login. AutoClaw may report that state for local diagnostics when the official SDK exposes it, but AutoClaw does not offer a Claude.ai login screen, broker subscription credentials, or market Free, Pro, or Max usage as an AutoClaw authentication path without Anthropic approval.

The AutoClaw service must run as the intended OS identity and see the same `HOME`, `CLAUDE_CONFIG_DIR`, and cloud-provider environment used during setup.

## Configuration inheritance

The managed adapter explicitly loads normal Claude user, project, and local setting sources. It preserves the `claude_code` system-prompt preset and appends current AutoClaw instructions.

Native settings may continue to own model, effort, thinking, skills, hooks, and project instructions. AutoClaw adds task cwd, Node MCP, the dispatch input, non-interactive permissions, and optional sparse model or effort overrides.

There is no AutoClaw-wide Claude context-window setting. The selected model, account, cloud provider, and Claude's native compaction own effective context behavior.

## Workspace, permission, and MCP readiness

The bundled runtime, AutoClaw process, task workspace, and Node MCP endpoint must share a compatible local execution environment.

Readiness requires:

- the SDK and bundled runtime can start
- the task workspace exists and is accessible under the selected tool and sandbox policy
- AutoClaw Node MCP connects through Streamable HTTP
- required Node MCP tools are permitted
- `AskUserQuestion` and unresolved provider-native approvals cannot wait for provider UI
- a fresh session can commit an AutoClaw plan and boundary
- the active SDK client can be interrupted and drained

Operator MCP is not part of Claude worker readiness.

## Session and stop behavior

AutoClaw keeps the Claude session id as the provider session hint. The active `ClaudeSDKClient` stays private. `stop()` interrupts that client, privately drains the interrupted response before any reuse, and succeeds only when the active query and its adapter-owned background work can no longer continue.

Resume always receives the current instructions and input. If the pinned version cannot refresh the instruction layer correctly, the adapter starts a fresh session and persists the replacement session id.

## Status and doctor

```text
autoclaw provider status claude
autoclaw provider doctor claude
autoclaw doctor --provider claude
```

The checks report:

- enabled and default-provider state
- installed SDK and bundled runtime versions
- custom runtime path when used
- credential source and presence without credential content
- effective Claude config directory and loaded setting sources
- task cwd, native-tool, permission, and sandbox compatibility
- Node MCP reachability and tool discovery
- fresh start, resume, interrupt, and drain conformance
- confirmation that provider-native questions cannot wait invisibly

Missing supported authentication points to `autoclaw claude setup`. A failed Claude check blocks Claude dispatches only; it does not block AutoClaw startup.

## Non-goals

- AutoClaw does not mirror all Claude settings into its own config.
- AutoClaw does not persist SDK messages, hook events, built-in tool events, or provider terminal state as runtime truth.
- AutoClaw does not translate `AskUserQuestion` into a second human-wait path.
- AutoClaw does not broker Claude.ai subscription authentication without approval.

## Related contracts

- [Provider support and compatibility](provider-support-and-compatibility.md)
- [Provider CLI and doctor](provider-cli-and-doctor.md)
- [Claude Agent SDK adapter](../architecture/adapters/claude-agent-sdk.md)
