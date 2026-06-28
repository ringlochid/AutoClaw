# Prepare a release

Status: Reference

Last verified: 2026-06-28

Use this guide when preparing public package artifacts.

Release-ready means code, tests, docs, examples, package resources, install behavior, DB behavior, and supported workflows agree.

## Before building

Confirm:

- the release scope is clear
- version changes are intentional
- public docs match supported behavior
- examples match shipped schemas and workflow keys
- package data includes definitions, prompt assets, and service resources needed at runtime
- migrations, reset, and upgrade behavior are covered when DB truth changed
- unsupported install channels are not described as shipped support

## Required evidence

At minimum, collect:

- `make check-api`
- applicable unit and integration tests
- docs freeze validation
- markdown unwrap check for touched docs
- package build success
- package install smoke for the supported public lane

Add stronger lanes when relevant:

- `make test-api-db` for DB, schema, reset, upgrade, registry, or Postgres behavior
- relevant e2e lane for runtime, parent-first flows, human requests, command runs, support-state, or launch behavior
- prompt catalog generation and validation when prompt assets changed

Use [choose a verification lane](choose-a-verification-lane.md) to map the release scope to commands.

## Build and publish rule

Publish only from the root packaging surface.

The supported v1 distribution story is:

- PyPI wheel and sdist
- `pipx install autoclaw`
- `pipx install "autoclaw[postgres]"`
- `uv tool install autoclaw`
- `uv tool install "autoclaw[postgres]"`

Convenience channels such as standalone binaries, npm shims, Homebrew, macOS service parity, and Windows service parity are not shipped v1 support unless a later change explicitly adds and verifies them.

## Install smoke

After building or publishing, prove at least one clean install path:

```bash
pipx install autoclaw
autoclaw onboard
autoclaw doctor
autoclaw openclaw check
```

For the managed Linux service lane:

```bash
autoclaw onboard --install-daemon
autoclaw service status
```

For Postgres release scope, also prove the extra plus `AUTOCLAW_DATABASE_URL` path.

## Post-release checks

Check:

- package can be installed from the intended artifact source
- `autoclaw --version` reports the intended version
- `autoclaw doctor` is healthy on the supported path
- `autoclaw openclaw check` is healthy in a supported OpenClaw shape
- docs front doors point at current public behavior

## Related pages

- [Publish a release](../reference/maintainers/publish-a-release.md)
- [Testing and release checklist](../reference/maintainers/testing-and-release-checklist.md)
- [Release and install strategy](../reference/maintainers/release-and-install-strategy.md)
- [Recover a broken release](recover-a-broken-release.md)
