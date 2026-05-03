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
- local DB migration flows
- local definition import flows
- local doctor/config/service flows
- local task-compose file entry and task start flow
- OpenClaw connectivity checks

### API

The API owns:

- public and browser-safe request surfaces
- operator snapshot/trace and flow control surfaces
- guarded definition registry writes
- internal runtime adapter surfaces
- runtime read models

### Package

The package owns:

- installing the backend runtime
- exposing the CLI entrypoint
- shipping bundled console and resources
- shipping migrations and service templates needed by the supported install path

## Separation rules

- keep the frozen CLI aligned to currently shipped root commands, with the explicit frozen `autoclaw definitions import ...` addition
- keep runtime control API-first, with the standard external plugin only as an adapter-specific parity surface over operator-safe routes
- keep guarded definition revision lifecycle API-owned even though local definition import is now a canonical root CLI front door and the standard external plugin may mirror those routes
- keep public noun families explicit in the API even when the CLI shape differs
- do not collapse the internal dispatch-bound runtime adapter lane and the external operator-safe plugin parity surface

## Installed-resource expectations

The packaged install must expose:

- CLI entrypoint
- console assets
- migration resources
- service-template resources

## Related contracts

- `cli-surface-and-operator-workflows.md`
- `api-surface-and-trust-lane-map.md`
- `release-and-install-strategy.md`
- `distribution-and-database-support-matrix.md`
