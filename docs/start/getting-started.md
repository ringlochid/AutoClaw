# Getting started

This guide is the fastest supported path to a first local AutoClaw install.

## Recommended v1 lane

Use the published package with `pipx`.

```bash
pipx install autoclaw
autoclaw onboard
autoclaw doctor
autoclaw openclaw check
```

This guide is written for the shipped Linux lane. The fully supported v1 managed-service path is Linux with `systemd --user`, which covers common systemd user-service distros such as Ubuntu, Debian, Fedora, and Arch when Python 3.12 and the normal user-service environment are available.

On macOS or Windows, use `autoclaw serve` as the foreground local-proof path. Native `launchd` and Windows Scheduled Task service parity are later work.

If you want the managed service installed during onboarding, use:

```bash
autoclaw onboard --install-daemon
autoclaw service status
```

If you skipped service install during onboarding, either run `autoclaw service install` before `autoclaw service start`, or use `autoclaw serve` as the foreground runner.

## Optional `uv` lane

If you prefer `uv`, install the same package artifacts with:

```bash
uv tool install autoclaw
autoclaw onboard
autoclaw doctor
autoclaw openclaw check
```

If `autoclaw` is not on `PATH` yet after the `uv` install, run `uv tool update-shell` once and restart the shell.

Use the Postgres-enabled package when you need to run multiple tasks concurrently:

- `pipx install "autoclaw[postgres]"`
- `uv tool install "autoclaw[postgres]"`

Then set `AUTOCLAW_DATABASE_URL` to a real `postgresql+asyncpg://...` URL before onboarding.

## What each command does

- `autoclaw onboard` is the guided first-run path
- `autoclaw doctor` checks local AutoClaw state plus the AutoClaw-owned OpenClaw integration slice
- `autoclaw openclaw check` verifies the OpenClaw side without writing
- `autoclaw service install` writes the Linux managed-service entry when it was not installed during onboarding
- `autoclaw service start` starts the managed Linux user service after that service exists
- `autoclaw serve` is the foreground fallback for host proof and debugging

## Next steps

After the install path is healthy:

1. Run [start a task](start-a-task.md).
2. Learn where runtime outputs land in [inspect a task](inspect-a-task.md).
3. Use [install and start locally](../reference/cli/install-and-start-local.md) for the exact support boundary and the contributor/dev repo-checkout lane.
