# Install and onboard problems

Use this page when install, first-run setup, or the top-level health checks fail.

## Supported install lanes

The public v1 install story is:

- primary: `pipx install autoclaw`
- secondary: `uv tool install autoclaw`
- contributor/dev only: editable repo checkout

The fully supported managed-service lane is Linux with `systemd --user`. Ubuntu, Debian, Fedora, Arch, and similar systemd user-service hosts are the intended lane when Python 3.12 is available. Use `autoclaw serve` as the foreground fallback when service management is not available.

## `autoclaw` is not found

Check:

- confirm the package installed without error
- confirm the tool executable directory is on `PATH`
- for `uv`, run `uv tool update-shell` once and restart the shell when needed

Fix:

- reinstall with the supported tool lane
- restart the shell after PATH changes
- use the repo checkout lane only when developing AutoClaw itself

Reference: [Install and start AutoClaw locally](../reference/cli/install-and-start-local.md).

## `autoclaw onboard` fails before writing

Likely cause:

- OpenClaw support preflight blocked the host shape before local config, DB, wrapper, or service state was changed

Check:

```bash
autoclaw openclaw check --json
```

Fix:

- confirm the OpenClaw Gateway base URL is loopback
- confirm the OpenClaw binary and config path can be resolved
- use a supported auth shape: token auth, password auth, or explicit no-auth loopback
- avoid trusted-proxy, non-loopback, ambiguous auth, or unresolved secret-reference shapes for the v1 path

Continue with [OpenClaw integration problems](openclaw-integration.md) if the support check is blocked.

## `autoclaw doctor` is unhealthy after onboarding

Check:

```bash
autoclaw doctor --json
autoclaw openclaw check --json
autoclaw config path
```

Likely causes:

- local config or data dir is not writable
- packaged resources are missing from the installed package
- the database URL points at an unavailable database
- the OpenClaw integration slice is missing or drifted

Fix:

- run `autoclaw doctor --fix` when the support preflight is healthy
- run `autoclaw configure --section definitions` when packaged definitions need reseeding
- run `autoclaw configure --section openclaw` when only the OpenClaw integration slice drifted
- run `autoclaw db upgrade` when the configured database needs schema creation or upgrade

## Non-interactive setup stops or prompts

Use `--non-interactive` for guided commands in scripts or CI-like environments:

```bash
autoclaw onboard --non-interactive --json
autoclaw configure --section all --non-interactive --json
```

If a command needs a missing value in non-interactive mode, pass the value explicitly or run the command interactively once.

## Related pages

- [Getting started](../start/getting-started.md)
- [CLI surface and config precedence](../reference/cli/cli-surface-and-config-precedence.md)
- [CLI support checks and self-contained setup](../reference/cli/cli-fast-fail-and-self-contained-report.md)
