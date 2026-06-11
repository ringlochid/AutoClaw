# Testing guide

Status: Reference

Use this page to choose the proof lane that matches the surface you changed.

## Main proof lanes

- fast local confidence: [Verify the current install and runtime](../reference/cli/verify-current-install-and-runtime.md)
- stronger DB-backed lane: [Run Docker Postgres verification](../reference/maintainers/run-docker-postgres-verification.md)
- workflow proof lanes: [Run real e2e workflow lanes](../reference/maintainers/run-real-e2e-workflow-lanes.md)

## Rule of thumb

- use the fast local lane for install/start sanity
- use the Postgres lane when DB-backed behavior matters
- use the real e2e lanes when the runtime or workflow story is the thing you are validating
