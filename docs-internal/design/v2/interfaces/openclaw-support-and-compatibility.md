# OpenClaw support and compatibility

Status: Target

This page defines the external local support contract for the `openclaw` provider.

## Support status

OpenClaw is a targeted external provider. The operator installs, configures, upgrades, and supervises OpenClaw and its Gateway independently from AutoClaw.

OpenClaw is not included in `autoclaw[managed]`. AutoClaw owns only its narrow Gateway adapter, stable Node MCP integration, setup checks, and dispatch-time control requests.

## Supported Gateway shape

The initial supported baseline uses a documented `webchat` client path. AutoClaw configures Gateway handshake client mode independently from the agent delivery channel:

```toml
[openclaw]
enabled = true
gateway_url = "ws://127.0.0.1:18789"
client_mode = "webchat"
delivery_channel = "webchat"
```

The values may differ when the installed OpenClaw contract supports that combination.

`backend` is configurable and experimental only when the installed OpenClaw version exposes a supported third-party identity and the full launch, disconnect, MCP, resume, and abort suite passes. AutoClaw must not impersonate OpenClaw's reserved internal `gateway-client` identity.

## Setup ownership

```text
autoclaw openclaw setup
```

The setup flow may:

- collect or validate the Gateway endpoint and documented client identity
- register or verify the stable AutoClaw Node MCP endpoint for the selected worker integration
- keep handshake client mode and delivery channel independent
- verify that the OpenClaw worker can access the local AutoClaw task workspace
- run bounded launch and abort conformance

It must not:

- install or upgrade the full OpenClaw product
- take over Gateway process supervision
- rewrite unrelated OpenClaw agents or user configuration
- weaken Gateway bind, TLS, pairing, or authentication policy
- create an AutoClaw-managed operator-agent profile
- require Operator MCP for provider readiness

## Workspace and MCP readiness

The selected OpenClaw worker must be able to reach AutoClaw Node MCP and operate on the task workspace expected by the local integration. AutoClaw does not require one fixed `~/.openclaw/workspaces/<agent_id>` layout or globally disable OpenClaw sandboxing.

Readiness is behavior-based:

- the worker can connect to Node MCP and discover its logical tools
- task and node recognition values from the live `NodeSession` are accepted
- the worker can read current context and commit an AutoClaw plan and boundary
- provider-native questions and approvals do not create an invisible wait
- accepted launch survives control-connection release when that mode is declared supported
- a fresh control connection can abort the active session

Operator MCP is not part of OpenClaw worker readiness.

## Session and stop behavior

AutoClaw keeps the OpenClaw session key as the provider session hint. The adapter creates the key when starting a fresh provider conversation. A Gateway run id may remain private for precise abort but does not enter the generic persisted runtime model.

`start()` calls `agent` and waits only for acceptance. `stop()` uses `sessions.abort` through the same centralized provider-control policy and succeeds only when the supported abort response establishes the adapter-owned stop boundary. AutoClaw does not depend on `agent.wait`, Gateway tool events, or provider completion.

## Status and doctor

```text
autoclaw provider status openclaw
autoclaw provider doctor openclaw
autoclaw doctor --provider openclaw
```

The checks report:

- enabled and default-provider state
- Gateway endpoint and installed OpenClaw version when discoverable
- supported client identity, handshake mode, and delivery channel
- auth presence and connection result without credential content
- Node MCP registration and reachability
- local task-workspace compatibility
- launch acceptance and disconnect behavior
- fresh-connection abort behavior
- webchat support status and separate backend experimental status

A failed OpenClaw check blocks OpenClaw dispatches only; it does not block AutoClaw startup.

## Non-goals

- AutoClaw does not manage the full OpenClaw installation or security posture.
- AutoClaw does not persist Gateway lifecycle events, tool streams, or provider terminal state as runtime truth.
- AutoClaw does not promise backend mode before the upstream identity and conformance rules are satisfied.
- AutoClaw does not maintain a long-lived Gateway connection unless the supported installed version requires one privately.

## Related contracts

- [Provider support and compatibility](provider-support-and-compatibility.md)
- [Provider CLI and doctor](provider-cli-and-doctor.md)
- [OpenClaw Gateway adapter](../architecture/adapters/openclaw-gateway.md)
