# Install and start AutoClaw locally

This page defines the supported local install and start paths for the shipped AutoClaw package.

## Primary supported install lane: `pipx`

Use `pipx` as the default public install path for v1.

1. Install the default package: `pipx install autoclaw`
2. Run guided first-run setup: `autoclaw onboard`
3. Verify local state: `autoclaw doctor`
4. Verify the OpenClaw integration side without writing: `autoclaw openclaw check`
5. If you did not install the managed service during onboarding, install it now: `autoclaw service install`
6. Start the managed Linux user service: `autoclaw service start`
7. Optional foreground host-proof path: `autoclaw serve`

Postgres package lane for multiple concurrent task runs:

```bash
pipx install "autoclaw[postgres]"
export AUTOCLAW_DATABASE_URL=postgresql+asyncpg://autoclaw:autoclaw@127.0.0.1:5432/autoclaw
autoclaw onboard --install-daemon
autoclaw doctor
autoclaw openclaw check
autoclaw service status
```

## Secondary supported install lane: `uv`

Use `uv` when you want the same published package artifacts through uv's tool-install flow instead of `pipx`.

Default package lane:

```bash
uv tool install autoclaw
autoclaw onboard --install-daemon
autoclaw doctor
autoclaw openclaw check
autoclaw service status
```

Postgres package lane for multiple concurrent task runs:

```bash
uv tool install "autoclaw[postgres]"
export AUTOCLAW_DATABASE_URL=postgresql+asyncpg://autoclaw:autoclaw@127.0.0.1:5432/autoclaw
autoclaw onboard --install-daemon
autoclaw doctor
autoclaw openclaw check
autoclaw service status
```

Installing `autoclaw[postgres]` only adds the async Postgres driver. Without `AUTOCLAW_DATABASE_URL`, the shipped default lane remains SQLite.

If `uv` reports that the tool executable directory is not on `PATH`, run `uv tool update-shell` once and restart the shell.

## Contributor and dev lane: repo checkout

Use a repo checkout only when you are developing AutoClaw itself rather than following the supported package-install story.

1. Change into the repo root: `cd <autoclaw-repo>`
2. Create a virtual environment: `python -m venv .venv`
3. Install the repo package with dev dependencies: `<venv-python> -m pip install -e .[dev]`
4. Run first-run setup: `<venv-bin>/autoclaw onboard`
5. Verify local state: `<venv-bin>/autoclaw doctor`
6. Verify the OpenClaw integration side without writing: `<venv-bin>/autoclaw openclaw check`
7. If you did not install the managed service during onboarding, install it now: `<venv-bin>/autoclaw service install`
8. Start the managed Linux user service: `<venv-bin>/autoclaw service start`
9. Optional foreground host-proof path: `<venv-bin>/autoclaw serve`

Path notes:

- on POSIX, `<venv-python>` is `.venv/bin/python` and `<venv-bin>/autoclaw` is `.venv/bin/autoclaw`
- on Windows, `<venv-python>` is `.venv\\Scripts\\python` and `<venv-bin>/autoclaw` is `.venv\\Scripts\\autoclaw`

These path notes help contributor/dev checkout ergonomics only. They do not imply Windows managed-service parity for the shipped v1 support boundary.

## Support boundary

- the fully supported v1 managed-service path is Linux with `systemd --user`
- distro support is capability-based: Ubuntu, Debian, Fedora, Arch, and similar systemd user-service hosts are the intended lane when Python 3.12 and user services are available
- `autoclaw service install|start|stop|restart|status` should be taught as Linux-first v1 behavior
- macOS `launchd` and Windows Scheduled Task support are planned follow-on work, not shipped v1 parity
- `autoclaw serve` remains the foreground fallback for local host proof and debugging
- `autoclaw onboard` installs the managed service only when you opt into that path, for example with `--install-daemon` or the interactive install prompt

## Defaults and notes

- current config and data defaults come from `platformdirs`
- default local DB: SQLite in the AutoClaw data dir
- default API bind: `127.0.0.1:18125`
- `serve` exits with its parent shell or session
- the shipped onboarding and configuration flow reconciles both local AutoClaw state and the AutoClaw-owned OpenClaw integration slice
- when the local SQLite runtime comes from an older incompatible schema, `autoclaw onboard` backs that DB up and reconciles a fresh current-schema runtime DB instead of failing immediately
- the AutoClaw API port is stored in `server.port`
- the current shipped v1 loopback-only OpenClaw port is stored through `openclaw.base_url`
