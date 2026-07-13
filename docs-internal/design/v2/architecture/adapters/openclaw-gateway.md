# OpenClaw Gateway adapter

Status: Target

This page maps an externally managed OpenClaw Gateway into the minimal AutoClaw provider adapter.

## Confirmed external behavior

- OpenClaw Gateway is a WebSocket control plane. Its `agent` request accepts work and returns a run id and acceptance time before the agent run completes: [OpenClaw agent loop](https://docs.openclaw.ai/agent-loop).
- `sessions.abort` can abort a session by session key and may accept a run id for a more precise abort: [OpenClaw Gateway protocol](https://docs.openclaw.ai/gateway/protocol).
- Gateway handshake client mode and the agent request's delivery channel are separate protocol fields: [OpenClaw Gateway protocol](https://docs.openclaw.ai/gateway/protocol).
- The device-less `gateway-client` plus `backend` identity is a reserved trusted same-process or loopback control path. Custom automation should use a supported device identity, pairing, or another documented integration path rather than impersonating that internal identity: [OpenClaw Gateway protocol](https://docs.openclaw.ai/gateway/protocol), [OpenClaw trusted proxy authentication](https://docs.openclaw.ai/gateway/trusted-proxy).

## AutoClaw mapping

OpenClaw remains independently installed, configured, and supervised. AutoClaw neither bundles the Gateway nor manages its full lifecycle.

The mapping is:

- one provider session hint is the OpenClaw session key
- the adapter creates a fresh key when no hint is supplied and returns the effective key from `start()`
- `start()` opens a Gateway control connection, submits `agent`, waits only for acceptance, and then releases the connection when the supported Gateway path permits it
- `stop()` opens a control connection, calls `sessions.abort`, and returns only after the supported response establishes that the targeted active turn can no longer continue
- an optional run id and any retained connection remain private adapter control details
- Gateway events, `agent.wait`, tool events, and provider completion never update controller progress or close the AutoClaw dispatch

The launch request maps `instructions_text` to OpenClaw `extraSystemPrompt` and `input_text` to the agent `message`. Gateway handshake `client.mode` and the agent request `channel` are configured independently; sharing one constant is not part of the adapter contract.

The supported baseline is a documented `webchat` client path. A `backend` mode may be configured and tested only when the installed OpenClaw version exposes a supported third-party identity and the full adapter conformance suite passes. AutoClaw must never claim the reserved internal `gateway-client` identity merely to obtain backend behavior.

The OpenClaw worker must be able to reach the stable AutoClaw Node MCP endpoint and the local task workspace. OpenClaw MCP setup is provider-local configuration; per-dispatch task and node recognition still uses the AutoClaw `NodeSession` values rendered into the current prompt.

## Open assumptions and non-goals

- Disconnect-after-acceptance must be proven against each supported OpenClaw version. If an installed version requires a live Gateway connection, the adapter may retain one privately without ingesting its events as runtime truth.
- `backend` remains experimental for AutoClaw until upstream provides a supported external identity and both launch and abort conformance pass. Only the webchat path is promised by the initial support contract.
- AutoClaw does not persist a generic Gateway run id, provider terminal state, tool-event stream, or process-local event registry.
- AutoClaw does not install, upgrade, expose, authenticate, or supervise the entire OpenClaw deployment.

## Additional conformance requirements

The OpenClaw adapter must prove:

- Node MCP plan, progress, wait, and boundary operations work with provider events disabled
- disconnecting after accepted launch does not terminate the supported run
- a fresh control connection can abort the active session
- abort success satisfies the generic stop boundary; an unknown or unsupported result fails the control call
- fresh and resumed session hints work
- handshake client mode and delivery channel can differ
- webchat passes as the supported baseline
- backend passes the same suite before it is enabled experimentally

## Related contracts

- [Minimal provider adapter contract](../adapter-contract.md)
- [Provider CLI and doctor](../../interfaces/provider-cli-and-doctor.md)
- [OpenClaw support and compatibility](../../interfaces/openclaw-support-and-compatibility.md)
- [Node and operator MCP surface contract](../../interfaces/node-and-operator-mcp-surface-contract.md)
