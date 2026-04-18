# 09 — Phase 9: Local-first Packaging and Distribution

## Goal

Make AutoClaw installable as a local-first product without Docker as the primary installation boundary.

Target shape:

- AutoClaw can be installed into a clean Python environment as a real package
- the built console is bundled and served by the package
- SQLite works as the default local database for single-user installs
- Postgres remains the recommended production database
- Docker remains an optional helper for dev, CI, and production convenience, not the core product boundary

## Why this phase exists

The current repo is still organized like a development workspace, not a distributable product.

Today the codebase still has several packaging/productization blockers:

- `apps/api/pyproject.toml` is app-local rather than product-level packaging
- runtime path resolution still depends on repo-relative locations
- the console build/runtime boundary is not packaged as a stable distributable artifact
- the database layer is Postgres-first today
- Docker is currently doing too much work as a dev/runtime glue layer

That is acceptable while the runtime model is still landing.
It is not the clean end state if AutoClaw is meant to be installed via PyPI, `pipx`, or a normal Python packaging flow.

## Product position this phase should enforce

AutoClaw should become:

- a Python package first
- a local-first tool second
- a production-deployable service third

Not the other way around.

That means:

- **package install** is the primary user path
- **SQLite local mode** is the default local persistence path
- **Postgres** is the stronger production/runtime path
- **Docker Compose** is a convenience path, not the definition of the product

## Logical packaging/runtime abstraction this phase should freeze

Phase 9 is the right place to freeze the packaging/runtime boundary before backend tables, mounts, service handles, and logs spread ad hoc through the runtime.

This matters for product quality too:

- it keeps AutoClaw powerful as the system grows
- it keeps the user-facing model easy to understand
- it prevents backend-specific mess from leaking into normal task/operator flows

This should be a logical abstraction, not a demand that Docker become the primary user-facing product boundary.

### Task image

Immutable reusable seed/template for task-environment defaults.

Typical examples:

- default task-resource layout
- allowed task-scoped services
- bootstrap/input schema hints
- stable content hash for reuse/export/import

### Task compose

Live task environment topology for one concrete task.

Typical responsibilities:

- own and wire task-scoped workspace/context/manifest roots
- own optional services such as repo checkouts, browsers, DB/cache helpers, or sandboxes
- expose typed slots that node runtime instances can consume

### Runtime image

Immutable node execution contract.

Typical responsibilities:

- carry effective role/mode/policy meaning
- carry required/allowed skill contract
- declare required resource slots and backend hint
- stay reusable and inspectable across retries/restarts

### Runtime container

Live node execution instance.

Typical responsibilities:

- bind one runtime image to one task/flow/node identity
- bind task-compose resources/services into runtime slots
- track backend handles, bootstrap state, mounts, typed events, and raw logs

### Why this belongs in Phase 9

Package/install work is where the user-facing runtime contract gets frozen.
If AutoClaw skips this layer now, backend-specific side effects tend to leak directly into core runtime tables and ad hoc controller code.

Important rule:

- first backend can still be OpenClaw sessions plus task-owned filesystem/object-storage roots
- the abstraction should be backend-agnostic even if Docker/OCI is added later

## Release shapes to support

### 1. Local package install

Target examples:

- `pipx install autoclaw`
- `pip install autoclaw`
- internal wheel install for controlled environments

Expected properties:

- no repo checkout required
- no `PYTHONPATH=.` tricks
- no mandatory Docker dependency
- no hardcoded repo-relative asset paths

### 2. Local developer repo install

The repo should still support fast iteration for contributors.

Expected properties:

- editable install works cleanly
- local console build/dev server still works
- Postgres and Docker remain available for realistic integration testing

### 3. Production deployment

Expected properties:

- Postgres remains supported and recommended
- OpenClaw remains an external dependency/integration
- Docker/Kubernetes/systemd deployment shapes remain possible
- package structure is the same as the local install shape

## Non-goals

This phase should **not**:

- bundle OpenClaw itself into AutoClaw
- make Docker the required end-user install path
- pretend SQLite and Postgres have identical concurrency semantics
- remove Postgres support
- turn packaging work into a rewrite of the runtime model
- absorb watchdog-autonomy/recovery design as a packaging exit gate
- absorb n8n-style graph authoring/editor work as a packaging exit gate
- turn skill-reference UX questions into a raw skill-package hosting rewrite

## Current blockers to clear

### 1. Backend package layout is not distribution-ready

Current issues include:

- app-local packaging under `apps/api`
- flat-layout install assumptions
- runtime imports and data loading that still assume repo structure

The package should move toward a real distributable Python layout, such as:

- `src/autoclaw/...`

The exact final tree can vary, but the important part is that imports, entrypoints, and data files all work from an installed package.

### 2. Runtime still depends on repo-relative data paths

Current examples:

- config/env loading anchored to repo-relative paths
- definition registry/bootstrap loading from repository directories

Those paths need to move behind package-safe resource loading.

Preferred direction:

- use `importlib.resources` for packaged definitions, migrations, and built assets where appropriate
- allow explicit override paths only as an advanced/operator setting

### 3. Console delivery is not packaged cleanly yet

The built frontend should be a packaged runtime asset, not something that only works from the repo.

Required end state:

- console build artifacts are bundled into the installable package
- backend serves packaged console assets from a stable internal path
- the console no longer depends on build-time injection of sensitive or operator-only API configuration that should instead come from runtime config/session state

### 4. Database layer is Postgres-first today

Current portability blockers include:

- direct use of Postgres `JSONB` in ORM models
- Postgres driver assumption (`asyncpg`) as the only runtime path
- Postgres-specific integration-test reset flow
- runtime locking assumptions built around `SELECT ... FOR UPDATE`

This does **not** mean the whole model is incompatible with SQLite.
It means the persistence layer needs an intentional portability pass.

## Clean database support contract

The clean support contract is:

### SQLite

Use SQLite for:

- local installs
- single-user usage
- lightweight development
- smoke tests focused on packaging/local behavior

SQLite support does **not** need to promise full production-equivalent concurrency behavior.
It needs to be correct and usable for the local/single-user path.

### Postgres

Use Postgres for:

- production deployments
- concurrent runtime execution
- stronger locking semantics
- full integration/performance verification

Postgres remains the truth path for the heavy-duty runtime profile.

## ORM / persistence compatibility plan

Keep **one ORM model layer**, with a small dialect-compatibility layer rather than separate model trees.

### 1. Add portable database types

Create a shared module such as:

- `app/db/types.py`

Use it to define portable types such as:

- `PortableJSON = JSON().with_variant(JSONB, "postgresql")`

Then replace direct `JSONB` usage in ORM models with that portable type.

Principle:

- one logical model
- dialect-specific storage optimization only where useful

### 2. Keep enums portable

Preferred approach:

- use SQLAlchemy enum handling in a way that remains portable
- if native enum behavior creates migration/dialect friction, prefer string-backed enums (`native_enum=False`) over database-native special cases

Do not create a second enum model layer just for SQLite.

### 3. Isolate locking behavior behind helpers

Current row-lock semantics should not remain scattered through runtime code.

Preferred direction:

- keep locking behind runtime/db helpers
- Postgres path can keep row-level locking
- SQLite path should use a compatible local-mode strategy such as transaction-level write locking and/or optimistic checks

Important rule:

- do not promise identical lock semantics across SQLite and Postgres
- do promise correct local behavior for SQLite

### 4. Add SQLite engine support explicitly

Add explicit SQLite support to engine/session creation.

That includes:

- adding the SQLite async driver path
- accepting SQLite database URLs
- setting SQLite-specific pragmas as needed for reliability
- making local DB creation/bootstrap first-class rather than incidental

### 5. Make migrations/tests dialect-aware

The migration/test path must stop assuming Postgres-only reset behavior.

Required split:

- Postgres integration suite remains the production-truth lane
- SQLite compatibility suite verifies local/package behavior

Typical examples:

- Postgres: schema reset / real integration lane
- SQLite: temporary DB or `drop_all/create_all` compatibility lane

## Packaging refactor plan

### 1. Move to a real installable Python package

Refactor the backend into a real package structure.

Key outcomes:

- imports work after installation
- entrypoints work without repo-relative execution
- runtime resources are package-addressable

### 2. Package definitions and migrations as data/resources

Treat definitions and migration resources as part of the product artifact.

Required behavior:

- bootstrap can load packaged definitions without a repo checkout
- migration tooling can find its resources from an installed package
- development can still override with local paths when needed

### 3. Serve bundled console assets from the package

Bundle a built console artifact into the installable distribution.

Required behavior:

- package install can serve the UI
- no separate frontend repo/runtime is required for basic operator usage
- dev mode can still use the live frontend toolchain

### 4. Add real entrypoints

Replace repo-specific execution habits with real package entrypoints.

Examples of what this means conceptually:

- API/server entrypoint
- bootstrap/init entrypoint
- optional local-dev helper entrypoints

Phase 9 should define a minimal stable CLI contract so package installs have a predictable operator surface from day one.

## Configuration plan

### Local-first defaults

For a clean local install:

- default database should be SQLite
- default state path should be inside an app-owned local data directory
- console should talk to the local API without manual Docker wiring
- OpenClaw integration should remain explicit and externally configurable

### Production defaults

For production:

- database URL should typically point to Postgres
- OpenClaw connectivity remains explicit
- Docker/systemd/orchestrator deployment can wrap the same package artifact

## CLI contract

Phase 9 should define one primary package entrypoint:

- `autoclaw`

Use subcommands rather than multiple unrelated binaries.
Keep the first stable CLI small.

### Required commands

#### `autoclaw init`

Purpose:

- create local config/state directories
- resolve the database target in one step
- write an initial config file when missing
- run schema upgrade automatically for the resolved database
- bootstrap packaged definitions automatically for the common first-run path

Database selection behavior:

1. use `--database-url <url>` if provided
2. else use an already-set env/config database URL if present
3. else fall back to the default local SQLite path under the data directory

This means the normal first-run path should be a **single command**:

- `autoclaw init`
- or `autoclaw init --database-url postgresql+asyncpg://...`

Expected flags:

- `--config <path>`
- `--data-dir <path>`
- `--database-url <url>`
- `--sqlite-path <path>`
- `--force`
- `--skip-bootstrap`
- `--skip-db-upgrade`

#### `autoclaw serve`

Purpose:

- run the API/server for local or deployed use
- serve the bundled console assets by default

Expected flags:

- `--config <path>`
- `--host <host>`
- `--port <port>`
- `--reload`
- `--open-browser`
- `--database-url <url>`
- `--log-level <level>`

#### `autoclaw db upgrade`

Purpose:

- run schema migrations/upgrade for the configured database

Expected flags:

- `--config <path>`
- `--database-url <url>`
- `--revision <revision>`

#### `autoclaw db bootstrap`

Purpose:

- load packaged definitions and initialize registry content for a clean install

Expected flags:

- `--config <path>`
- `--definitions-root <path>`
- `--force`

These `db` subcommands remain available for recovery, admin, and advanced workflows, but the **common first-install path should not require them** separately.

#### `autoclaw doctor`

Purpose:

- verify database connectivity
- verify packaged resources are available
- verify OpenClaw integration settings are present when configured
- verify console assets are installed

Expected flags:

- `--config <path>`
- `--json`

#### `autoclaw config path`

Purpose:

- print the active config path and key local directories

#### `autoclaw config show`

Purpose:

- print the resolved non-secret runtime config
- support redaction for secrets by default

Expected flags:

- `--config <path>`
- `--json`
- `--include-defaults`

#### `autoclaw openclaw check`

Purpose:

- verify configured OpenClaw connectivity without starting a flow

Expected flags:

- `--config <path>`
- `--base-url <url>`
- `--token <token>`
- `--agent-id <id>`

### CLI rules

- CLI flags override all other config sources
- commands should print human output by default and support `--json` for automation where useful
- local installs should be operable with `init -> serve` as the shortest path
- first-run DB setup should be a **single command**: `autoclaw init [--database-url <url>]`
- users should not need separate `db upgrade` and `db bootstrap` commands for the normal first-install path
- no command should require Docker for the local happy path

## Config layer contract

Phase 9 should define one clean settings model for both package installs and repo development.

### Config source precedence

Use this precedence order:

1. explicit CLI flags
2. environment variables
3. explicit config file path (`--config` or `AUTOCLAW_CONFIG`)
4. default user config file
5. built-in package defaults

### Database resolution for `autoclaw init`

For the first-run setup command, database resolution should be explicit and predictable:

1. `--database-url <url>` if supplied
2. `AUTOCLAW_DATABASE_URL` if supplied
3. configured database URL from config file if already present
4. default local SQLite database path

Default fallback when no DB URL is provided:

- `sqlite+aiosqlite:///<data_dir>/autoclaw.db`

This keeps Postgres opt-in while ensuring the tool is still usable out of the box with no Docker and no manual DB provisioning.

### Default directory layout

Use `platformdirs` rather than repo-relative paths.

Typical targets:

- config dir: platform default config home, e.g. `~/.config/autoclaw/`
- data dir: platform default data home, e.g. `~/.local/share/autoclaw/`
- state dir: platform default state home, e.g. `~/.local/state/autoclaw/`
- cache dir: platform default cache home, e.g. `~/.cache/autoclaw/`

Default config file:

- `<config_dir>/config.toml`

Default local SQLite path:

- `<data_dir>/autoclaw.db`

### Default task resource materialization layout

When task-scoped resources are materialized to the local filesystem, the default host layout should sit under the data dir, not a repo-relative `autoclaw-tasks/` folder.

Recommended shape:

- `<data_dir>/tasks/<full-task-id>/workspace/`
- `<data_dir>/tasks/<full-task-id>/context/`
- `<data_dir>/tasks/<full-task-id>/manifests/`

Rules:

- use the full task id, not a truncated prefix
- keep DB keys and logical URIs as the stable identity (`task.<task_id>.workspace`, `task://<task_id>/workspace`, and so on)
- treat `manifests/` as materialized exports or audit copies only; `context_manifests` rows remain the execution truth
- if a backend other than the local filesystem materializes these roots, preserve the same logical ids and URI contract

### Config file responsibilities

The config file should hold:

- database URL or local SQLite path
- API/server host and port
- OpenClaw connection settings
- console origin/settings where needed
- optional override paths for definitions or packaged resources
- log level and runtime mode

Do not require repo `.env` files for installed product behavior.
`.env` can remain a development convenience, not the primary installed-product config mechanism.

### Definition discovery and stable key contract

Current code already prefers packaged definitions when available and otherwise falls back to an explicit `AUTOCLAW_DEFINITIONS_ROOT` / configured `definitions_root` override. It does not implicitly scan repo-local `definitions/` in the installed-product path.

For the installed product, make the contract explicit:

- packaged definitions in the installed package are the default bootstrap source
- the default editable/operator-managed definitions root is `<config_dir>/definitions/`, with another explicit configured override path still allowed when needed
- bootstrap/import writes into the DB registry; the DB remains live truth after import
- files are import/export/bootstrap artifacts, not live runtime state

Stable identity rule:

- definition key == path key == filename stem == YAML `id`
- draft/publish APIs must continue rejecting mismatches
- duplicate keys across sources should fail deterministically or require explicit operator choice, not silently win by scan order

### Environment contract

Keep the `AUTOCLAW_` prefix for environment overrides.

At minimum, support explicit env vars for:

- `AUTOCLAW_CONFIG`
- `AUTOCLAW_DATA_DIR`
- `AUTOCLAW_DATABASE_URL`
- `AUTOCLAW_API_HOST`
- `AUTOCLAW_API_PORT`
- `AUTOCLAW_OPENCLAW_BASE_URL`
- `AUTOCLAW_OPENCLAW_GATEWAY_TOKEN`
- `AUTOCLAW_OPENCLAW_AGENT_ID`
- `AUTOCLAW_API_KEY`
- `AUTOCLAW_INTERNAL_API_KEY`
- `AUTOCLAW_LOG_LEVEL`

### Default behavior by mode

#### Local mode

Defaults should be:

- SQLite database
- packaged definitions/resources
- bundled console assets
- loopback API bind unless overridden

#### Production mode

Defaults should assume:

- explicit database URL, typically Postgres
- explicit secrets/config
- external OpenClaw endpoint configuration
- operator-managed deployment wrapper (systemd, container, orchestrator)

## Recommended non-Docker local setup

If Docker is optional, the docs should say what the preferred local install shape actually is.

Recommended path:

1. install the package with `pipx install autoclaw`
2. keep secrets in a separate env file such as `~/.config/autoclaw/autoclaw.env`
3. run `autoclaw init` for the default SQLite path, or `autoclaw init --database-url <url>` if Postgres is desired
4. let `autoclaw init` create or update the user config automatically
5. run `autoclaw serve`

### Why this is the preferred local shape

- no repo checkout required
- no Docker dependency required
- default SQLite works out of the box
- Postgres is opt-in via one extra flag or config value
- non-secret settings stay visible in config
- secrets stay out of the main config file
- later promotion to Postgres is mostly a database-URL swap rather than a full environment redesign

### Recommended config split

Use this split by default:

- `config.toml` for non-secret runtime settings
- `autoclaw.env` for secrets and emergency overrides

Typical `config.toml` responsibilities:

- server host and port
- database URL/path
- OpenClaw base URL
- OpenClaw agent id
- log level
- optional override paths

Typical `autoclaw.env` responsibilities:

- `AUTOCLAW_API_KEY`
- `AUTOCLAW_INTERNAL_API_KEY`
- `AUTOCLAW_OPENCLAW_GATEWAY_TOKEN`

### Example local `config.toml`

```toml
[server]
host = "127.0.0.1"
port = 8123

[database]
url = "sqlite+aiosqlite:///home/ubuntu/.local/share/autoclaw/autoclaw.db"

[openclaw]
base_url = "http://127.0.0.1:18789"
agent_id = "autoclaw-worker"

[logging]
level = "INFO"
```

### Example local `autoclaw.env`

```bash
AUTOCLAW_API_KEY=replace-me
AUTOCLAW_INTERNAL_API_KEY=replace-me
AUTOCLAW_OPENCLAW_GATEWAY_TOKEN=replace-me
```

### Recommended service-mode shape without Docker

For long-running host use, prefer:

- package install via `pipx` or a dedicated virtualenv
- config file in `~/.config/autoclaw/config.toml`
- secrets loaded from `EnvironmentFile=~/.config/autoclaw/autoclaw.env`
- service runner via `systemd --user`

That keeps the runtime shape consistent between interactive local use and service mode.

### Rule of thumb

- `pipx` for normal user installs
- dedicated `.venv` for contributors/developers working in the repo
- `autoclaw init` with no DB URL -> default SQLite local setup
- `autoclaw init --database-url <postgres-url>` -> Postgres setup without Docker
- install `autoclaw[postgres]` only when Postgres is actually desired
- Docker remains optional for integration testing, CI, and deployment convenience only

## Package metadata and distribution contract

### Distribution name

Use one primary PyPI distribution name:

- `autoclaw`

### Import package name

Use one primary Python import package:

- `autoclaw`

Avoid keeping the long-term installed product split across repo-shaped package names like `autoclaw-api`.

### Build metadata location

Move package build metadata to the repo root once packaging becomes real.

Preferred end state:

- root `pyproject.toml` owns the distributable package
- frontend build is a build step, not an install-time dependency
- installed package contains all required Python/runtime assets

### Core dependencies

Core install should include what is needed for the local happy path.

That means core dependencies should include the SQLite/local stack, for example:

- FastAPI / ASGI runtime
- SQLAlchemy / Alembic
- Pydantic settings
- HTTP client libraries
- `aiosqlite`
- `platformdirs`

Postgres should be an extra, not the only supported path.

### Optional extras

Recommended extras:

- `autoclaw[postgres]` -> Postgres runtime driver(s), e.g. `asyncpg`
- `autoclaw[dev]` -> lint, typecheck, test, build, release tooling
- `autoclaw[test]` -> test-only dependencies when separated from dev

Do not make Node/npm a runtime dependency for the installed Python package.
Node belongs to development/build time only.

### Packaged resources

The wheel should bundle:

- built console assets
- packaged definitions
- Alembic/migration resources
- any static templates/assets needed at runtime

The install should not need a repo checkout to find those resources.

Important packaging boundary:

- run the frontend build (`npm run build`) during the release/package build pipeline
- copy the resulting `apps/console/dist/**` output into Python package resources
- publish the Python package containing those built assets
- do **not** treat the control panel as a separately published npm package for the normal AutoClaw install path

The built `dist/` output, including hashed files under `dist/assets/`, should be included as packaged static resources and served by the installed Python application.

### Console scripts

Expose at least:

- `autoclaw = autoclaw.cli:main`

Do not require users to run module paths or repo-local scripts for common operations.

## Publish and release plan

### Versioning policy

Use one clear version policy for package releases.

Recommended path:

- stay on `0.x` while packaging/runtime surfaces are still moving materially
- use prerelease tags for release candidates when needed, e.g. `0.9.0rc1`
- move to `1.0` only after install/config/runtime contracts are stable enough to document as supported

### Build pipeline

Each release candidate should:

1. build the frontend assets
2. place bundled assets into package resources
3. build `sdist` and `wheel`
4. run `twine check`
5. run fresh-environment install smoke tests
6. run local SQLite happy-path verification
7. run Postgres integration verification

### Publish flow

Recommended order:

1. cut a release branch or release PR
2. bump version and update changelog/release notes
3. build wheel + sdist in CI
4. publish prerelease builds to TestPyPI when the release is packaging-significant
5. verify `pip install` and `pipx install` from TestPyPI in a fresh environment
6. publish to PyPI
7. create the Git tag and GitHub release

### Release verification checklist

A release is not ready unless all of these pass:

- `pip install autoclaw` works in a fresh virtualenv
- `pipx install autoclaw` works for the CLI path
- `autoclaw init` works without repo files present
- `autoclaw serve` starts and serves the packaged console
- SQLite local mode works end-to-end
- Postgres mode still passes its integration lane
- OpenClaw connectivity checks still pass with explicit config

### Rollback / bad release policy

If a broken package release escapes:

- yank the bad PyPI release rather than overwrite it
- cut a patch release with a clear fix
- keep TestPyPI verification in the loop for packaging-sensitive changes

### Publish ownership and artifacts

The release process should publish:

- `sdist`
- universal or platform-appropriate wheel(s)
- release notes summarizing install/runtime changes

Package publishing should be automated in CI once the artifact shape is stable, but initial releases can still be manually gated until the workflow proves reliable.

## Repository implementation checklist

This phase should not stay at the level of packaging intent.
It should produce a repo-level execution plan tied to the current code layout.

Use the current tree as the migration source:

- backend package/runtime today: `apps/api/app/**`
- backend packaging today: `apps/api/pyproject.toml`
- migrations today: `apps/api/alembic/**`
- frontend today: `apps/console/**`
- packaged definitions source today: `definitions/**`
- top-level repo tooling today: `Makefile`, `docker-compose.yml`, `scripts/**`

### Milestone P9.1 — package substrate and import-safe layout

Goal:

- turn the backend from a repo-local app into a real installable Python package

Current first landed slice:

- root `pyproject.toml` now exists as the package/distribution entrypoint
- a thin `autoclaw` package wrapper now exposes the public CLI / ASGI entrypoints without forcing the full internal rename yet
- root-level `pytest` now picks up the correct async config from the package metadata
- a real user-service CLI now exists via `autoclaw service install|up|stop|restart|status`, backed by a packaged systemd unit template
- the repo helper `scripts/install-systemd-user.sh` now delegates to the CLI service installer instead of rendering its own unit separately
- top-level `autoclaw up` now upgrades the DB then serves the app, matching the intended local-first happy path more closely
- the deeper internal migration away from `app.*` imports is still pending; this is the first substrate slice, not the full rename

Primary files/workstreams:

- current: `apps/api/pyproject.toml`
- current: `apps/api/app/**`
- current: `apps/api/alembic/**`
- target: root `pyproject.toml`
- target: `src/autoclaw/**`

Checklist:

- create root package metadata for the distributable product
- move or remap `apps/api/app/**` into an installable import package such as `src/autoclaw/**`
- stop relying on repo-local import assumptions such as `PYTHONPATH=.`
- make migrations import/package-safe instead of repo-layout-safe only
- ensure editable install still works for contributors
- decide whether `apps/api/pyproject.toml` is deleted, reduced to dev-only glue, or replaced by the root package metadata

Exit criteria:

- `python -c "import autoclaw"` works after install from wheel
- server startup/imports no longer depend on the repo checkout shape
- core runtime code imports from the installed package path rather than `app.*`

### Milestone P9.2 — config and path ownership layer

Goal:

- make installed-product config/path behavior explicit and independent of repo-relative defaults

Primary files/workstreams:

- current: `apps/api/app/config.py`
- current: `apps/api/app/core/settings.py`
- current: `apps/api/app/main.py`
- likely new: `src/autoclaw/config.py`
- likely new: `src/autoclaw/paths.py`
- likely new: `src/autoclaw/resources.py`

Checklist:

- replace repo-relative path discovery with `platformdirs`-based config/data/state/cache directories
- add config file loading for installed-product use, ideally `config.toml`
- define config precedence: CLI > env > explicit config path > default config file > built-in defaults
- keep `AUTOCLAW_` env overrides as the stable env contract
- make config inspection/redaction available for `autoclaw config show`
- stop requiring repo `.env` files for installed-product behavior
- keep `.env` support only as an optional development convenience
- define the default task workspace/context/manifest filesystem materialization layout under `<data_dir>/tasks/<full-task-id>/...`
- add an explicit config surface for an optional operator-managed definitions root instead of relying on repo-relative discovery in installed mode

Exit criteria:

- local install can start with no repo checkout present
- default config/data directories are outside the repo
- non-secret effective config can be printed deterministically

### Milestone P9.3 — database compatibility plan

Goal:

- support both SQLite and Postgres with one ORM model layer and an explicit behavior contract

Support contract:

- **SQLite**: local install, single-user, low-concurrency, packaging smoke, lightweight development
- **Postgres**: production, concurrent runtime, stronger locking semantics, full integration verification

Important rule:

- do not promise identical concurrency semantics across SQLite and Postgres
- do provide correct local behavior on SQLite and full production behavior on Postgres

Primary files/workstreams:

- current: `apps/api/app/db/base.py`
- current: `apps/api/app/db/session.py`
- current: `apps/api/app/db/models/registry.py`
- current: `apps/api/app/db/models/runtime.py`
- current: `apps/api/app/runtime/control.py`
- current: `apps/api/alembic/env.py`
- current: `apps/api/alembic/versions/20260414_0001_fresh_initial_schema.py`
- current: `apps/api/tests/integration/conftest.py`
- current: `apps/api/tests/integration/test_*`

Checklist:

- add a shared DB-types module such as `app/db/types.py` or `src/autoclaw/db/types.py`
- replace direct `postgresql.JSONB` usage with a portable type such as SQLAlchemy `JSON` with a Postgres `JSONB` variant
- review enum handling in `app/db/base.py`; if native DB enums complicate portability, prefer string-backed enums (`native_enum=False`)
- extend `app/db/session.py` to support both SQLite and Postgres engine creation cleanly
- add SQLite connection setup/pragmas (`foreign_keys=ON`, WAL/busy-timeout where appropriate)
- move row-locking assumptions behind a helper/abstraction instead of calling `with_for_update()` directly from runtime code
- patch `app/runtime/control.py` and any write paths that rely on Postgres row-lock semantics so SQLite local mode uses an explicit compatible write-lock/optimistic strategy
- make Alembic/env bootstrap work for both installed-package resource loading and SQLite/Postgres URL targets
- split the test strategy into:
  - Postgres integration truth lane
  - SQLite compatibility lane
- mark concurrency-sensitive tests as Postgres-only when SQLite cannot guarantee equivalent semantics

Recommended implementation notes:

- the first portability pass should target schema creation, local init, local bootstrap, and local happy-path execution on SQLite
- keep the full high-concurrency/runtime-integrity lane verified on Postgres
- do not block Phase 9 on making every concurrency-path test fully dialect-identical

Acceptance criteria:

- installed package can initialize and boot against SQLite without Docker
- current schema can be created and migrated on SQLite using the portable model/migration path
- local bootstrap definitions load correctly on SQLite
- Postgres integration suite remains green
- SQLite compatibility suite is green for the supported local-mode behaviors

### Milestone P9.4 — packaged resources and console delivery

Goal:

- make the UI and definition assets part of the product artifact rather than repo-only files

Primary files/workstreams:

- current: `apps/console/package.json`
- current: `apps/console/src/**`
- current build output: `apps/console/dist/**`
- current definitions: `definitions/**`
- likely target package resources: `src/autoclaw/web/**`, `src/autoclaw/definitions/**`, `src/autoclaw/alembic/**`
- current server entry: `apps/api/app/main.py`

Checklist:

- make frontend build a packaging/build step rather than an install-time requirement
- run `npm ci && npm run build` for `apps/console` in the release/build pipeline
- copy or bundle `apps/console/dist/**` into package resources included in the wheel
- serve bundled static assets from the installed package
- treat Vite/npm as development/build tooling only, not part of the installed runtime contract
- do not require a separate npm publish step for the control panel in the normal AutoClaw distribution path
- package `definitions/**` so bootstrap works without repo checkout
- package Alembic resources so DB upgrade works from an installed artifact
- remove any remaining build-time secret injection patterns from the console path; runtime config should come from server/config, not baked secrets
- preserve the current developer experience where Vite/live frontend can still be used during repo development
- make registry/bootstrap source order explicit: packaged definitions first, then explicit configured definitions root/import path, never implicit repo checkout state in the installed path
- enforce definition key stability rules (`path key == filename stem == YAML id`) during bootstrap/import

Exit criteria:

- `autoclaw serve` can serve the packaged console from an installed wheel
- registry/bootstrap can find packaged definitions with no repo files present
- migrations are runnable from the installed package

### Milestone P9.5 — CLI and local bootstrap experience

Goal:

- make package install usable without manual repo-specific commands

Primary files/workstreams:

- likely new: `src/autoclaw/cli.py`
- likely new: `src/autoclaw/commands/**`
- current runtime entry: `apps/api/app/main.py`
- current bootstrap helpers: `scripts/**`, `definitions/**`, runtime/bootstrap services

Checklist:

- implement the first stable CLI surface described above (`init`, `serve`, `db upgrade`, `db bootstrap`, `doctor`, `config`, `openclaw check`)
- ensure `autoclaw init` can create config/data directories and a local SQLite DB path by default
- ensure `autoclaw db bootstrap` can load packaged definitions without relying on repo scripts
- ensure `autoclaw doctor` can verify package resources, DB, and OpenClaw connectivity
- ensure common commands are human-readable by default and scriptable with `--json` where it matters

Exit criteria:

- shortest local happy path is documented and works as `autoclaw init -> autoclaw serve`
- repo-local shell snippets are no longer the primary user-facing operating path

### Milestone P9.6 — release automation and publish readiness

Goal:

- make package publication a repeatable engineering process rather than a one-off manual exercise

Primary files/workstreams:

- target: root `pyproject.toml`
- likely target: CI workflow(s) for build/test/release
- likely target: release notes/changelog files
- docs: install and release documentation

Checklist:

- add CI jobs that build frontend assets, bundle package resources, and produce wheel/sdist artifacts
- add fresh-environment install smoke tests for both `pip install` and `pipx install`
- add SQLite local happy-path smoke in CI
- keep Postgres integration verification in CI for production truth
- add TestPyPI verification for packaging-sensitive releases
- add PyPI publish workflow once artifact stability is proven
- document release owner steps, verification steps, and yank/rollback procedure

Exit criteria:

- release candidate artifacts are reproducible in CI
- TestPyPI verification is routine for packaging-significant changes
- PyPI publishing can be performed without repo-local ad-hoc steps

## Database compatibility implementation notes

Use the DB workstream above as the actionable plan, but keep these design boundaries explicit:

### What should stay shared

Keep one shared implementation for:

- ORM models
- most schema/migration ownership
- runtime services/business logic
- API/presenter layer
- definitions/bootstrap logic

### What may diverge by dialect

Allow deliberate divergence for:

- JSON storage optimization (`JSONB` on Postgres vs generic JSON on SQLite)
- connection/engine settings
- locking strategy
- test expectations around concurrency and transaction semantics

### What should not happen

Do **not**:

- create separate Postgres-only and SQLite-only model trees
- make SQLite pretend to be a full production-concurrency replacement for Postgres
- let Postgres-specific SQL leak back into general runtime code without a compatibility boundary
- let packaging be blocked forever on perfect dialect equivalence

### First-priority DB patches

If implementation starts tomorrow, patch in this order:

1. portable JSON/db types module
2. model replacements in `db/models/registry.py` and `db/models/runtime.py`
3. engine/session dialect handling in `db/session.py`
4. locking abstraction around `runtime/control.py`
5. SQLite compatibility fixtures/tests
6. package/dependency split (`aiosqlite` core, `asyncpg` extra)

## Docker’s role after this phase

Docker should remain useful, but narrower.

Good Docker roles:

- local integration testing
- CI reproducibility
- production convenience packaging
- bundled Postgres/OpenClaw helper environments

Bad Docker roles:

- being required just to run AutoClaw locally
- hiding packaging defects
- being the only way assets/config paths line up correctly

## Suggested implementation order

### Slice A — package-safe paths and resources

First fix:

- repo-relative paths
- packaged definitions/assets/migrations loading
- entrypoint structure

Why first:

- it reduces packaging ambiguity early
- it does not require committing to SQLite semantics yet

### Slice B — console packaging

Then fix:

- built asset bundling
- backend static serving from packaged resources
- runtime config separation from build-time secrets/config

### Slice C — SQLite compatibility lane

Then add:

- portable ORM types
- SQLite engine path
- local DB bootstrap
- SQLite compatibility tests

### Slice D — install UX

Then add:

- clean package entrypoints
- local-first defaults
- install/run documentation
- wheel/sdist validation

### Slice E — release verification

Finally verify:

- clean install in a fresh environment
- local SQLite happy path
- packaged console loads
- definitions bootstrap works from package resources
- Postgres integration suite still passes
- Docker smoke remains optional but healthy

## Verification gates

Do not call this phase done until all of these are true:

### Packaging gates

- wheel builds successfully
- sdist builds successfully
- clean install works in a fresh environment
- editable install still works for contributors

### Local runtime gates

- AutoClaw can boot locally without Docker
- local package install can initialize and use SQLite
- packaged definitions are discoverable without repo checkout
- packaged console assets are served correctly
- the packaged runtime contract is explicit enough that task compose/runtime container state can be inspected without transcript scraping

### Production/runtime gates

- Postgres-backed integration suite remains green
- concurrency-sensitive runtime behavior remains verified against Postgres
- Docker-based smoke still works as a supported optional path

## Documentation outcomes required from this phase

When this phase is done, the docs should clearly state:

- how to install AutoClaw locally without Docker
- when SQLite is the right choice
- when Postgres is the right choice
- how Docker fits in as an optional deployment/testing tool
- what OpenClaw must be configured separately for
- how logical task/runtime packaging works even when the first backend is an OpenClaw session rather than a literal container runtime

## End state

When this phase is complete, the clean story should be:

- AutoClaw is a real Python product, not just a repo shape
- local installs do not require Docker
- SQLite is available for the local/single-user path
- Postgres remains the production-strength path
- Docker is still useful, but optional
- OpenClaw remains an external integration boundary rather than a bundled internal subsystem
