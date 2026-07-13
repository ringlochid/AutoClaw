# Claude Agent SDK adapter

Status: Target

This page maps the official Claude Agent SDK into the minimal AutoClaw provider adapter.

## Confirmed external behavior

- Anthropic describes the Agent SDK as the Claude Code agent loop exposed as a library, with the same tools, context management, sessions, permissions, hooks, and MCP integration: [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview).
- The Python package bundles a compatible Claude Code executable by default. A custom `cli_path` is optional: [Claude Agent SDK Python package](https://github.com/anthropics/claude-agent-sdk-python).
- `ClaudeSDKClient` supports streaming multi-turn work, session resume, and interruption. After interruption, the client response must be drained before reuse: [Claude Agent SDK Python reference](https://code.claude.com/docs/en/agent-sdk/python).
- The SDK can load normal user, project, and local Claude settings, and can append instructions to the `claude_code` system-prompt preset: [Claude Agent SDK Python reference](https://code.claude.com/docs/en/agent-sdk/python).
- The SDK supports programmatic Streamable HTTP MCP servers and server-scoped allowed-tool patterns: [Claude Agent SDK MCP](https://code.claude.com/docs/en/agent-sdk/mcp).
- Claude's native `AskUserQuestion` and tool-permission callbacks can wait for input unless the embedding client configures a non-interactive policy: [Claude Agent SDK user input](https://code.claude.com/docs/en/agent-sdk/user-input).
- Anthropic says third-party products must not offer Claude.ai login or route their users through Free, Pro, or Max subscription credentials without prior approval. Agent SDK integrations should use supported API or cloud authentication: [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview#authentication).

## AutoClaw mapping

AutoClaw installs the tested `claude-agent-sdk` dependency and uses its bundled Claude Code runtime by default. A separate global `claude` executable is not a prerequisite for this managed path.

The mapping is:

- one provider session hint is one Claude session id
- one AutoClaw dispatch queries a new or resumed `ClaudeSDKClient` session
- the active client remains private to the adapter and `AgentControlManager`
- `stop()` interrupts that client, drains the interrupted response privately, and returns only after the active query and its adapter-owned background work can no longer continue
- SDK messages and hooks never update controller progress or completion

For every fresh or resumed start, the adapter applies an ephemeral correctness overlay:

- task workspace as the current working directory
- explicit loading of native user, project, and local setting sources
- the `claude_code` system-prompt preset with `instructions_text` appended
- `input_text` as the dispatch input
- AutoClaw Node MCP as a Streamable HTTP server
- provider-native approvals and questions configured not to wait
- optional AutoClaw model or effort overrides

The adapter disables `AskUserQuestion` and unresolved native approval waits. It permits the AutoClaw Node MCP tools required by the worker and applies the selected non-interactive machine policy to other native tools. Human direction and long-running controller waits go through AutoClaw MCP only.

AutoClaw preserves the Claude session id returned by SDK initialization. If resume cannot apply the current instruction layer reliably, the adapter starts a new session with the full prompt and returns the replacement id.

The supported AutoClaw setup path uses an Anthropic API credential or a supported cloud provider such as Bedrock or Vertex. Credentials remain in the provider-owned environment or configuration. AutoClaw may detect an externally managed Claude login for diagnostics, but it does not broker, store, or market Claude.ai subscription authentication.

## Open assumptions and non-goals

- The exact allowed native-tool set and sandbox combination remain pinned-version conformance details. They must preserve normal coding usefulness without creating a provider-native interactive wait.
- Stop conformance must prove that interrupt plus drain establishes the adapter-owned execution boundary. An uncertain result is a retryable control failure rather than successful stop.
- AutoClaw does not persist SDK messages, hook events, built-in tool events, token streams, or provider terminal state.
- AutoClaw does not expose a generic context-window setting. Claude model selection and native compaction own effective context behavior.
- A separately installed Claude Code executable may be supported later as an explicit custom-runtime choice, but it is not the default managed integration.
- Claude.ai subscription brokerage is out of scope unless Anthropic explicitly approves the product integration.

## Related contracts

- [Minimal provider adapter contract](../adapter-contract.md)
- [Provider CLI and doctor](../../interfaces/provider-cli-and-doctor.md)
- [Claude support and compatibility](../../interfaces/claude-support-and-compatibility.md)
- [Human request and approval contract](../../interfaces/human-request-and-approval-contract.md)
