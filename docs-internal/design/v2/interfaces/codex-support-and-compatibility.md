# Codex support and compatibility

Status: Target

This page defines the local managed support contract for the `codex` provider.

## Support status

Codex is a targeted managed provider. AutoClaw uses the tested official Python SDK and its pinned Codex runtime by default.

The normal installation is:

```bash
pip install "autoclaw[codex]"
```

A separately installed global `codex` CLI is not required. An explicit custom runtime path may be supported as an advanced local override after it passes the same conformance suite.

## Authentication

Supported Codex authentication is provider-owned ChatGPT or API-key authentication.

```text
autoclaw codex login
```

The command delegates to the official Codex login protocol, including the supported browser or device-code flow. Codex stores and refreshes credentials under its own home or OS credential store. AutoClaw does not read, copy, print, or persist the credential payload.

The AutoClaw service must run as the intended OS identity and see the same `HOME` and `CODEX_HOME` used during login.

## Configuration inheritance

The managed adapter inherits normal Codex configuration, including:

- user `config.toml`
- trusted-project `.codex/config.toml`
- `AGENTS.md` and project instructions
- Codex skills and user MCP servers
- native model, reasoning, compaction, and model-provider settings

AutoClaw applies only its ephemeral correctness overlay: task cwd, current prompt lanes, required Node MCP, non-interactive approvals, selected sandbox policy, and optional sparse model or effort overrides.

There is no AutoClaw-wide Codex context-window setting. The native model catalog and config own effective context and compaction.

## Workspace and MCP readiness

The bundled runtime, AutoClaw process, task workspace, and Node MCP endpoint must share a compatible local execution environment.

Readiness requires:

- the SDK and bundled runtime can start
- the task workspace exists and is accessible under the configured sandbox
- AutoClaw Node MCP connects as a required managed-agent server
- provider-native approvals cannot wait for a separate UI
- a fresh thread can commit an AutoClaw plan and boundary
- an active turn can be interrupted

Operator MCP is not part of Codex worker readiness.

## Session and stop behavior

AutoClaw keeps the Codex thread id as the provider session hint. The active turn handle stays private. `stop()` interrupts that turn through app-server, privately drains any remaining provider response required by the pinned SDK, and succeeds only when the active turn and its adapter-owned background work can no longer continue.

Resume always receives the current instructions and input. If the pinned version cannot refresh the instruction layer correctly, the adapter starts a fresh thread and persists the replacement thread id.

## Status and doctor

```text
autoclaw provider status codex
autoclaw provider doctor codex
autoclaw doctor --provider codex
```

The checks report:

- enabled and default-provider state
- installed SDK and bundled runtime versions
- custom runtime path when used
- auth type and presence without credential content
- effective Codex home and configuration sources
- task cwd and sandbox compatibility
- Node MCP reachability and tool discovery
- fresh start, resume, and interrupt conformance

Missing authentication points to `autoclaw codex login`. A failed Codex check blocks Codex dispatches only; it does not block AutoClaw startup.

## Non-goals

- AutoClaw does not mirror all Codex settings into its own config.
- AutoClaw does not persist turn ids, provider events, diffs, or terminal provider state as runtime truth.
- AutoClaw does not use provider-native approval requests as its human-wait lane.

## Related contracts

- [Provider support and compatibility](provider-support-and-compatibility.md)
- [Provider CLI and doctor](provider-cli-and-doctor.md)
- [Codex app-server adapter](../architecture/adapters/codex-app-server.md)
