# Release and install strategy

This page defines the supported v1 install and release posture.

## Primary v1 path

The primary v1 install path is:

1. publish root package artifacts to PyPI
2. install with `pipx`

The root package remains the primary release artifact.

## Secondary v1 tool-install path

`uv` is a supported secondary install lane for the same published package artifacts.

- default package: `uv tool install autoclaw`
- Postgres package: `uv tool install "autoclaw[postgres]"`

This does not replace the primary `pipx` story. It is an alternate tool-install path over the same PyPI package release.

## Supported local install stories

### Default local lane: `pipx`

```bash
pipx install autoclaw
autoclaw onboard --install-daemon
autoclaw doctor
autoclaw openclaw check
autoclaw service status
```

### Supported Postgres lane: `pipx`

```bash
pipx install "autoclaw[postgres]"
export AUTOCLAW_DATABASE_URL=postgresql+asyncpg://autoclaw:autoclaw@127.0.0.1:5432/autoclaw
autoclaw onboard --install-daemon
autoclaw doctor
autoclaw openclaw check
autoclaw service status
```

### Default local lane: `uv`

```bash
uv tool install autoclaw
autoclaw onboard --install-daemon
autoclaw doctor
autoclaw openclaw check
autoclaw service status
```

### Supported Postgres lane: `uv`

```bash
uv tool install "autoclaw[postgres]"
export AUTOCLAW_DATABASE_URL=postgresql+asyncpg://autoclaw:autoclaw@127.0.0.1:5432/autoclaw
autoclaw onboard --install-daemon
autoclaw doctor
autoclaw openclaw check
autoclaw service status
```

Installing `autoclaw[postgres]` only adds the async Postgres driver. Set `AUTOCLAW_DATABASE_URL` to a Postgres URL before onboarding if you actually want the runtime on Postgres instead of the default SQLite lane.

Use the Postgres extra together with [Use Postgres](use-postgres.md).

## Release architecture

```mermaid
flowchart TD
    A["Git tag or release commit"] --> B["build root package artifacts"]
    B --> C["publish PyPI wheel and sdist"]
    C --> D["pipx primary install path"]
    C --> E["uv secondary install path"]
    B --> F["package bundled console, migrations, and service resources"]
```

Figure: v1 release truth is the packaged root Python distribution plus bundled runtime resources needed by the supported install path.

## Support matrix boundary

Shipped v1 support includes:

- PyPI wheel and sdist
- `pipx install autoclaw`
- `pipx install "autoclaw[postgres]"`
- `uv tool install autoclaw`
- `uv tool install "autoclaw[postgres]"`
- SQLite local-first smoke lane
- Postgres plus Docker strong verification lane
- guided first-run through `autoclaw onboard`
- Linux `systemd --user` managed service lifecycle through `autoclaw service install|start|stop|restart|status`

Managed-service support boundary for v1:

- Linux: `systemd --user` by default
- macOS: not yet a shipped v1 parity lane
- Windows: not yet a shipped v1 parity lane

Windows and macOS service-manager support belong to later follow-on work and should not be taught as shipped v1 behavior.

See [Distribution and database support matrix](distribution-and-database-support-matrix.md) for the supported matrix.

## Not currently supported

These are not part of the supported v1 install story:

- standalone binaries
- npm shim package
- Homebrew or other convenience installer
- repo-native editable install as the primary public onboarding story

They must not be taught as supported v1 install paths until they gain explicit support and tests.

## Release rule

Publish only from the root packaging surface.

Convenience channels, if added later, must wrap the primary release artifacts rather than becoming the source of truth.

## Related contracts

- [Distribution and database support matrix](distribution-and-database-support-matrix.md)
- [Testing and release checklist](testing-and-release-checklist.md)
