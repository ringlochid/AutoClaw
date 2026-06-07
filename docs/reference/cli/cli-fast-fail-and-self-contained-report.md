# CLI fast-fail and self-contained setup report

Status: Reference

Last verified: 2026-05-28

This report records the current shipped CLI commands, the current OpenClaw support-check decisions, and the current self-contained onboarding or service stance in this workspace.

## Summary decisions

- OpenClaw support preflight is now the **first gate** for commands that start runtime work or mutate OpenClaw-managed or service-managed state.
- `autoclaw onboard` now fail-fast checks OpenClaw support **before** writing local config, touching the DB, or installing the managed service.
- `autoclaw configure` now fail-fast checks OpenClaw support before any `openclaw` or `service` reconciliation.
- `autoclaw doctor --fix` now fail-fast checks OpenClaw support before local or wrapper repair.
- `autoclaw openclaw setup` and `autoclaw openclaw doctor --fix` now fail-fast check before wrapper writes.
- `autoclaw service install`, `autoclaw service start`, and `autoclaw service restart` now fail-fast check before managed-service mutation or startup.
- the packaged Linux `systemd --user` unit now runs `autoclaw openclaw check` as an `ExecStartPre`, so service startup keeps the same support gate.
- read-only or teardown commands remain usable for diagnosis or cleanup when OpenClaw support is blocked.
- `autoclaw openclaw check` is still a direct config/material/compatibility probe only; it does not prove session-effective worker-session bundle-MCP tool mounting on its own.

## Current shipped CLI commands

Current parser, exported through `apps/api/src/autoclaw/interfaces/cli/main.py` and backed by `apps/api/src/autoclaw/interfaces/cli/**`, exposes:

- `autoclaw init`
- `autoclaw serve`
- `autoclaw onboard`
- `autoclaw configure`
- `autoclaw doctor`
- `autoclaw config path`
- `autoclaw config show`
- `autoclaw db upgrade`
- `autoclaw db reset`
- `autoclaw definitions import --file <definition_path> [--overwrite reject|allow_new_revision]`
- `autoclaw definitions import [--overwrite reject|allow_new_revision]`
- `autoclaw task-compose start --file <task_compose_path>`
- `autoclaw openclaw check`
- `autoclaw openclaw setup`
- `autoclaw openclaw doctor`
- `autoclaw service render`
- `autoclaw service install`
- `autoclaw service uninstall`
- `autoclaw service start`
- `autoclaw service stop`
- `autoclaw service restart`
- `autoclaw service status`

## Current support-check policy

### Commands that now fail-fast check OpenClaw support first

| Command | Current behavior |
| --- | --- |
| `autoclaw serve` | checks support before API startup |
| `autoclaw onboard` | checks support before local config write, DB work, or service install |
| `autoclaw configure --section all` | checks support before runtime/openclaw/service reconciliation |
| `autoclaw configure --section openclaw` | checks support before wrapper reconciliation |
| `autoclaw configure --section service` | checks support before service reconciliation |
| `autoclaw doctor --fix` | checks support before local and wrapper repair |
| `autoclaw openclaw setup` | checks support before wrapper writes |
| `autoclaw openclaw doctor --fix` | checks support before wrapper repair |
| `autoclaw service install` | checks support before writing env file or unit |
| `autoclaw service start` | checks support before starting the managed service |
| `autoclaw service restart` | checks support before restarting the managed service |
| `systemd` unit `ExecStartPre` | runs `autoclaw openclaw check` before DB upgrade and `serve` |

### Commands intentionally not gated by the OpenClaw support preflight

These remain usable because they are read-only, teardown-oriented, or AutoClaw-local primitives.

| Command | Reason |
| --- | --- |
| `autoclaw init` | local config/bootstrap primitive |
| `autoclaw config path` | read-only local path readback |
| `autoclaw config show` | read-only config readback |
| `autoclaw doctor` | read-only health reporting; still reports OpenClaw integration first |
| `autoclaw db upgrade` | local DB primitive |
| `autoclaw db reset` | local DB primitive |
| `autoclaw definitions import ...` | local definition import surface |
| `autoclaw task-compose start --file ...` | local task-start wrapper; no new preflight gate yet |
| `autoclaw openclaw check` | the canonical read-only support/compatibility probe |
| `autoclaw openclaw doctor` | inspection is allowed; only `--fix` is gated |
| `autoclaw service render` | local template render only |
| `autoclaw service stop` | teardown path should stay available |
| `autoclaw service status` | read-only managed-service readback |
| `autoclaw service uninstall` | teardown path should stay available |

## Current support classification rules

Current support preflight classifies:

- OpenClaw binary resolution from explicit config/env override or `PATH`
- OpenClaw config path resolution
- loopback vs non-loopback Gateway base URL
- token auth
- password auth
- explicit no-auth loopback mode
- ambiguous auth state
- unresolved secret-reference state
- missing required auth material
- blocked trusted-proxy mode

Current supported shapes:

- loopback Gateway with token auth
- loopback Gateway with password auth
- explicit loopback no-auth Gateway

Current blocked shapes:

- missing OpenClaw binary
- non-loopback Gateway
- trusted-proxy auth
- ambiguous auth mode
- unresolved token/password references without resolved values
- no supported auth material

## Current self-contained onboarding and service stance

### What is self-contained now

- `onboard` preflights first, then writes local AutoClaw config, DB state, wrapper material, and optional service metadata.
- `openclaw setup` persists the selected worker/operator ids and persists discovered `binary_path` and `config_path` back into local AutoClaw config.
- when `gateway_token` or `gateway_password` are supplied through AutoClaw config/env, onboard/setup may persist those into local AutoClaw config too.
- the Linux `systemd --user` service reads `AUTOCLAW_CONFIG`, `AUTOCLAW_DATA_DIR`, and optional env-file overrides and now checks OpenClaw support before startup.

### What is still not fully universal

- cross-platform managed-service support is still incomplete: macOS `launchd` and Windows Scheduled Task managers are present as stubs, not full implementations.
- if Gateway auth material lives only in the OpenClaw config family rather than in AutoClaw config, runtime can still depend on the persisted OpenClaw config path rather than being fully independent from OpenClaw-side config.
- `task-compose start` remains outside the new fail-fast coverage because it is still treated as the local backend task-start wrapper rather than an onboarding/service-control surface.

## Current command-role decisions

- `init` stays a low-level local bootstrap primitive.
- `serve` stays a low-level foreground runner, but now fails fast on unsupported OpenClaw host shape.
- `onboard` is the primary first-run command.
- `configure` is the targeted re-entry command.
- `doctor` is the top-level health/readback command; `doctor --fix` is the repair command.
- `openclaw check` is the canonical read-only support/compatibility check.
- `openclaw setup` writes only the AutoClaw-owned OpenClaw integration slice.
- `openclaw doctor --fix` repairs only the AutoClaw-owned OpenClaw integration slice.
- `service ...` is the managed lifecycle surface; install/start/restart now share the same fail-fast support gate.

## Current implementation pointers

Primary touched surfaces for this decision set:

- `apps/api/src/autoclaw/interfaces/cli/__init__.py`
- `apps/api/src/autoclaw/interfaces/cli/commands/openclaw/support.py`
- `apps/api/src/autoclaw/interfaces/cli/commands/bootstrap.py`
- `apps/api/src/autoclaw/interfaces/cli/commands/onboard.py`
- `apps/api/src/autoclaw/interfaces/cli/commands/configure.py`
- `apps/api/src/autoclaw/interfaces/cli/commands/doctor.py`
- `apps/api/src/autoclaw/interfaces/cli/commands/openclaw/wrapper.py`
- `apps/api/src/autoclaw/interfaces/cli/commands/service.py`
- `apps/api/src/autoclaw/platform/managed_services/resources/systemd/autoclaw.service`
- `apps/api/tests/unit/cli/**`
- `apps/api/tests/integration/public_surfaces/test_root_cli_commands.py`

## Verification run used for this report

- `./.venv/bin/ruff check apps/api/src/autoclaw/interfaces/cli/commands/bootstrap.py apps/api/src/autoclaw/interfaces/cli/commands/openclaw/support.py apps/api/src/autoclaw/interfaces/cli/commands/openclaw/wrapper.py apps/api/src/autoclaw/interfaces/cli/commands/onboard.py apps/api/src/autoclaw/interfaces/cli/commands/configure.py apps/api/src/autoclaw/interfaces/cli/commands/doctor.py apps/api/src/autoclaw/interfaces/cli/commands/service.py apps/api/tests/unit/cli apps/api/tests/integration/public_surfaces/test_root_cli_commands.py`
- `./.venv/bin/pytest -q apps/api/tests/integration/public_surfaces/test_root_cli_commands.py`
- `./.venv/bin/pytest -q apps/api/tests/unit/cli apps/api/tests/unit/test_package_entrypoints.py`

## Related pages

- `cli-surface-and-config-precedence.md`
- `packaging-cli-and-install.md`
- `install-and-start-local.md`
- `verify-current-install-and-runtime.md`
