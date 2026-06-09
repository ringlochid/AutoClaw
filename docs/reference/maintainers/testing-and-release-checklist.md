# Testing and release checklist

Status: Reference

This page defines the stable maintainer checklist for tests, package validation, release readiness, and docs parity.

## Hard rule

Release-ready means:

- code, tests, docs, and examples agree
- the required public and maintainer surfaces are exercised at the appropriate lane depth
- package, install, DB, and reset behavior are explicitly checked
- missing mandatory evidence blocks release

## Required evidence groups

### Unit and integration

- unit coverage for changed core logic
- integration coverage for changed runtime, DB, route, provider, CLI, package, or plugin behavior
- explicit note when a test category was not viable and why

### E2E lanes

The required workflow lanes follow the progressive lane matrix:

- minimal lane when prompt/runtime/bootstrap flow is viable
- normal lane when parent/review/closure flow is viable
- maximal lane when multi-subtree/review/replan flow is viable

### Package, install, and DB

- package build success for the shipped package surface
- install smoke for the supported `pipx` path
- package resource presence checks for bundled console assets, definitions, migrations, and service templates
- SQLite local-smoke verification
- Postgres + Docker strong-lane verification
- reset or migration smoke when DB, package, or public-surface truth changed

### Docs and examples

- updated docs for every changed contract
- updated examples for every changed example contract
- regenerated prompt inventory and rendered examples when prompt-layer authorities changed
- validator pass for the docs set

## Related maintainer pages

- [Run Docker-backed Postgres verification](run-docker-postgres-verification.md)
- [Run real e2e workflow lanes](run-real-e2e-workflow-lanes.md)
- [Publish a release](publish-a-release.md)
