# CLI, API, and package shape

Status: Target

This page defines the frozen package, CLI, and API boundary at the product surface level.

## Package authority

The root package manifest remains the product authority for:

- packaged Python entrypoints
- packaged console assets
- packaged migrations or Alembic resources
- packaged service templates

The shipped package must make those resources available without relying on repo-local paths.

## Surface split

### CLI

The CLI owns:

- local install and onboarding flows
- AutoClaw-local `init` and `doctor`
- OpenClaw wrapper lifecycle entrypoints under `autoclaw openclaw ...`
- local DB migration flows
- local definition import flows
- local doctor/config/service flows
- local task-compose file entry and task start flow
- OpenClaw connectivity checks
- the high-level output and automation contract for user-facing commands

### API

The API owns:

- public and browser-safe request surfaces
- operator snapshot/trace and flow control surfaces
- guarded definition registry writes
- internal runtime adapter surfaces, including the live OpenClaw dispatch,
  wait, and abort path under runtime-owned services
- runtime read models

### Package

The package owns:

- installing the backend runtime
- exposing the CLI entrypoint
- shipping bundled console and resources
- shipping migrations and service templates needed by the supported install path

## Config authority

The canonical local `config.toml` owns user-configurable runtime and adapter
knobs.

Rules:

- `[openclaw]` owns endpoint, gateway auth, agent identity, and
  request-timeout knobs for the runtime-owned OpenClaw adapter
- `[runtime]` owns dispatch-drain, watchdog, and recovery cadence knobs
- `autoclaw config ...` is the direct local config front door
- `autoclaw openclaw setup|configure` may help write or validate OpenClaw
  related config, but they do not become the owner of live runtime dispatch
  semantics
- protocol pins, required Gateway methods, required scopes, and canonical MCP
  inventories are docs/code contract truth, not user-tunable config

## OpenClaw and MCP wrapper rule

AutoClaw exposes exactly two canonical MCP tool surfaces:

1. `operator MCP`
2. `node MCP`

Rules:

- `tool` is the canonical runtime term
- `operator MCP` is the standard external parity surface and carries the
  operator-safe definition-registry, task-start, runtime-read, and runtime
  control tools
- `node MCP` is private, internal, and dispatch-bound
- `plugin` or `bundle` names one concrete OpenClaw package or wrapper that may
  expose one or both canonical MCP surfaces
- a plugin or wrapper does not create a third truth surface or rename the
  runtime model
- task-scoped observability reads, if surfaced as tools, remain operator-safe
  and stay on `operator MCP`

## Separation rules

- keep the frozen CLI aligned to currently shipped root commands, with the explicit frozen `autoclaw definitions import ...` addition
- keep `autoclaw init` AutoClaw-local and keep OpenClaw lifecycle verbs under
  `autoclaw openclaw check|setup|onboard|configure|doctor`
- keep `autoclaw openclaw check` read-only, `setup` baseline-write only,
  `onboard` guided first-run, `configure` subset re-entry only, and `doctor`
  repair-only
- keep `bootstrap` out of the primary install and onboarding vocabulary;
  reserve it for internal runtime or materialization contracts
- keep runtime control API-first, with `operator MCP` and any plugin or MCP
  wrapper only as adapter-specific parity surfaces over operator-safe routes
- keep actual OpenClaw dispatch, wait, abort, and callback-binding logic
  runtime-owned rather than migrating it into CLI/package or wrapper setup
  surfaces
- keep guarded definition revision lifecycle API-owned even though local
  definition import is now a canonical root CLI front door and the standard
  external plugin or MCP wrapper may mirror those routes
- keep public noun families explicit in the API even when the CLI shape differs
- keep `--json` as output-shape only, keep `--non-interactive` as the
  automation switch, and keep rich styling TTY-only with `--plain`,
  `--no-color`, and `NO_COLOR` escape hatches
- keep the rich CLI visual grammar aligned to OpenClaw's lobster-palette,
  panel-and-section, data-dense terminal layout instead of inventing a
  separate AutoClaw presentation language
- do not collapse `node MCP` and `operator MCP` into one shared mixed catalog
  or session

## Installed-resource expectations

The packaged install must expose:

- CLI entrypoint
- console assets
- migration resources
- service-template resources

## Related contracts

- `cli-surface-and-operator-workflows.md`
- `api-surface-and-trust-lane-map.md`
- `../how-to/install-and-onboard.md`
- `release-and-install-strategy.md`
- `distribution-and-database-support-matrix.md`
