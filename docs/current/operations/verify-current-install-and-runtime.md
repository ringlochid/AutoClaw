# Verify the current install and runtime

Status: Current

Last verified: 2026-05-28

This page defines the current local fast verification lane that is still provable from the shipped CLI and API tree.

## Procedure

1. Run `autoclaw onboard --json`
2. Run `autoclaw doctor --json`
3. Run `autoclaw openclaw check --json`
4. Start the API with the managed Linux user service `autoclaw service start` or with `autoclaw serve`
5. Confirm `GET /healthz` returns `200 OK`
6. Confirm `GET /readyz` returns `200 OK`

## Expected healthy signs

- `autoclaw onboard --json` writes config, seeds the shipped SQLite runtime, repairs a legacy incompatible local SQLite schema by backing it up and reconciling a fresh runtime DB when needed, selects or bootstraps the AutoClaw worker/operator agent path, patches those OpenClaw agent profiles, writes the OpenClaw-managed AutoClaw MCP server definitions, and rewrites the local wrapper material when the OpenClaw host shape is supported
- `autoclaw doctor --json` reports local config, DB, packaged-resource, managed-service, and OpenClaw integration health
- `autoclaw openclaw check --json` reports selected worker/operator agent state, patched OpenClaw agent-profile state, OpenClaw-managed AutoClaw MCP server state, wrapper-state presence, and compatibility state without writing
- `autoclaw serve` starts the API without immediate fatal errors
- `autoclaw service start` starts the managed Linux `systemd --user` service
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
