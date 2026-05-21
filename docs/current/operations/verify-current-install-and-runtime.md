# Verify the current install and runtime

Status: Current

Last verified: 2026-05-12

This page defines the current local fast verification lane that is still provable from the shipped CLI and API tree.

## Procedure

1. Run `autoclaw init --json`
2. Start the API with `autoclaw serve` or `autoclaw service start`
3. Confirm `GET /healthz` returns `200 OK`
4. Confirm `GET /readyz` returns `200 OK`

## Expected healthy signs

- `autoclaw init --json` writes config and seeds the shipped SQLite runtime
- `autoclaw serve` starts the API without immediate fatal errors
- `autoclaw service start` provides a durable local launch path when verification must survive the parent shell/session lifecycle
- `/healthz` reports service health
- `/readyz` reports database-backed readiness

## What this proves

- config is writable on the shipped path
- seeded definitions are available on the shipped SQLite lane
- DB connection works for the configured lane
- the current local API can start and answer health probes

## What this does not prove

- full DB-backed integration coverage
- Docker/Postgres verification
- external provider or bridge reachability beyond the local API surface

## Relationship to the stronger lane

Use this page for a fast local confidence check.

Use `run-docker-postgres-verification.md` when you need the stronger DB-backed lane described by the current repo docs as the better verified baseline.

## Evidence

- inspected CLI entrypoints in `apps/api/app/cli.py`, including `init` and `serve`
- inspected API startup in `apps/api/app/main.py`
- inspected health routes in `apps/api/app/api/routes/health.py`
- inspected current verification framing in `../README.md` and `run-docker-postgres-verification.md`
- did not execute the commands in this page during this docs pass
