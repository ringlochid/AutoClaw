# Getting started

This guide is the fastest supported path to a first local AutoClaw install after OpenClaw is healthy.

If OpenClaw is not installed, configured, or reachable yet, start with [prepare OpenClaw first](prepare-openclaw.md).

## Recommended install path

Use the published package with `pipx`.

```bash
# Prepare OpenClaw before AutoClaw writes integration state.
openclaw status
openclaw gateway status

# Install the AutoClaw package.
pipx install autoclaw

# Guided first-run setup for AutoClaw.
autoclaw onboard

# Check local config, DB, packaged resources, service, and integration health.
autoclaw doctor

# Verify the OpenClaw side without writing.
autoclaw openclaw check
```

Then read the resolved config and open the local console:

```bash
autoclaw config path
autoclaw config show --json
```

Open `http://127.0.0.1:<server.port>/`. The default port is `18125`.

This guide is written for the shipped Linux path. The fully supported v1 managed-service path is Linux with `systemd --user`, which covers common systemd user-service distros such as Ubuntu, Debian, Fedora, and Arch when Python 3.12 and the normal user-service environment are available.

On macOS or Windows, use `autoclaw serve` as the foreground local-proof path. Native `launchd` and Windows Scheduled Task service parity are later work.

If you want the managed service installed during onboarding, use:

```bash
autoclaw onboard --install-daemon
autoclaw service status
```

If you skipped service install during onboarding, either run `autoclaw service install` before `autoclaw service start`, or use `autoclaw serve` as the foreground runner.

## Optional `uv` path

If you prefer `uv`, install the same package artifacts with:

```bash
# Install the same published AutoClaw package through uv.
uv tool install autoclaw

# Guided first-run setup for AutoClaw.
autoclaw onboard

# Check local AutoClaw state.
autoclaw doctor

# Verify the OpenClaw side without writing.
autoclaw openclaw check
```

If `autoclaw` is not on `PATH` yet after the `uv` install, run `uv tool update-shell` once and restart the shell.

Use the Postgres-enabled package when you need to run multiple tasks concurrently:

- `pipx install "autoclaw[postgres]"`
- `uv tool install "autoclaw[postgres]"`

Then set `AUTOCLAW_DATABASE_URL` to a real `postgresql+asyncpg://...` URL before onboarding.

## What onboarding asks

Interactive `autoclaw onboard` asks four things:

1. **Continue with guided onboarding?** Confirms before any local state is written.
2. **Install the managed service now?** Installs the Linux `systemd --user` service; answer no and use `autoclaw serve` or `autoclaw service install` later.
3. **AutoClaw service / MCP port** (default `18125`). AutoClaw serves its API and MCP surfaces on this loopback port.
4. **OpenClaw gateway port** (default `18789`, or the port already in your OpenClaw config). AutoClaw connects to the local Gateway here.

Compatibility checks run after the ports are chosen. Use `--port`, `--openclaw-gateway-port`, `--install-daemon`/`--skip-daemon`, and `--non-interactive` to answer these up front in scripts.

## What each command does

- `openclaw status` checks OpenClaw before AutoClaw depends on it
- `openclaw gateway status` checks Gateway service state and reachability
- `autoclaw onboard` is the guided first-run path
- `autoclaw doctor` checks local AutoClaw state plus the AutoClaw-owned OpenClaw integration slice
- `autoclaw openclaw check` verifies the OpenClaw side without writing
- `autoclaw config path` prints the local `config.toml` path
- `autoclaw config show --json` prints redacted effective settings, including `server.port` and `paths.data_dir`
- `autoclaw service install` writes the Linux managed-service entry when it was not installed during onboarding
- `autoclaw service start` starts the managed Linux user service after that service exists
- `autoclaw serve` is the foreground fallback for host proof and debugging

## Next steps

After the install path is healthy:

1. Check [configuration and settings](configuration-and-settings.md).
2. Run [start a task](start-a-task.md).
3. Read the generated runtime-output map in [inspect a task](inspect-a-task.md).
4. Install the operator skills in [set up OpenClaw agents and operator skills](../guides/set-up-openclaw-agents-and-skills.md).
5. Use [install and start locally](../reference/cli/install-and-start-local.md) for the exact support boundary and the contributor/dev repo-checkout path.
