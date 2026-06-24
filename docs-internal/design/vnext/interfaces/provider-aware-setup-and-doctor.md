# Provider-aware setup, configure, and doctor

Status: Target

This page defines the Vnext operator setup, configure, and doctor contract once `openclaw`, `codex`, and `claude` are first-class providers.

## Core rule

Operator setup becomes provider-first rather than OpenClaw-first.

The setup flow must help the operator choose providers, verify them, configure them, and pick one default provider before normal task execution relies on them.

The exact compatibility details for each provider family should live in provider support docs rather than being inferred from generic setup prose.

## Canonical command families

Vnext should own these operator-facing command families:

- `autoclaw onboard`
- `autoclaw configure`
- `autoclaw doctor`
- `autoclaw openclaw ...`
- `autoclaw codex ...`
- `autoclaw claude ...`

Rules:

- `onboard`, `configure`, and `doctor` are shared top-level operator flows
- `autoclaw openclaw`, `autoclaw codex`, and `autoclaw claude` are provider-specific branches for targeted setup or troubleshooting
- provider-specific branches must not redefine controller truth or authored workflow schema

## Onboard flow

The canonical onboard flow is:

1. choose which providers should be enabled on this host
2. preflight each selected provider
3. collect auth or local setup for each selected provider in order
4. choose one `runtime.default_provider`
5. run provider-specific finishing steps such as service, wrapper, or local binary checks when needed
6. persist machine-local config

Rules:

- the flow must not assume OpenClaw is always the first or only provider
- the chosen default provider must be explicit
- fallback is defined only to that one default provider
- fallback applies only before dispatch acceptance

## Configure semantics

`autoclaw configure` should expose the current machine-local runtime shape.

Minimum configurable concerns are:

- enabled provider set
- `runtime.default_provider`
- provider-local auth or environment requirements
- provider-local transport or connection settings
- provider-local permission or approval settings when they matter to launch compatibility
- provider-local support or compatibility requirements such as required execution mode, sandbox mode, or workspace or workdir rules when they are real constraints

Provider-local settings remain machine-local runtime concerns. They must not become reusable authored workflow truth.

## Doctor semantics

`autoclaw doctor` should report current provider readiness in controller-relevant terms.

Minimum output expectations are:

- enabled or configured providers
- configured default provider
- per-provider preflight status
- per-provider auth or connect status
- per-provider support-shape status for any required execution mode, sandbox mode, or workspace or workdir rule
- whether the provider can use the required shared node and operator MCP surfaces
- whether fallback to the default provider is available for a given requested provider

Rules:

- doctor should report launch incompatibility as a provider/runtime problem, not as a workflow-schema problem
- doctor should explain whether a failure blocks only one provider or blocks every configured provider
- doctor should name the failing support precondition directly when one provider requires an exact mode or workspace shape
- doctor output may include provider-local details, but those do not become controller truth

## Service asymmetry rule

Provider families need not expose identical setup verbs.

Rules:

- `openclaw` may own gateway, wrapper, or service setup
- `codex` may own app-server, SDK, or local CLI auth and config
- `claude` may own Agent SDK auth and config without requiring an AutoClaw-managed daemon
- the shared setup flow must allow this asymmetry without pretending every provider has the same lifecycle
- the support docs may therefore freeze different compatibility constraints for each provider family rather than forcing one fake universal rule

## Non-goals

This page does not define:

- authored node fields
- portable provider preference semantics
- provider-specific MCP tool vocabularies
- task-level fallback after dispatch acceptance

## Related contracts

- [Provider support and compatibility](provider-support-and-compatibility.md)
- [OpenClaw support and compatibility](openclaw-support-and-compatibility.md)
- [Codex support and compatibility](codex-support-and-compatibility.md)
- [Claude support and compatibility](claude-support-and-compatibility.md)
- [Workflow node schema](workflow-node-schema.md)
- [Provider preference and runtime config](provider-selection-and-runtime-config.md)
- [Node and operator MCP surface contract](node-and-operator-mcp-surface-contract.md)
