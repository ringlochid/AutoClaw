# Phase 5A Definition Read Write Start Subset Evidence

Status: Reference

selected phase: Phase 5A
current phase page: docs-internal/execution/v1/phases/phase-5a-definition-ingest-api-and-cli.md
selected work packages: P5A-WP1
summary-only: no
delegated slices: listed
slice id: phase5a-public-http-subset
slice type: edit
owned surfaces: apps/api/src/autoclaw/definitions/registry/**, apps/api/src/autoclaw/interfaces/http/routers/**, apps/api/src/autoclaw/interfaces/http/router.py, apps/api/tests/integration/public_surfaces/**
touched surfaces: apps/api/src/autoclaw/definitions/registry/**, apps/api/src/autoclaw/interfaces/http/routers/definitions.py, apps/api/src/autoclaw/interfaces/http/routers/tasks.py, apps/api/src/autoclaw/interfaces/http/router.py, apps/api/tests/integration/public_surfaces/**
slice id: phase5a-operator-mcp-subset
slice type: edit
owned surfaces: apps/api/src/autoclaw/interfaces/mcp/operator/server.py, apps/api/src/autoclaw/interfaces/mcp/transport.py, apps/api/src/autoclaw/interfaces/mcp/operator/**, apps/api/tests/integration/mcp/, apps/api/tests/integration/public_surfaces/mcp/**
touched surfaces: apps/api/src/autoclaw/interfaces/mcp/operator/server.py, apps/api/src/autoclaw/interfaces/mcp/transport.py, apps/api/src/autoclaw/interfaces/mcp/operator/**, apps/api/tests/integration/mcp/, apps/api/tests/integration/public_surfaces/mcp/**
slice id: phase5a-schema-contract
slice type: edit
owned surfaces: apps/api/src/autoclaw/definitions/contracts/**, apps/api/src/autoclaw/runtime/contracts/**, apps/api/tests/unit/test_phase5a_schema_contract.py
touched surfaces: apps/api/src/autoclaw/definitions/contracts/**, apps/api/src/autoclaw/runtime/contracts/**, apps/api/tests/unit/test_phase5a_schema_contract.py
slice id: phase5a-review
slice type: review-only
owned surfaces: apps/api/src/autoclaw/definitions/registry/**, apps/api/src/autoclaw/interfaces/http/routers/**, apps/api/src/autoclaw/interfaces/mcp/operator/server.py, apps/api/app/schemas/**, apps/api/tests/integration/public_surfaces/**, apps/api/tests/unit/test_phase5a_schema_contract.py, docs-internal/execution/v1/plans/phase-5a-definition-read-write-start-subset.md, docs-internal/execution/v1/evidence/phase-5a-definition-read-write-start-subset.md, docs-internal/execution/v1/reviews/phase-5a-definition-read-write-start-subset.md
touched surfaces: none

## Plan and review links

- approved plan: `../plans/phase-5a-definition-read-write-start-subset.md`
- mandatory review: `../reviews/phase-5a-definition-read-write-start-subset.md`
- review artifact: `../reviews/phase-5a-definition-read-write-start-subset.md`

## Commands Run

- `./.venv/bin/pytest apps/api/tests/unit/test_phase5a_schema_contract.py apps/api/tests/integration/public_surfaces/test_public_http_subset.py apps/api/tests/integration/public_surfaces/mcp/test_operator_server_phase5a.py apps/api/tests/integration/mcp/ -q`
- `./.venv/bin/ruff check apps/api/src/autoclaw/definitions/registry/** apps/api/src/autoclaw/interfaces/http/routers/definitions.py apps/api/src/autoclaw/interfaces/http/routers/tasks.py apps/api/src/autoclaw/interfaces/http/router.py apps/api/src/autoclaw/interfaces/mcp/transport.py apps/api/src/autoclaw/interfaces/mcp/operator/server.py apps/api/src/autoclaw/interfaces/mcp/operator apps/api/src/autoclaw/definitions/contracts/** apps/api/src/autoclaw/runtime/contracts/** apps/api/tests/integration/public_surfaces/** apps/api/tests/unit/test_phase5a_schema_contract.py apps/api/tests/integration/mcp/`
- `make pyright-api` on the final integrated state
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings` on the final integrated state
- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- `./.venv/bin/pytest apps/api/tests/e2e/workflows/minimal/test_minimal_runtime_lane.py apps/api/tests/e2e/workflows/normal/test_normal_lane.py -q`
- `./.venv/bin/pytest apps/api/tests/integration/test_db_reset_db.py apps/api/tests/integration/test_readyz_real_db.py -q`
- `./.venv/bin/pytest -q`
- `make test-api-db`

## Outcome

- focused Phase 5A subset lanes passed (`21 passed`)
- shared registry service split passed style audit and pyright on the final integrated state
- operator MCP and public HTTP subset are both backed by the same service family
- viable minimal and normal e2e lanes passed (`2 passed`)
- reset-smoke lane passed (`2 passed`)
- broad repo-native pytest and DB-backed lane passed on the final integrated workspace state

## Artifacts Changed

- `apps/api/src/autoclaw/definitions/registry/definition_catalog.py`
- `apps/api/src/autoclaw/definitions/registry/definition_history.py`
- `apps/api/src/autoclaw/definitions/registry/task_start.py`
- `apps/api/src/autoclaw/interfaces/http/routers/definitions.py`
- `apps/api/src/autoclaw/interfaces/http/routers/tasks.py`
- `apps/api/src/autoclaw/interfaces/http/router.py`
- `docs-internal/design/v1/interfaces/api-machine-catalog.yaml`
- `docs-internal/execution/v1/phases/phase-5a-definition-ingest-api-and-cli.md`
- `docs-internal/execution/v1/maps/file-priority-map.md`
- `apps/api/src/autoclaw/definitions/contracts/**`
- `apps/api/src/autoclaw/runtime/contracts/start.py`
- `apps/api/src/autoclaw/interfaces/mcp/transport.py`
- `apps/api/src/autoclaw/interfaces/mcp/operator/server.py`
- `apps/api/src/autoclaw/interfaces/mcp/operator/**`
- `apps/api/tests/integration/public_surfaces/**`
- `apps/api/tests/unit/test_phase5a_schema_contract.py`
- `apps/api/tests/integration/mcp/`

## Residual Blockers

- broader root CLI noun-family work remains deferred to `P5A-WP2`
