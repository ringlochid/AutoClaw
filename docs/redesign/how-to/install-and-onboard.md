# Install and onboard the redesign target

Status: Target

This page defines the frozen v1 install and onboard path.

Use `bootstrap` only for internal runtime or materialization contracts. The operator-facing lifecycle uses `init`, `check`, `setup`, `onboard`, `configure`, and `doctor`.

The commands, flags, and rich terminal behavior below describe the redesign target. The current shipped CLI in this repo is narrower and does not yet expose the full `autoclaw openclaw ...` family or every target interaction flag.

## Minimal path

1. Install the product: `pipx install autoclaw`
2. Initialize AutoClaw-local config and directories: `autoclaw init`
3. Run the guided OpenClaw first-run flow: `autoclaw openclaw onboard`
4. Verify the OpenClaw side without writing: `autoclaw openclaw check`
5. Repair local AutoClaw state only when needed: `autoclaw doctor`
6. Start the local runtime when needed: `autoclaw serve`

Minimal example:

```text
pipx install autoclaw
autoclaw init
autoclaw openclaw onboard
autoclaw openclaw check
autoclaw doctor
autoclaw serve
```

## Subset re-entry path

Use this path after first-run when only part of the OpenClaw setup needs to change.

- `autoclaw openclaw configure` revisits one existing setup slice without rerunning the full guided first-run flow
- `autoclaw openclaw check` stays the read-only verification step before or after a targeted change
- `autoclaw openclaw doctor` is the repair path when previously written OpenClaw state needs remediation

Subset example:

```text
autoclaw openclaw configure
autoclaw openclaw check --json
autoclaw openclaw doctor
```

## Direct setup path

Use this path when automation or a low-level operator flow needs baseline writes without the guided first-run wrapper.

- `autoclaw openclaw setup` writes only baseline OpenClaw config, workspace material, and the two canonical MCP tool-surface definitions
- `autoclaw openclaw check` remains the read-only follow-up verification

Direct setup example:

```text
autoclaw init
autoclaw openclaw setup --non-interactive
autoclaw openclaw check --json
```

## Command-role guardrails

- `autoclaw init` stays AutoClaw-local and is not the OpenClaw setup noun
- `autoclaw openclaw check` is read-only
- `autoclaw openclaw setup` writes baseline OpenClaw wrapper state only
- `autoclaw openclaw onboard` is the guided first-run entrypoint
- `autoclaw openclaw configure` is subset re-entry only
- `autoclaw openclaw doctor` is repair and remediation only

## CLI interaction and output rules

- `--json` is output-shape only
- `--non-interactive` controls automation and disables guided prompts
- `--plain`, `--no-color`, and `NO_COLOR` disable rich styling
- rich styling is TTY-only
- when styling is present, onboarding, setup, configure, and doctor should mirror OpenClaw's lobster palette and warning-first tone rather than inventing a separate AutoClaw visual language
- rich onboarding and doctor flows should keep OpenClaw's structured terminal-native layout: prominent command header, accent section headings, framed warning/status panels, and dense aligned diagnostics when reporting state

## Canonical local config shape

The canonical target config is controller/runtime-focused. It does not include a configured `definitions_root`, and it does not require a user-facing `[app].env` field.

```toml
[paths]
data_dir = "~/.local/share/autoclaw"

[database]
url = "sqlite+aiosqlite:///~/.local/share/autoclaw/autoclaw.db"

[server]
host = "127.0.0.1"
port = 8123
console_origins = ["http://127.0.0.1:5173"]

[logging]
level = "INFO"

[security]
api_key = "replace-me"
internal_api_key = "replace-me"

[openclaw]
base_url = "http://127.0.0.1:18789"
gateway_token = "replace-me"
agent_id = "autoclaw-worker"
timeout_ms = 120000

[runtime]
dispatch_drain_timeout_seconds = 30
watchdog_enabled = true
watchdog_interval_seconds = 15
watchdog_execution_stale_after_seconds = 300
watchdog_bootstrap_first_progress_timeout_seconds = 120
watchdog_auto_recover = true
watchdog_max_flows_per_tick = 50
watchdog_max_auto_recoveries_per_tick = 10
```

Rules:

- app/API auth uses API keys
- OpenClaw gateway auth stays in the OpenClaw config family
- the runtime-owned OpenClaw adapter connects to the local trusted-loopback Gateway backend path with `client.id="gateway-client"` and `client.mode="backend"`; it does not use the older CLI/device-auth shape for Phase 4A
- the configured `[openclaw].gateway_token` is the primary shared-token input for that backend path
- older configs may still carry `runtime.watchdog_bootstrap_ack_timeout_seconds`; treat it as a temporary compatibility alias for the canonical target knob `runtime.watchdog_bootstrap_first_progress_timeout_seconds`
- if a trusted-loopback connect fails with `AUTH_TOKEN_MISMATCH`, the adapter retries once with a locally resolved Gateway token in this order: `OPENCLAW_GATEWAY_TOKEN`, then `OPENCLAW_CONFIG_PATH`, then `~/.openclaw/openclaw.json` at `gateway.auth.token`
- non-loopback Gateway connects require full signed device identity and are not a shipped AutoClaw Phase 4A path
- older local configs may still carry `openclaw.internal_api_key` and `openclaw.account`; the current runtime drops those legacy TOML keys during config load and does not use them in live Gateway requests
- local definition import reads explicit files or a shallow current-working-directory scan
- runtime does not depend on a configured definitions root after import
- actual OpenClaw dispatch, wait, abort, and callback authority validation stays in the runtime-owned adapter path; this config only supplies its tunable inputs
- OpenClaw setup writes local wrapper config, workspace material, and the two canonical MCP tool-surface definitions only; it does not reassign controller-owned runtime truth

## Minimum checks

- config created
- database path exists
- API keys configured
- canonical runtime watchdog config is present when watchdog automation is enabled
- chosen provider reachable if configured
- OpenClaw wrapper check passes without requiring writes
