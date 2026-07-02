# Recover a broken release

Use this guide when a published or release-candidate package is wrong.

AutoClaw does not define a special rollback command. Recovery is a maintainer process: identify the broken surface, preserve evidence, repair the smallest correct slice, verify the affected lanes, and publish a fixed artifact when needed.

## First response

Classify the break:

- install failure
- onboarding or OpenClaw support failure
- service startup or health failure
- task launch failure
- runtime or operator behavior failure
- DB, migration, reset, or Postgres failure
- docs or examples mismatch

Preserve:

- package version
- install command
- platform and Python version
- `autoclaw doctor --json`
- `autoclaw openclaw check --json`
- service status or serve log
- task id and operator trace when a task exists

Redact secrets before sharing evidence.

## Stabilize users

If there is a safe documented workaround, publish that first.

Examples:

- use `autoclaw serve` instead of the managed service on unsupported hosts
- use SQLite until the Postgres lane is repaired
- run `autoclaw openclaw check` and fix the support shape before re-running setup
- use the previous known-good package version when the package index still offers it

Do not document unsupported service managers, installers, or OpenClaw Gateway shapes as temporary official support.

## Repair

Patch the owning surface:

- packaging resource or dependency issue -> [maintain packaging](maintain-packaging.md)
- DB or migration issue -> [maintain database support](maintain-database-support.md)
- docs or example issue -> [maintain docs](maintain-docs.md)
- runtime or task behavior issue -> use the relevant backend owner docs and verification lane

Update docs and examples in the same change when the public contract changed.

## Verify

Run the lane that proves the broken surface. The smallest local test is not enough when the failed surface is broader.

Common recovery checks:

```bash
make check-api
./.venv/bin/python -m scripts.docs.docs_freeze.cli validate
git diff --check
```

Add:

- `make test-api-db` for DB-backed breaks
- relevant e2e lane for task-launch or runtime breaks
- package build and install smoke for package breaks
- `autoclaw onboard`, `autoclaw doctor`, and `autoclaw openclaw check` for setup breaks

## Publish the fix

For public package releases:

- publish only from the root package surface
- use a new fixed version rather than mutating a released artifact
- update release notes with the affected surface and verification
- consider yanking only when the broken package should not be installed and the package index workflow supports it

## Related pages

- [Prepare a release](prepare-a-release.md)
- [Choose a verification lane](choose-a-verification-lane.md)
- [Testing and release checklist](../reference/maintainers/testing-and-release-checklist.md)
- [Diagnostic bundle](../help/diagnostic-bundle.md)
