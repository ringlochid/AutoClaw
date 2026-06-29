# Provider preference and runtime config

Status: Target

This page defines the V2 current-shape contract for node-level provider preference and machine-local provider configuration.

## Core rule

Provider preference should stay explicit and simple:

- workflow nodes may optionally express a provider preference
- machine-local config owns provider setup details plus one default provider
- fallback may use only the default provider
- fallback may happen only before dispatch acceptance

Portable authored definitions must not embed host paths, auth material, or provider-local transport details as reusable registry truth.

## Authored node field

V2 authored workflow nodes may include:

```yaml
provider_preference: openclaw | codex | claude | optional
```

Rules:

- `provider_preference` is optional
- when omitted, runtime resolves the node through the machine-local default provider
- `provider_preference` belongs to workflow nodes, not role or policy definitions
- `provider_preference` is authored preference, not a guarantee of final provider resolution
- `provider_preference` is a portable logical selector, not a model string, host path, socket path, auth ref, or sandbox config object

This field may appear on root, parent, or worker nodes.

## Machine-local config shape

The canonical local runtime config shape is:

```yaml
runtime:
    default_provider: openclaw | codex | claude
openclaw:
    # local OpenClaw gateway and wrapper settings
codex:
    # local Codex app-server or SDK settings
claude:
    # local Claude Agent SDK settings
```

Field meaning:

- `runtime.default_provider` is the machine-local default provider for nodes that do not set `provider_preference`
- `openclaw`, `codex`, and `claude` hold machine-local auth, transport, model, permission, and tool-surface configuration
- exact provider support constraints such as execution mode, sandbox mode, or workspace or workdir rules belong to the provider support pages and their machine-local config lanes rather than to portable authored workflow schema

Raw host paths, transport details, and local auth material are legal only in this machine-local config lane.

## Resolution rule

Provider resolution for one node attempt is:

1. if the node sets `provider_preference`, that becomes `requested_provider`
2. otherwise `requested_provider` is `runtime.default_provider`
3. runtime preflights and connects the requested provider
4. if the requested provider fails before dispatch acceptance and it is not already the default provider, runtime retries once with `runtime.default_provider`
5. if the default provider also fails, the dispatch does not open

## Launch compatibility rule

Before dispatch acceptance, runtime must verify that the requested or resolved provider can use the required provider-neutral AutoClaw node and operator MCP surfaces plus any required runtime-control wiring.

Rules:

- ordinary node MCP access is a provider/runtime compatibility fact, not a dispatch capability family
- if the requested provider cannot launch with the required shared MCP and runtime surfaces, runtime either falls back to the default provider or fails the dispatch before acceptance
- provider launch incompatibility must not open a dispatch and then masquerade as an ordinary controller capability rejection for node MCP access
- provider-specific auth, transport, approval, and session setup remain machine-local config or adapter concerns rather than authored workflow truth

## Fallback boundary

Fallback is intentionally narrow.

Rules:

- fallback is only from the requested provider to the one default provider
- fallback is only for preflight, bootstrap, auth, or connect failure before dispatch acceptance
- fallback must not silently chain across multiple providers
- once an attempt has started on a provider, that attempt stays pinned to that provider
- later retry or redispatch may choose a different provider, but that is a new controller-owned attempt decision rather than a hidden live switch

## Provenance and audit

Provider resolution should persist controller-owned provenance such as:

```yaml
provider_resolution:
    requested_provider: openclaw | codex | claude
    resolved_provider: openclaw | codex | claude
```

Rules:

- `requested_provider` is what authoring plus local default resolution asked for
- `resolved_provider` is the provider that actually owns the accepted attempt
- detailed fallback internals may stay in support-state or observability lanes, but the surfaced contract must still distinguish a successful accepted resolution from a pre-accept launch failure
- adapter session ids and model ids are secondary adapter evidence only; they do not replace controller lineage truth
- controller-owned provenance must never expose raw credentials or machine-local secret values

## Pre-accept launch failure surface

If the requested provider and the allowed default-provider fallback both fail before dispatch acceptance, the controller should surface one stable pre-accept failure family such as:

```yaml
provider_launch_failure:
    code: provider_launch_failed
    requested_provider: openclaw | codex | claude
    attempted_provider: openclaw | codex | claude
    stage: preflight | auth | bootstrap | connect
    message: string
```

Rules:

- this failure happens before dispatch acceptance and therefore must not masquerade as an accepted attempt that later changed provider
- `attempted_provider` is the provider whose final pre-accept launch failed; when no fallback was attempted, it matches `requested_provider`
- the minimum surfaced contract freezes `code`, `requested_provider`, `attempted_provider`, `stage`, and `message`
- deeper adapter evidence such as session ids, wrapper stderr, or auth diagnostics may stay in support-state or observability lanes

## Separation rule

Keep these lanes separate:

- portable role and policy definitions
- portable workflow node `provider_preference`
- machine-local provider config
- controller-owned task and dispatch truth

Node `provider_preference` is reusable authored intent.

Machine-local provider sections decide how this host reaches `openclaw`, `codex`, or `claude`.

Controller truth records the requested and resolved provider, not the raw machine-local config internals.

## Non-goals

This contract does not define:

- role-level provider binding
- task-compose provider override precedence
- multi-hop provider fallback chains
- mid-attempt hot-swap across providers
- identical lifecycle verbs for every provider family

## Related contracts

- [Workflow node schema](workflow-node-schema.md)
- [Role and policy definition schema](role-and-policy-definition-schema.md)
- [Provider support and compatibility](provider-support-and-compatibility.md)
- [Provider-aware setup, configure, and doctor](provider-aware-setup-and-doctor.md)
- [Node and operator MCP surface contract](node-and-operator-mcp-surface-contract.md)
- [Capability, security, and audit](capability-security-and-audit.md)
- [Control API and task event stream](control-api-and-task-event-stream.md)
- [Prompt system v2](../prompt-layer/prompt-system-v2.md)
- [Codex app-server adapter](../architecture/adapters/codex-app-server.md)
- [Claude Agent SDK adapter](../architecture/adapters/claude-agent-sdk.md)
