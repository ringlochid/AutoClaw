# Codex app-server adapter

Status: Target

This page maps the official Codex Python SDK and its local app-server runtime into the minimal AutoClaw provider adapter.

## Confirmed external behavior

- The official `openai-codex` Python package controls a local Codex app-server over JSON-RPC. Published SDK builds include a pinned Codex runtime, while a custom binary is optional: [Codex SDK Python library](https://developers.openai.com/codex/sdk/#python-library).
- App-server exposes thread start and resume, turn start, and turn interrupt. Threads carry conversation context while turns are individual agent runs: [Codex app-server](https://developers.openai.com/codex/app-server).
- Codex supports ChatGPT and API-key authentication, stores its own credentials under the Codex home or OS credential store, and refreshes them itself: [Codex authentication](https://developers.openai.com/codex/auth).
- Codex reads normal user and trusted-project configuration, including model, reasoning, sandbox, approval, project instructions, skills, MCP, and compaction settings: [Codex configuration reference](https://developers.openai.com/codex/config-reference).
- App-server owns provider-native approval and streamed event protocols. Those protocols are client integration surfaces, not evidence of AutoClaw task success: [Codex app-server](https://developers.openai.com/codex/app-server).

## AutoClaw mapping

AutoClaw installs the tested `openai-codex` SDK dependency and uses its bundled runtime by default. A separate global `codex` executable is not a prerequisite for this managed path.

The mapping is:

- one provider session hint is one Codex thread id
- one AutoClaw dispatch starts one turn in a new or resumed thread
- the active turn handle remains private to the adapter and `AgentControlManager`
- `stop()` interrupts that active turn and returns only after the adapter can establish that the turn and any turn-owned background work can no longer continue
- app-server output is drained privately and never updates controller progress or completion

For every fresh or resumed start, the adapter applies an ephemeral correctness overlay:

- task workspace as the current working directory
- current `instructions_text` and `input_text`
- AutoClaw Node MCP as a required managed-agent MCP server
- a non-interactive approval policy
- the selected workspace sandbox policy
- optional AutoClaw model or effort overrides

The overlay must not rewrite the user's `config.toml`. Normal user and trusted-project Codex configuration, `AGENTS.md`, skills, and provider-owned authentication remain active beneath the overlay. AutoClaw leaves model choice, reasoning effort, model context metadata, and compaction settings unset unless the operator explicitly provides a sparse override.

AutoClaw preserves the thread id after each successful start. If resume cannot apply the current instruction layer reliably, the adapter starts a new thread with the full prompt and returns the replacement id.

Provider-native approvals must not wait for an app-server UI. The adapter resolves them non-interactively according to the AutoClaw machine policy, and the worker prompt routes human direction through AutoClaw MCP.

`autoclaw codex login` delegates authentication to the official Codex login protocol. Codex stores the credentials; AutoClaw stores neither tokens nor `auth.json` contents.

## Open assumptions and non-goals

- Exact request fields used for per-thread MCP and instruction overrides remain an adapter implementation detail until the pinned SDK version is selected and conformance-tested.
- Stop conformance must include any background terminal or process owned by the active turn. Failure to establish the stop boundary is a retryable control failure, not a successful interrupt.
- Unix socket or `stdio` app-server transport may be selected privately. Experimental app-server WebSocket transport is not required.
- AutoClaw does not persist generic Codex turn ids, provider events, diffs, token streams, or provider terminal state.
- AutoClaw does not add a generic context-window option. Codex's model catalog and native configuration own actual capacity and compaction behavior.
- A separately installed Codex CLI may be supported later as an explicit custom-runtime choice, but it is not the default managed integration.

## Related contracts

- [Minimal provider adapter contract](../adapter-contract.md)
- [Provider CLI and doctor](../../interfaces/provider-cli-and-doctor.md)
- [Codex support and compatibility](../../interfaces/codex-support-and-compatibility.md)
- [Node and operator MCP surface contract](../../interfaces/node-and-operator-mcp-surface-contract.md)
