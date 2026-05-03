# Run the current Docker and Postgres verification lane

Status: Current

Last verified: 2026-04-24

This page defines the stronger current verification lane.

## Procedure

1. Start the compose stack: `make docker-up`
2. Run the DB-backed suite: `make test-api-db`
3. Stop the compose stack: `make docker-down`

## What this proves

- Postgres-backed integration behavior
- current migration/schema path on the stronger DB lane
- the stronger verified baseline used by the current repo documentation

## What this does not prove

- every external provider path
- every plugin configuration lane
- non-Postgres production environment behavior

## Relationship to the fast lane

Use `verify-current-install-and-runtime.md` for a quick local confidence check.

Use this page when you need the stronger verified lane and a DB-backed proof path instead of a local-only smoke.

## Evidence

- inspected `autoclaw-main/Makefile` targets `docker-up`, `test-api-db`, and `docker-down`
- inspected `autoclaw-main/docker-compose.yml` as the current compose entrypoint
- did not execute the commands in this page during this docs pass
