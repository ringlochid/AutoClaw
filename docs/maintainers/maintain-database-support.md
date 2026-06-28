# Maintain database support

Status: Reference

Last verified: 2026-06-28

Use this guide when changing persistence, schema, migrations, reset, upgrade, registry currentness, or SQLite/Postgres behavior.

## Supported DB posture

AutoClaw is SQLite-first for local use.

The stronger DB-backed lane is Postgres through:

- `pipx install "autoclaw[postgres]"`
- `uv tool install "autoclaw[postgres]"`
- `AUTOCLAW_DATABASE_URL=postgresql+asyncpg://...`

Installing the Postgres extra only adds the driver. It does not select Postgres without a Postgres database URL.

## When DB changes require Postgres proof

Run the Postgres lane when a change touches:

- schema creation, migration, reset, or upgrade
- runtime persistence models
- registry currentness or revision storage
- task launch persistence
- command-run or human-request source rows
- SQL that may behave differently across SQLite and Postgres
- legacy repair or cross-DB compatibility code

## Required checks

Use focused tests while iterating. Before closeout, run the applicable lanes:

```bash
make check-api
make test-api-unit
make test-api-integration
make test-api-db
```

Use the e2e lanes when DB changes can affect launched workflow execution:

```bash
make test-api-e2e-minimal
make test-api-e2e-normal
make test-api-e2e-maximal
```

Choose the smallest e2e lane that proves the changed surface; use heavier lanes when parent-first or multi-subtree behavior is affected.

## Reset and upgrade expectations

`autoclaw db upgrade` should ensure schema and seed packaged definitions.

`autoclaw db reset` recreates the shipped SQLite database path, reapplies schema, and reseeds definitions.

Onboarding can repair some older incompatible local SQLite state by backing it up and reconciling a fresh current-schema runtime DB.

When changing repair behavior, prove both:

- successful current-schema setup
- the relevant legacy or incompatible-state path

## Cross-DB review checklist

- constraints encode real runtime truth
- relationship and foreign-key behavior works on SQLite and Postgres
- enum and JSON usage stays portable unless the boundary is intentionally Postgres-only
- reseeding preserves controller-owned currentness
- task launch reads registry current truth, not repo seed files
- `/readyz` still reflects DB readiness
- docs explain the package extra plus database URL requirement

## Related pages

- [Use Postgres on the DB-backed lane](../reference/maintainers/use-postgres.md)
- [Run Docker-backed Postgres verification](../reference/maintainers/run-docker-postgres-verification.md)
- [Distribution and database support matrix](../reference/maintainers/distribution-and-database-support-matrix.md)
- [Postgres and database problems](../help/postgres-and-database.md)
