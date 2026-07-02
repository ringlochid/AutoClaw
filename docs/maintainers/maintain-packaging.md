# Maintain packaging

Use this guide when changing the package surface, install story, bundled resources, dependencies, entrypoint, or version.

The root Python package is the release artifact. `pipx` is the primary public install lane. `uv` is the supported secondary tool-install lane over the same published artifacts.

## Package truth

The package surface is owned by `pyproject.toml`.

Current package facts:

- package source root: `apps/api/src`
- console script: `autoclaw = autoclaw.interfaces.cli.main:main`
- Python requirement: `>=3.12`
- default DB driver: `aiosqlite`
- Postgres extra: `autoclaw[postgres]` with `asyncpg`

Current package data includes:

- `definitions/seeds/policies/*.yaml`
- `definitions/seeds/roles/*.yaml`
- `definitions/seeds/workflows/*.yaml`
- `interfaces/web_console/assets/*`
- `interfaces/web_console/assets/assets/*`
- `platform/managed_services/resources/systemd/*.service`
- `runtime/prompt/assets/*.json`
- `runtime/prompt/assets/blocks/*.md`

If a new runtime resource must ship inside the package, add it to package data and prove it from an installed package path.

## When changing the console UI

The publishable package serves the built console UI from packaged resources under `autoclaw.interfaces.web_console`.

Use:

```bash
make console-package-assets
```

This runs the Vite production build and syncs `apps/console/dist` into `apps/api/src/autoclaw/interfaces/web_console/assets`. Build package artifacts after this step:

```bash
make package-build
```

The production console uses same-origin API requests by default, so packaged UI routes keep working when the API service runs on a configured port instead of the development default.

## When changing bundled definitions

Check:

- seed YAML validates
- reference examples still match the seed truth
- registry seeding can import the packaged mirror
- task-compose examples point at real workflow keys

Useful checks:

```bash
./.venv/bin/pytest apps/api/tests/unit/definition_schemas
./.venv/bin/python -m scripts.docs.docs_freeze.cli validate
```

## When changing service resources

The shipped managed-service lane is Linux with `systemd --user`.

Check:

- `autoclaw service render` still renders the packaged template
- `autoclaw service install` still writes the env file and user unit on a supported Linux host
- docs do not imply macOS or Windows managed-service parity
- docs describe distro support as capability-based systemd user-service support rather than a separate packaged binary per distro

## When changing dependencies or extras

Keep the public story simple:

- default package should support the SQLite local-first lane
- `autoclaw[postgres]` should add only the Postgres driver lane
- dev dependencies belong under the `dev` extra

After dependency changes, verify the package still installs in a clean environment.

## Maintainer checklist

- package metadata changed intentionally
- version changed only when a release or package smoke requires it
- package data includes every shipped resource needed at runtime
- public install docs still say `pipx` primary and `uv` secondary
- repo checkout remains documented as contributor/dev, not public onboarding
- Postgres docs still require both the extra and `AUTOCLAW_DATABASE_URL`
- package smoke proves the installed `autoclaw` command can run

## Checks

For packaging changes, use at least:

```bash
make check-api
make check-console
./.venv/bin/python -m scripts.docs.docs_freeze.cli validate
make package-build
git diff --check
```

Add package build and install smoke before release. Add DB and e2e lanes when the packaged resource can affect runtime, definitions, prompt rendering, service startup, or migrations.

## Related pages

- [Release and install strategy](../reference/maintainers/release-and-install-strategy.md)
- [Distribution and database support matrix](../reference/maintainers/distribution-and-database-support-matrix.md)
- [Install and start AutoClaw locally](../reference/cli/install-and-start-local.md)
- [Prepare a release](prepare-a-release.md)
