# Postgres and database problems

Use this page when DB setup, migrations, reset, `/readyz`, or the Postgres-backed lane fails.

## Supported DB lanes

The default shipped local lane is SQLite.

The supported Postgres lane requires:

- installing `autoclaw[postgres]`
- setting `AUTOCLAW_DATABASE_URL` to a Postgres SQLAlchemy URL
- running onboarding and schema upgrade against that URL

Installing the Postgres extra only adds the async driver. It does not select Postgres unless `AUTOCLAW_DATABASE_URL` points at Postgres.

## `/readyz` fails

Check:

```bash
autoclaw doctor --json
autoclaw db upgrade
curl http://127.0.0.1:18125/readyz
```

Likely causes:

- database URL is invalid
- database server is unavailable
- schema was not created or upgraded
- package was installed without the Postgres extra
- the service environment differs from the shell environment

## Postgres driver is missing

Fix by installing the Postgres extra:

```bash
pipx install "autoclaw[postgres]"
```

or:

```bash
uv tool install "autoclaw[postgres]"
```

Then set:

```bash
export AUTOCLAW_DATABASE_URL=postgresql+asyncpg://autoclaw:autoclaw@127.0.0.1:5432/autoclaw
```

Use your real local credentials instead of the example values.

## Reset or upgrade fails

Use `db upgrade` when you want to create or migrate schema without dropping the configured database.

Use `db reset` only when you intentionally want to recreate the shipped SQLite database path and reseed packaged definitions.

Check:

- the configured database URL
- whether the command is running against SQLite or Postgres
- whether the process has permission to write the data dir
- whether the database contains older incompatible state

Current onboarding can repair some older incompatible local SQLite state by backing it up and reconciling a fresh current-schema runtime DB.

## Strong verification lane fails

The repo-owned strong DB lane is:

```bash
make test-api-db
```

This command brings up the isolated test compose project, recreates `autoclaw_test`, runs the grouped integration suite, and tears the test project down on exit.

Use it when DB-backed behavior, schema, reset, migration, or Postgres-specific behavior changed.

## Related pages

- [Use Postgres on the DB-backed lane](../reference/maintainers/use-postgres.md)
- [Run Docker-backed Postgres verification](../reference/maintainers/run-docker-postgres-verification.md)
- [Distribution and database support matrix](../reference/maintainers/distribution-and-database-support-matrix.md)
