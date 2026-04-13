# Backlog

This file is a **parking lot**, not committed roadmap truth.

## Near-term cleanup / quality follow-ups

- add CI for `make check-api`, `make test-api`, and `make test-api-db`
- replace generic `ValueError` service exceptions with typed domain exceptions
- add presenter-focused tests and explicit API error-path tests
- add a scripted end-to-end runtime smoke path
- review additional indexes as new list/history/query paths are introduced

## Candidate future work

- richer policy model
- OpenTelemetry / tracing / structured observability
- deeper operator graph explorer
- workflow-pack library expansion
- pack templates for research, release, compliance, and MVP building
- import/export polish for registry definitions
- stronger OpenClaw integration ergonomics
- concurrency controls and scheduling refinements
- audit/event stream hardening
- docs/examples for contributors and extension authors
