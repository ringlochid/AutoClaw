# Run the current Docker and Postgres verification lane

Status: Current

Last verified: 2026-05-05

This page defines the stronger current verification lane.

If this repo-native DB-lane command surface changes, update this page together with the touched command surface so the documented procedure stays current.

## Procedure

1. Run the self-contained DB-backed suite: `make test-api-db`

## What this proves

- Postgres-backed integration behavior
- the isolated Docker compose test path for Postgres-backed proof
- the stronger DB-backed verification lane used by the current repo tooling

## What this does not prove

- every provider or continuity scenario
- every local-only CLI path
- non-Postgres production environment behavior

## Relationship to the fast lane

This is the stronger current DB-backed lane.

Keep `make test-api-integration` as the default repo-native integration lane.

It is appropriate when you need:

- schema and reset proof on Postgres
- the Dockerized API test container path without depending on a separately-started compose stack
- higher-confidence runtime and registry verification than unit tests alone

## Notes

- `make test-api-db` brings up the isolated test compose project, recreates `autoclaw_test`, runs the grouped integration suite, and tears the test project down on exit.
- `make docker-up` and `make docker-down` remain the manual development stack commands; they are not required for this proof lane.
- The documented `make test-api-db` command surface was last aligned to repo truth on 2026-05-23.

## Evidence

- inspected `Makefile` target `test-api-db` plus the unit, local integration, and e2e companion targets
- inspected `docker-compose.yml` isolated `postgres-test` and `api-test` services plus the repo-owned grouped runner under `scripts/testing/`
- did not execute the full DB-backed lane for this page
