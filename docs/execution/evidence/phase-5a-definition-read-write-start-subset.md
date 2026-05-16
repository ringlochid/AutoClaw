# Phase 5A Definition Read Write Start Subset Evidence

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
owned surfaces: apps/api/autoclaw/openclaw/operator_server.py, apps/api/autoclaw/openclaw/common.py, apps/api/autoclaw/openclaw/operator_mcp/**, apps/api/tests/integration/phase4b/mcp/test_operator_server.py, apps/api/tests/integration/phase5a/mcp/**
touched surfaces: apps/api/autoclaw/openclaw/operator_server.py, apps/api/autoclaw/openclaw/common.py, apps/api/autoclaw/openclaw/operator_mcp/**, apps/api/tests/integration/phase4b/mcp/test_operator_server.py, apps/api/tests/integration/phase5a/mcp/**
slice id: phase5a-schema-contract
slice type: edit
owned surfaces: apps/api/app/schemas/definitions/**, apps/api/app/schemas/runtime/**, apps/api/tests/unit/test_phase5a_schema_contract.py
touched surfaces: apps/api/app/schemas/definitions/**, apps/api/app/schemas/runtime/**, apps/api/tests/unit/test_phase5a_schema_contract.py
slice id: phase5a-review
slice type: review-only
owned surfaces: apps/api/app/registry/**, apps/api/app/api/routes/**, apps/api/autoclaw/openclaw/operator_server.py, apps/api/app/schemas/**, apps/api/tests/integration/phase5a/**, apps/api/tests/unit/test_phase5a_schema_contract.py, docs/execution/plans/phase-5a-definition-read-write-start-subset.md, docs/execution/evidence/phase-5a-definition-read-write-start-subset.md, docs/execution/reviews/phase-5a-definition-read-write-start-subset.md
touched surfaces: none

## Plan and review links

- approved plan: `../plans/phase-5a-definition-read-write-start-subset.md`
- mandatory review: `../reviews/phase-5a-definition-read-write-start-subset.md`
- review artifact: `../reviews/phase-5a-definition-read-write-start-subset.md`

## Commands Run

- `./.venv/bin/pytest apps/api/tests/unit/test_phase5a_schema_contract.py apps/api/tests/integration/phase5a/test_public_http_subset.py apps/api/tests/integration/phase5a/mcp/test_operator_server_phase5a.py apps/api/tests/integration/phase4b/mcp/test_operator_server.py -q`
- `./.venv/bin/ruff check apps/api/app/registry/** apps/api/app/api/routes/definitions.py apps/api/app/api/routes/tasks.py apps/api/app/api/router.py apps/api/autoclaw/openclaw/common.py apps/api/autoclaw/openclaw/operator_server.py apps/api/autoclaw/openclaw/operator_mcp apps/api/app/schemas/definitions/** apps/api/app/schemas/runtime/** apps/api/tests/integration/phase5a/** apps/api/tests/unit/test_phase5a_schema_contract.py apps/api/tests/integration/phase4b/mcp/test_operator_server.py`
- `make pyright-api` on the final integrated state
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings` on the final integrated state
- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- `./.venv/bin/pytest apps/api/tests/e2e/phase2/test_minimal_runtime_lane.py apps/api/tests/e2e/phase3/normal_lane/test_normal_lane.py -q`
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

- `apps/api/app/registry/definition_catalog.py`
- `apps/api/app/registry/definition_history.py`
- `apps/api/app/registry/task_start.py`
- `apps/api/app/api/routes/definitions.py`
- `apps/api/app/api/routes/tasks.py`
- `apps/api/app/api/router.py`
- `docs/redesign/interfaces/api-machine-catalog.yaml`
- `docs/execution/phases/phase-5a-definition-ingest-api-and-cli.md`
- `docs/execution/maps/file-priority-map.md`
- `apps/api/app/schemas/definitions/**`
- `apps/api/app/schemas/runtime/start.py`
- `apps/api/autoclaw/openclaw/common.py`
- `apps/api/autoclaw/openclaw/operator_server.py`
- `apps/api/autoclaw/openclaw/operator_mcp/**`
- `apps/api/tests/integration/phase5a/**`
- `apps/api/tests/unit/test_phase5a_schema_contract.py`
- `apps/api/tests/integration/phase4b/mcp/test_operator_server.py`

## Residual Blockers

- broader root CLI noun-family work remains deferred to `P5A-WP2`
