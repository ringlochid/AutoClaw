# Provider-aware setup, configure, and doctor

Status: Target

This page defines the V2 operator setup, configure, and doctor contract once `openclaw`, `codex`, and `claude` are first-class providers.

## Core rule

Operator setup becomes provider-first rather than OpenClaw-first.

The setup flow must help the operator choose providers, verify them, configure them, and pick one default provider before normal task execution relies on them.

The exact compatibility details for each provider family should live in provider support docs rather than being inferred from generic setup prose.

## Canonical command families

V2 should own these operator-facing command families:

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

## Canonical CLI envelopes

Shared provider-aware commands use these shapes:

```text
autoclaw onboard [--providers openclaw,codex,claude] [--default-provider <provider>] [--json] [--non-interactive] [--install-daemon]
autoclaw configure [--section all|runtime|providers|openclaw|codex|claude|service|definitions|web] [--default-provider <provider>] [--enable-provider <provider>] [--disable-provider <provider>] [--json] [--non-interactive]
autoclaw doctor [--provider all|openclaw|codex|claude] [--json] [--fix]
```

Provider-specific branches use:

```text
autoclaw openclaw check|setup|doctor [--json] [--fix]
autoclaw codex check|setup|doctor [--json] [--fix]
autoclaw claude check|setup|doctor [--json] [--fix]
```

Rules:

- `check` is read-only
- `setup` may write provider-local machine config and provider-owned support material for that provider branch
- `doctor` is read-only unless `--fix` is supplied
- `--fix` must repair only AutoClaw-owned local state and the named provider's AutoClaw-owned integration slice
- provider-specific branches must write only machine-local config or provider support material; they must not mutate reusable authored definitions

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

Canonical config readback should use:

```yaml
provider_runtime_config:
    runtime:
        enabled_providers:
            - openclaw | codex | claude
        default_provider: openclaw | codex | claude
    openclaw:
        enabled: boolean
        support_profile: string | null
    codex:
        enabled: boolean
        transport: stdio | unix_socket | http | null
    claude:
        enabled: boolean
        transport: stdio | http | null
```

Rules:

- `runtime.default_provider` must be one of `runtime.enabled_providers`
- provider-local sections may carry additional machine-local keys, but portable workflow schema must not read those keys directly
- support-profile details are owned by the provider support pages and verified by doctor

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

Canonical JSON output should use:

```yaml
provider_doctor_report:
    status: ok | warning | error
    default_provider: openclaw | codex | claude | null
    providers:
        - provider: openclaw | codex | claude
          enabled: boolean
          support_status: implemented | targeted | deferred | unsupported
          readiness: ready | needs_setup | blocked | deferred
          can_use_node_surface: boolean
          can_use_operator_surface: boolean
          fallback_to_default_available: boolean
          checks:
              - name: string
                status: ok | warning | error | skipped
                code: string
                message: string
                fix_available: boolean
```

Rules:

- top-level `status` is `error` when every enabled provider is blocked or the default provider is unusable
- top-level `status` is `warning` when at least one enabled non-default provider is blocked but the default provider can run
- `support_status` uses the shared provider support vocabulary
- `readiness` answers whether this host can launch that provider now
- `can_use_node_surface` and `can_use_operator_surface` report provider-neutral MCP surface compatibility, not adapter-local feature richness

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
