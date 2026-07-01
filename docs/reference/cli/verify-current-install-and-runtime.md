# Verify an install and runtime

This page defines the fast local verification lane that is still supported by the shipped CLI and API tree.

## Procedure

1. Run `autoclaw onboard --json --non-interactive`
2. Run `autoclaw doctor --json`
3. Run `autoclaw openclaw check --json`
4. Start the API with `autoclaw serve`, or use `autoclaw service start` if the managed Linux user service has already been installed
5. Confirm `GET /healthz` returns `200 OK`
6. Confirm `GET /readyz` returns `200 OK`

## Expected healthy signs

- `autoclaw onboard --json` writes config, seeds the shipped SQLite runtime, repairs a legacy incompatible local SQLite schema by backing it up and reconciling a fresh runtime DB when needed, selects or bootstraps the AutoClaw worker/operator agent path, patches those OpenClaw agent profiles, writes the OpenClaw-managed AutoClaw MCP server definitions, and rewrites the local wrapper material when the OpenClaw host shape is supported
- `autoclaw doctor --json` reports local config, DB, packaged-resource, managed-service, and OpenClaw integration health
- `autoclaw openclaw check --json` reports selected worker/operator agent state, patched OpenClaw agent-profile state, OpenClaw-managed AutoClaw MCP server state, wrapper-state presence, and compatibility state without writing
- `autoclaw openclaw check --json` does not prove session-effective worker-session MCP mounting; it verifies direct config, wrapper, compatibility, and material state only
- `autoclaw serve` starts the API without immediate fatal errors
- `autoclaw service start` starts the managed Linux `systemd --user` service after that service has been installed
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
- external provider or OpenClaw integration reachability beyond the local API surface
- session-effective worker-session MCP inventories through the live OpenClaw bundle-MCP path

## Relationship to the stronger lane

Use this page for a fast local confidence check.

If you are running the sequence in a non-TTY environment such as CI or a script runner, keep `--non-interactive` on the guided commands so they do not stop on prompt handling.

Use [Run Docker-backed Postgres verification](../maintainers/run-docker-postgres-verification.md) when you need the stronger DB-backed lane.
