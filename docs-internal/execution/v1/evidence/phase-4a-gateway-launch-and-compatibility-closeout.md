# Phase 4A Gateway Launch And Compatibility Closeout Evidence

Status: Reference

selected phase: Phase 4A
current phase page: docs-internal/execution/v1/phases/phase-4a-openclaw-gateway-session-and-continuity.md
selected work packages: P4A-WP1, P4A-WP2
summary-only: no
delegated slices: listed
slice id: phase4a-launch-taxonomy
slice type: edit
owned surfaces: apps/api/src/autoclaw/runtime/dispatch/**, apps/api/tests/integration/phase4a/**
touched surfaces: apps/api/src/autoclaw/runtime/dispatch/gateway/__init__.py, apps/api/tests/integration/phase4a/runtime_dispatch_gateway/test_launch_integration.py
slice id: phase4a-compatibility-pin
slice type: edit
owned surfaces: apps/api/src/autoclaw/integrations/openclaw/gateway/**, apps/api/tests/integration/phase4a/**, docs-internal/design/v1/architecture/openclaw-gateway-rpc-subset.md
touched surfaces: apps/api/src/autoclaw/integrations/openclaw/gateway/**, apps/api/tests/integration/phase4a/**, docs-internal/design/v1/architecture/openclaw-gateway-rpc-subset.md
slice id: phase4a-review
slice type: review-only
owned surfaces: apps/api/src/autoclaw/runtime/dispatch/**, apps/api/src/autoclaw/integrations/openclaw/gateway/**, apps/api/tests/integration/phase4a/**, docs-internal/design/v1/architecture/openclaw-gateway-rpc-subset.md, docs-internal/execution/v1/plans/phase-4a-gateway-launch-and-compatibility-closeout.md, docs-internal/execution/v1/evidence/phase-4a-gateway-launch-and-compatibility-closeout.md, docs-internal/execution/v1/reviews/phase-4a-gateway-launch-and-compatibility-closeout.md
touched surfaces: none

## Plan and review links

- approved plan: `../plans/phase-4a-gateway-launch-and-compatibility-closeout.md`
- mandatory review: `../reviews/phase-4a-gateway-launch-and-compatibility-closeout.md`
- review artifact: `../reviews/phase-4a-gateway-launch-and-compatibility-closeout.md`

## Commands Run

- `./.venv/bin/pytest apps/api/tests/integration/phase4a/test_openclaw_gateway_adapter.py apps/api/tests/integration/phase4a/test_openclaw_gateway_compatibility.py apps/api/tests/integration/phase4a/runtime_dispatch_gateway/test_launch_integration.py -q`
- `./.venv/bin/ruff check apps/api/src/autoclaw/runtime/dispatch/gateway apps/api/src/autoclaw/integrations/openclaw/gateway/request_builders.py apps/api/src/autoclaw/integrations/openclaw/gateway/fixtures.py apps/api/tests/integration/phase4a/test_openclaw_gateway_adapter.py apps/api/tests/integration/phase4a/test_openclaw_gateway_compatibility.py apps/api/tests/integration/phase4a/runtime_dispatch_gateway/test_launch_integration.py`
- `./.venv/bin/mypy apps/api/src/autoclaw/runtime/dispatch/gateway apps/api/src/autoclaw/integrations/openclaw/gateway/protocol.py apps/api/src/autoclaw/integrations/openclaw/gateway/request_builders.py apps/api/src/autoclaw/integrations/openclaw/gateway/fixtures.py apps/api/tests/integration/phase4a/test_openclaw_gateway_adapter.py apps/api/tests/integration/phase4a/test_openclaw_gateway_compatibility.py apps/api/tests/integration/phase4a/runtime_dispatch_gateway/test_launch_integration.py`
- `make pyright-api`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
- `./.venv/bin/pytest -q`
- `make test-api-db`
- live compatibility probe via `adapter.check_compatibility()`
- live machine-control proof via `launch_run -> abort_run -> wait_for_run`

## Outcome

- focused Phase 4A lane passed
- live compatibility probe passed on protocol `4`
- live machine-control proof passed against the installed gateway
- repo-native typing, audit, and broad pytest lanes passed on the final integrated workspace state
- Phase 4A remains the owner for transport-boundary compaction such as single-point session-key normalization, smaller wire-facing launch input, and removal of request-local `observed_events` ballast from the live Gateway call path

## Artifacts Changed

- `apps/api/src/autoclaw/runtime/dispatch/gateway/__init__.py`
- `apps/api/src/autoclaw/integrations/openclaw/gateway/protocol.py`
- `apps/api/src/autoclaw/integrations/openclaw/gateway/request_builders.py`
- `apps/api/src/autoclaw/integrations/openclaw/gateway/fixtures.py`
- `apps/api/tests/integration/phase4a/test_openclaw_gateway_adapter.py`
- `apps/api/tests/integration/phase4a/test_openclaw_gateway_compatibility.py`
- `apps/api/tests/integration/phase4a/runtime_dispatch_gateway/test_launch_integration.py`
- `docs-internal/design/v1/architecture/openclaw-gateway-rpc-subset.md`

## Residual Blockers

- local config token drift remains environment-scoped but does not block the bounded loopback retry path on this host
