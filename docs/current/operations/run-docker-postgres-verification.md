# Run the current Docker and Postgres verification lane

Status: Current

Last verified: 2026-05-05

This page defines the stronger current verification lane.

## Procedure

1. Start the compose stack: `make docker-up`
2. Run the DB-backed suite: `make test-api-db`
3. Stop the compose stack when you are done: `make docker-down`

## What this proves

- Postgres-backed integration behavior
- the shipped Docker compose path for the API and Postgres
- the stronger DB-backed verification lane used by the current repo tooling

## What this does not prove

- every provider or continuity scenario
- every local-only CLI path
- non-Postgres production environment behavior

## Relationship to the fast lane

This is the stronger current DB-backed lane.

It is appropriate when you need:

- schema and reset proof on Postgres
- the Dockerized API test container path
- higher-confidence runtime and registry verification than unit tests alone

## Evidence

- inspected `Makefile` targets `docker-up`, `test-api-db`, and `docker-down`
- inspected `docker-compose.yml` as the current compose entrypoint
- did not execute the commands in this docs pass
