# Verify the current install and runtime

Status: Current

Last verified: 2026-04-24

This page defines the current local fast verification lane.

## Procedure

1. Run `autoclaw doctor`
2. Run `autoclaw openclaw check`
3. Start the service with `autoclaw up`
4. Confirm the API and console are reachable

## Expected healthy signs

- `autoclaw doctor` reports readable config and usable local paths
- `autoclaw openclaw check` reports the current OpenClaw gateway result without hanging
- `autoclaw up` starts the API and console without immediate fatal errors
- the API responds and the console loads

## What this proves

- config is readable
- definitions are visible
- DB connection works for the configured lane
- OpenClaw gateway reachability is known
- the current local runtime can start

## What this does not prove

- full DB-backed integration coverage
- Docker/Postgres verification
- end-to-end bridge smoke beyond the current local surface

## Relationship to the stronger lane

Use this page for a fast local confidence check.

Use `run-docker-postgres-verification.md` when you need the stronger DB-backed lane described by the current repo docs as the better verified baseline.

## Evidence

- inspected CLI entrypoints in `autoclaw-main/apps/api/app/cli.py`, including `doctor`, `up`, and `openclaw check`
- inspected current verification framing in `../README.md` and `run-docker-postgres-verification.md`
- did not execute the commands in this page during this docs pass
