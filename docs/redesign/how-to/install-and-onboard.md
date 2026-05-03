# Install and onboard the redesign target

Status: Target

This page defines the frozen v1 install and onboard path.

## Recommended path

1. Install the product: `pipx install autoclaw`
2. Onboard the environment: `autoclaw init`
3. Check the environment: `autoclaw doctor`
4. Start the local runtime when needed: `autoclaw serve`

## Canonical local config shape

The canonical target config is controller/runtime-focused. It does not include a configured `definitions_root`, and it does not require a user-facing `[app].env` field.

```toml
[paths]
data_dir = "C:/Users/example/AppData/Local/autoclaw"

[database]
url = "sqlite+aiosqlite:///C:/Users/example/AppData/Local/autoclaw/autoclaw.db"

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
internal_api_key = "replace-me"
agent_id = "autoclaw-worker"
timeout_ms = 120000
account = "orin_a"

[runtime]
dispatch_drain_timeout_seconds = 30
watchdog_enabled = true
watchdog_interval_seconds = 15
watchdog_stale_after_seconds = 300
watchdog_execution_stale_after_seconds = 300
watchdog_bootstrap_ack_timeout_seconds = 120
watchdog_execution_hint_extension_seconds = 300
watchdog_bootstrap_hint_extension_seconds = 120
watchdog_auto_recover = true
watchdog_max_flows_per_tick = 50
watchdog_max_auto_recoveries_per_tick = 10
watchdog_bootstrap_max_auto_retries = 2
watchdog_max_auto_wakes = 1
```

Rules:

- app/API auth uses API keys
- OpenClaw gateway auth stays in the OpenClaw config family
- local definition import reads explicit files or a shallow current-working-directory scan
- runtime does not depend on a configured definitions root after import

## Minimum checks

- config created
- database path exists
- API keys configured
- canonical runtime watchdog config is present when watchdog automation is enabled
- chosen provider reachable if configured
