# Provider selection and runtime config

Status: Target

This page defines provider selection, sparse machine-local configuration, and launch provenance for the local V2 runtime.

## Core rule

Provider selection is a launch decision made before a dispatch is committed. It is not a runtime state machine and never contributes watchdog truth.

One committed dispatch has one resolved provider. Start and stop retries never switch that provider.

## Authored provider preference

V2 workflow nodes may carry one optional portable selector:

```yaml
provider_preference: openclaw | codex | claude | null
```

When omitted, the machine-local default provider is requested. The field belongs to a workflow node, not a role or policy definition, and may appear on root, parent, or worker nodes.

The field must not contain model names, executable paths, endpoint URLs, credentials, sandbox objects, or provider-native session ids.

## Resolution before dispatch commit

Resolution proceeds in this order:

1. Use the node preference when present; otherwise request `runtime.default_provider`.
2. Check whether that provider is enabled and ready on this host.
3. When a non-default requested provider is unavailable, try the one configured default provider.
4. Commit the dispatch only after one provider is resolved and its readiness preflight passes.
5. Persist requested and resolved provider provenance on the dispatch readback.

There is no multi-hop fallback chain. If neither candidate is ready, no dispatch opens. Resolution and readiness preflight do not call adapter `start()`: the controller commits the dispatch, prompt, and `NodeSession` first, then the central manager performs provider I/O.

After commit:

- all six start calls use the resolved provider
- all six stop calls use the same resolved provider
- any later replacement or continuation performs provider resolution again before its new dispatch is committed
- a replacement may resolve to another provider, but it omits a session hint created by the earlier provider

## Sparse machine-local config

The target config is intentionally small:

```toml
[runtime]
default_provider = "codex"

[codex]
enabled = true
# model = "..."          # optional AutoClaw override
# effort = "high"        # optional AutoClaw override

[claude]
enabled = false
# model = "sonnet"       # optional AutoClaw override
# effort = "high"        # optional AutoClaw override

[openclaw]
enabled = false
gateway_url = "ws://127.0.0.1:18789"
client_mode = "webchat"
delivery_channel = "webchat"
```

Rules:

- `runtime.default_provider` must name an enabled provider.
- Each provider section owns only AutoClaw-specific enablement, connection fields, and sparse model or effort overrides that the operator deliberately sets.
- OpenClaw handshake `client_mode` and delivery channel are independent fields.
- Provider-native auth material never belongs in this config.
- Codex and Claude native model catalogs, settings, project instructions, skills, compaction, and authentication are inherited rather than copied into AutoClaw config.
- There is no generic `context_window` option. Effective capacity is model- and provider-owned.

The effective precedence is:

1. AutoClaw correctness overlay: task workspace, prompt lanes, Node MCP, and non-interactive permissions
2. explicit sparse AutoClaw model or effort override
3. provider-native user and project configuration
4. provider defaults

## Local execution assumption

This phase is local-first and same-host. Provider and file adapters are code boundaries, not remote services.

For managed Codex and Claude integrations, the AutoClaw process, bundled provider runtime, Node MCP endpoint, and task workspace share one OS environment and filesystem namespace. Provider-native configuration and authentication must be visible to the AutoClaw service identity through values such as `HOME`, `CODEX_HOME`, or `CLAUDE_CONFIG_DIR`.

An AutoClaw process inside WSL or a container uses runtimes and paths inside that environment. It must not assume that a provider CLI or credential store in a different host namespace is transparently available.

OpenClaw is externally managed, but its worker still needs network access to Node MCP and filesystem access to the local task workspace expected by the configured integration.

## Provenance and failure readback

The minimum persisted launch provenance is:

```yaml
provider_resolution:
    requested_provider: openclaw | codex | claude
    resolved_provider: openclaw | codex | claude
```

Provider session hints and SDK/runtime versions may appear in bounded support readback, but they do not replace controller task, attempt, or dispatch identity.

Pre-commit resolution failure uses one stable family:

```yaml
provider_resolution_failure:
    code: provider_resolution_failed
    requested_provider: openclaw | codex | claude
    attempted_provider: openclaw | codex | claude
    stage: readiness | auth | configuration
    message: string
```

No secret value, raw provider credential, or unbounded provider output may appear in the failure record. A provider `start()` failure after dispatch commit uses the runtime's bounded provider-control readback and `control_failed` closure instead; it never re-enters provider fallback inside that dispatch.

## Startup isolation

An unavailable or misconfigured provider never prevents the AutoClaw API from starting. Startup loads provider configuration and reports readiness independently for each provider. Only a dispatch that resolves to an unavailable provider is blocked.

This allows operators to repair one provider through the CLI while other configured providers and controller surfaces remain available.

## Non-goals

This contract does not define:

- role-level provider binding
- task-level provider hot swap
- multi-provider dispatches
- distributed provider services or remote workspaces
- provider-native context-window normalization
- credentials stored by AutoClaw

## Related contracts

- [Workflow node schema](workflow-node-schema.md)
- [Provider support and compatibility](provider-support-and-compatibility.md)
- [Provider CLI and doctor](provider-cli-and-doctor.md)
- [Minimal provider adapter contract](../architecture/adapter-contract.md)
- [Runtime lifecycle and watchdog](../architecture/runtime-lifecycle-and-watchdog.md)
