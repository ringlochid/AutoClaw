# Phase 5A Definition Read Write Start Subset Plan

Status: Reference

selected phase: Phase 5A
current phase page: docs/execution/phases/phase-5a-definition-ingest-api-and-cli.md
selected work packages: P5A-WP1
summary-only: no
delegated slices: listed
slice id: phase5a-public-http-subset
slice type: edit
owned surfaces: apps/api/app/registry/**, apps/api/app/api/routes/**, apps/api/app/api/router.py, apps/api/tests/integration/phase5a/**
touched surfaces: apps/api/app/registry/**, apps/api/app/api/routes/definitions.py, apps/api/app/api/routes/tasks.py, apps/api/app/api/router.py, apps/api/tests/integration/phase5a/**
slice id: phase5a-operator-mcp-subset
slice type: edit
owned surfaces: apps/api/autoclaw/openclaw/operator_server.py, apps/api/autoclaw/openclaw/common.py, apps/api/autoclaw/openclaw/operator_mcp/**, apps/api/tests/integration/phase4b/mcp/, apps/api/tests/integration/phase5a/mcp/**
touched surfaces: apps/api/autoclaw/openclaw/operator_server.py, apps/api/autoclaw/openclaw/common.py, apps/api/autoclaw/openclaw/operator_mcp/**, apps/api/tests/integration/phase4b/mcp/, apps/api/tests/integration/phase5a/mcp/**
slice id: phase5a-schema-contract
slice type: edit
owned surfaces: apps/api/app/schemas/definitions/**, apps/api/app/schemas/runtime/**, apps/api/tests/unit/test_phase5a_schema_contract.py
touched surfaces: apps/api/app/schemas/definitions/**, apps/api/app/schemas/runtime/**, apps/api/tests/unit/test_phase5a_schema_contract.py
slice id: phase5a-review
slice type: review-only
owned surfaces: apps/api/app/registry/**, apps/api/app/api/routes/**, apps/api/autoclaw/openclaw/operator_server.py, apps/api/app/schemas/**, apps/api/tests/integration/phase5a/**, apps/api/tests/unit/test_phase5a_schema_contract.py, docs/execution/plans/phase-5a-definition-read-write-start-subset.md, docs/execution/evidence/phase-5a-definition-read-write-start-subset.md, docs/execution/reviews/phase-5a-definition-read-write-start-subset.md
touched surfaces: none

## Goal

Land the minimum shared-service-backed Phase 5A subset:

- public `/definitions` read/write routes
- public `POST /tasks/start`
- operator MCP definition read/history/upload/start parity
- no root CLI noun-family widening in this slice

## Ordered Work

1. Create a shared definition catalog/history/task-start service boundary.
2. Land the public HTTP subset on top of that service.
3. Land operator MCP parity on the same service.
4. Align the public schemas and focused tests.

## Validation

- focused Phase 5A schema, public HTTP, and operator MCP tests
- narrow lint/type checks on touched surfaces

## Delegated Slice Briefs

### phase5a-public-http-subset

- do-not-edit surfaces:
  - `apps/api/autoclaw/openclaw/**`
  - CLI and execution artifacts
- required reads:
  - Phase 5A page, definition contracts, API schema appendix, current registry/API contrast docs
- expected outputs:
  - shared definition service
  - `/definitions/*` and `/tasks/start` HTTP subset
- required validators:
  - focused HTTP subset tests
  - narrow lint on owned files
- dependencies:
  - schema contracts available
- parent-owned decisions:
  - exact public noun family for the minimum subset
- evidence to return:
  - changed file list
  - focused command outcomes
- stop conditions:
  - if operator MCP or CLI changes are required

### phase5a-operator-mcp-subset

- do-not-edit surfaces:
  - registry/API route code except read/reference
  - CLI and execution artifacts
- required reads:
  - Phase 5A page, operator MCP contract docs, machine catalog, shared service code
- expected outputs:
  - operator MCP definition/history/upload/start parity on the shared service
- required validators:
  - focused MCP tests
  - narrow lint on owned files
- dependencies:
  - shared definition service available
- parent-owned decisions:
  - operator MCP parity shape for the minimum subset
- evidence to return:
  - changed file list
  - focused command outcomes
- stop conditions:
  - if broader registry/API refactors are required

### phase5a-schema-contract

- do-not-edit surfaces:
  - routes, operator MCP, docs
- required reads:
  - Phase 5A page, API schema appendix, machine catalog, definition/task-start contracts
- expected outputs:
  - typed schemas for the new public/operator subset
- required validators:
  - focused unit schema tests
- dependencies:
  - selected subset contract fixed
- parent-owned decisions:
  - exact schema split for public vs operator parity
- evidence to return:
  - changed file list
  - focused command outcomes
- stop conditions:
  - if route/service work is required

### phase5a-review

- do-not-edit surfaces:
  - all repo-tracked files
- required reads:
  - Phase 5A page, plan, evidence, touched code/tests/docs
- expected outputs:
  - strict review verdict and closure-draft content only
- required validators:
  - non-mutating proof checks only
- dependencies:
  - edit slices integrated
- parent-owned decisions:
  - none; this slice reports review truth only
- evidence to return:
  - exact findings or pass verdict
  - draft-ready review text
- stop conditions:
  - if any repo edit seems necessary

## Exit Evidence

- HTTP and operator MCP use one shared service
- definition history remains operator-only
- public and operator subset tests pass
