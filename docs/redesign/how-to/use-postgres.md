# Use Postgres in the redesign target

Status: Target

This page defines the frozen stronger verification and concurrency lane.

## Package path

Install the Postgres-enabled package:

```bash
pipx install "autoclaw[postgres]"
```

## Runtime configuration

Set the exact DB environment variable:

```bash
AUTOCLAW_DATABASE_URL=postgresql+asyncpg://autoclaw:autoclaw@127.0.0.1:5432/autoclaw
```

## Product procedure

1. Install the Postgres extra
2. Set `AUTOCLAW_DATABASE_URL`
3. Run migrations: `autoclaw db upgrade`
4. Confirm health: `autoclaw doctor`
5. Start the product: `autoclaw serve`
6. Optional durable local-service path without systemd: `autoclaw service start`

## Strong verification lane

Use the stronger Docker-backed verification path:

```bash
make docker-up
make test-api-db
make docker-down
```

## Lane rule

Postgres + Docker is the stronger verification lane and the required release proof path for DB-backed behavior.
