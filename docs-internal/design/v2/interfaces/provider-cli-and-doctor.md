# Provider CLI and doctor

Status: Target

This page defines the local-first provider onboarding, authentication handoff, setup, readiness, and diagnostics experience.

## Core rule

AutoClaw CLI is the onboarding and support surface. Provider authentication and native configuration remain provider-owned.

The CLI must make a broken provider easy to understand without making that provider a prerequisite for AutoClaw startup.

## Canonical commands

The complete provider-facing command surface is:

```text
autoclaw onboard
autoclaw doctor [--provider <provider>]
autoclaw provider status [provider]
autoclaw provider doctor [provider]
autoclaw codex login
autoclaw claude setup
autoclaw openclaw setup
```

No parallel `configure`, provider `check`, provider `login` nesting, or provider-specific doctor verb is part of this target.

## Command ownership

| Command | Purpose | Mutation |
| --- | --- | --- |
| `autoclaw onboard` | Guide initial provider selection, setup, default choice, and final readiness | Writes AutoClaw machine-local config after confirmation |
| `autoclaw doctor` | Run broad or selected provider diagnostics plus shared runtime checks | Read-only |
| `autoclaw provider status` | Show cheap current configuration and readiness readback | Read-only |
| `autoclaw provider doctor` | Run deeper provider conformance for one or all providers | Read-only |
| `autoclaw codex login` | Delegate to the official Codex authentication protocol | Provider stores credentials |
| `autoclaw claude setup` | Guide and validate supported API or cloud credentials and local SDK config | Writes only confirmed AutoClaw machine-local choices |
| `autoclaw openclaw setup` | Configure and verify AutoClaw's narrow external Gateway integration | Writes only the confirmed AutoClaw integration slice |

Provider setup commands must not mutate reusable workflow, role, or policy definitions. Doctor commands must not offer hidden `--fix` behavior.

## Onboard flow

`autoclaw onboard` performs this guided sequence:

1. Detect which optional managed provider extras and external integrations are available.
2. Let the operator choose one or more providers to enable.
3. Route missing provider prerequisites to the exact command or package extra that owns them.
4. Run provider setup or authentication handoff only after operator confirmation.
5. Choose one enabled ready provider as `runtime.default_provider`.
6. Persist sparse machine-local AutoClaw config.
7. Run the same provider status and doctor checks used after onboarding.
8. Explain any remaining provider-specific warning without blocking unrelated providers.

Examples of prerequisite guidance are:

```text
Install Codex support:  pip install "autoclaw[codex]"
Install Claude support: pip install "autoclaw[claude]"
Install both:            pip install "autoclaw[managed]"

Authenticate Codex:     autoclaw codex login
Configure Claude:       autoclaw claude setup
Connect OpenClaw:       autoclaw openclaw setup
```

OpenClaw installation and supervision remain outside the onboard flow.

## Status semantics

`autoclaw provider status` is a fast readback. With no provider argument it reports every known provider; with one argument it reports only that provider.

Minimum fields are:

```yaml
provider_status:
    provider: openclaw | codex | claude
    enabled: boolean
    is_default: boolean
    support: supported | experimental | unsupported
    readiness: ready | needs_setup | blocked | not_installed
    auth:
        state: ready | missing | invalid | external | unknown
        type: string | null
    sdk_version: string | null
    runtime_version: string | null
    session_environment: string
    node_mcp: ready | blocked | unchecked
    active_controls:
        - dispatch_id: string
          operation: start | stop
          state: queued | attempting | retry_scheduled | succeeded | failed
          attempt: integer
          max_attempts: integer
          next_retry_at: string | null
          last_error_summary: string | null
    remediation: string | null
```

The readback never includes raw credentials, complete provider output, or provider events. Active control rows mirror bounded controller-owned retry state so an operator can see `attempt 3/6` rather than mistaking recovery for a hang.

`support` is a durable product compatibility label. Design maturity such as "targeted but not shipped" belongs only in internal target docs and never appears in CLI output. `readiness` remains the machine-specific setup result and is independent from support level.

## Doctor semantics

These two forms use the same check engine:

```text
autoclaw doctor [--provider <provider>]
autoclaw provider doctor [provider]
```

The top-level form may include shared AutoClaw runtime checks. The provider form is focused on provider compatibility. With no provider selector, each checks all enabled providers.

Per-provider doctor checks include:

- optional dependency or external-install presence
- SDK and bundled runtime version compatibility
- effective provider home, config sources, and service OS identity
- provider-owned auth presence and validity without secret content
- task-workspace and filesystem-namespace compatibility
- Node MCP reachability, initialize, and required tool discovery
- non-interactive provider approval and question behavior
- fresh start, continuity resume, replacement-hint fallback, and stop conformance
- provider-specific transport checks such as OpenClaw disconnect and fresh abort

Checks that would launch a billable provider turn are active probes. Doctor describes the probe and obtains interactive confirmation before running it; unattended broad doctor may report those checks as skipped. `autoclaw provider doctor [provider]` is the explicit focused path for full provider conformance.

One provider failure produces a provider-scoped warning or error. AutoClaw is globally blocked only when no enabled ready provider can satisfy the configured default and the operator attempts to start work that needs one.

## Provider-specific experience

### Codex login

`autoclaw codex login` starts the official Codex login protocol for supported ChatGPT or API authentication. Codex owns browser or device-code interaction, credential storage, and token refresh. AutoClaw reports success or actionable failure without reading the token.

### Claude setup

`autoclaw claude setup` explains and validates supported Anthropic API or cloud-provider authentication, confirms the SDK and bundled runtime, and checks native setting sources.

It does not present a Claude.ai subscription login screen or store OAuth credentials. An externally managed local Claude login may be reported only as external diagnostic state when the official SDK exposes it.

### OpenClaw setup

`autoclaw openclaw setup` owns only the AutoClaw integration boundary: Gateway endpoint and documented identity, independent handshake mode and delivery channel, stable Node MCP registration, task-workspace access, and launch/abort conformance.

It does not install, upgrade, or supervise OpenClaw; weaken its network or auth posture; rewrite unrelated agents; or create an operator-agent dependency.

## Service identity rule

CLI setup and the AutoClaw service must use compatible OS identity and environment.

Doctor compares relevant provider homes and namespace facts, including `HOME`, `CODEX_HOME`, `CLAUDE_CONFIG_DIR`, container or WSL boundaries, task paths, and Node MCP reachability. It must warn when interactive setup succeeded for one user but the service will run as another.

## Exit behavior

- Status exits successfully when readback is available, even if it reports a provider that needs setup.
- Provider doctor exits unsuccessfully when the selected provider is blocked or its conformance check fails.
- Broad doctor exits unsuccessfully when shared runtime checks fail or the configured default provider is blocked. A broken enabled non-default provider produces a warning while the default remains ready.
- Setup and login commands exit unsuccessfully when their delegated provider operation or final validation fails.

Messages must always name the next exact command or native provider action when remediation is known.

## Non-goals

This contract does not define:

- credentials stored by AutoClaw
- automatic installation of OpenClaw
- remote workspaces or provider-control services
- a generic provider context-window setting
- provider terminal events as health or completion truth
- Operator MCP as worker readiness

## Related contracts

- [Provider selection and runtime config](provider-selection-and-runtime-config.md)
- [Provider support and compatibility](provider-support-and-compatibility.md)
- [Codex support and compatibility](codex-support-and-compatibility.md)
- [Claude support and compatibility](claude-support-and-compatibility.md)
- [OpenClaw support and compatibility](openclaw-support-and-compatibility.md)
- [Runtime lifecycle and watchdog](../architecture/runtime-lifecycle-and-watchdog.md)
