# Phase 4B Watchdog, Operator MCP, Node MCP, And Support-State Implementation Plan

Status: Reference

selected phase: Phase 4B
current phase page: docs/execution/phases/phase-4b-watchdog-operator-plugin-and-support-state.md
selected work packages: P4B-WP1, P4B-WP2, P4B-WP3
summary-only: no
delegated slices: listed
slice id: phase4b-watchdog-runtime-loop
slice type: edit
owned surfaces: apps/api/app/runtime/watchdog/**, apps/api/app/config.py, apps/api/app/main.py, apps/api/tests/integration/phase4b/watchdog/**, docs/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md
touched surfaces: apps/api/app/runtime/watchdog/service.py, apps/api/app/runtime/watchdog/recovery.py, apps/api/app/runtime/watchdog/classification.py, apps/api/tests/integration/phase4b/watchdog/support.py, apps/api/tests/integration/phase4b/watchdog/case_support.py, apps/api/tests/integration/phase4b/watchdog/test_recovery_actions.py, apps/api/tests/integration/phase4b/watchdog/test_stale_classification.py, apps/api/tests/integration/phase4b/watchdog/test_foreground_guards.py, docs/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md
slice id: phase4b-operator-mcp-wrapper
slice type: edit
owned surfaces: apps/api/autoclaw/openclaw/common.py, apps/api/autoclaw/openclaw/operator_server.py, apps/api/app/runtime/effects/writes.py, apps/api/tests/integration/phase4b/mcp/test_operator_server.py, apps/api/tests/integration/phase4b/mcp/support.py, docs/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md
touched surfaces: apps/api/autoclaw/openclaw/common.py, apps/api/autoclaw/openclaw/operator_server.py, apps/api/app/runtime/effects/writes.py, apps/api/tests/integration/phase4b/mcp/test_operator_server.py, apps/api/tests/integration/phase4b/mcp/support.py, docs/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md
slice id: phase4b-node-mcp-wrapper
slice type: edit
owned surfaces: apps/api/autoclaw/openclaw/node_server.py, apps/api/autoclaw/openclaw/bindings.py, apps/api/app/runtime/control/node_operations.py, apps/api/tests/integration/phase4b/mcp/test_node_server.py, apps/api/tests/integration/phase4b/mcp/support.py, docs/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md
touched surfaces: apps/api/autoclaw/openclaw/node_server.py, apps/api/autoclaw/openclaw/bindings.py, apps/api/app/runtime/control/node_operations.py, apps/api/tests/integration/phase4b/mcp/test_node_server.py, apps/api/tests/integration/phase4b/mcp/support.py, docs/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md
slice id: phase4b-review
slice type: review-only
owned surfaces: apps/api/app/runtime/watchdog/**, apps/api/autoclaw/openclaw/**, apps/api/app/runtime/effects/writes.py, apps/api/app/runtime/control/node_operations.py, apps/api/tests/integration/phase4b/**, docs/execution/plans/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md, docs/execution/evidence/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md, docs/execution/reviews/phase-4b-watchdog-operator-node-mcp-support-state-implementation.md
touched surfaces: none

## Phase-local contract

- purpose: land real watchdog recovery, operator/node MCP parity over shared runtime/service seams, and support-state freeze without widening into Phase 5A public noun ownership
- success criteria:
  - watchdog recovery executes, not just classifies
  - `operator MCP` and `node MCP` use the shared controller-owned write boundary and stay transport-thin
  - `delivery-state.json`, `continuity-state.json`, `watchdog-state.json`,
    and `provider-events.ndjson` stay support-only and projection-backed
  - package/profile attachment proof is explicit when viable

## Ordered work

### `P4B-WP1`

- implement real watchdog recovery execution
- protect foreground-owned slots before watchdog classification families attach
- keep `recovery_dispatch_id` and watchdog readbacks truthful

### `P4B-WP2`

- unify operator MCP writes with the shared runtime write boundary
- move node MCP onto the shared Phase 3 node-operation seam
- keep operator/node surfaces transport-thin and inventory-bounded

### `P4B-WP3`

- strengthen node/operator-facing support-state and readback proof for
  `delivery-state.json`, `continuity-state.json`, `watchdog-state.json`, and
  `provider-events.ndjson`
- leave runtime-effective `tools.effective` / security-audit proof to the final QA wave when viable

## Validation checkpoints

- after `P4B-WP1`:
  - watchdog recovery tests green
  - foreground-slot skip behavior green
- after `P4B-WP2`:
  - operator MCP mutating tool proof green
  - node MCP shared-seam proof green
- after `P4B-WP3`:
  - integrated `apps/api/tests/integration/phase4b` lane green
- closeout:
  - live `tools.effective` or equivalent profile/session proof
  - `openclaw security audit --deep` when the wrapper/profile tree lands
  - full local `pytest`
  - `make test-api-db`

## 2026-05-14 repair slice

- scope:
  - make `node MCP` reuse callback authority for revoked-binding, paused,
    cancel, and same-dispatch stale writes
  - align `operator MCP` tool arguments from `q` to `query`
  - keep `call_parent_tool.expected_structural_revision_id` top-level on
    `node MCP`
  - make watchdog execution-stale timing ignore raw provider-signal churn
- landed proof:
  - focused schema checks for `operator MCP` and `node MCP`
  - focused stale-authority regression checks for `node MCP`
  - focused watchdog stale-classification regression check for
    provider-signal-only motion
  - integrated rerun of the targeted Phase 4B MCP/watchdog suites
- remaining closeout blockers outside this slice:
  - live `tools.effective` or equivalent runtime inventory proof
  - `openclaw security audit --deep`
  - exact support-state freeze proof for `delivery-state.json`,
    `continuity-state.json`, `watchdog-state.json`, and
    `provider-events.ndjson`
  - any still-required phase-closeout gates not rerun in this slice,
    including `make pyright-api`, style-audit proof, and reset-gate proof

## Test budget and stop conditions

- each edit slice runs only one narrow owned-slice batch once
- do not rerun an identical broad lane if a prior wave already passed it
- stop and route to Phase 5A if a requested MCP tool requires `/definitions` or `/tasks/start` ownership
- stop if support-state files or wrapper state start acting like controller truth

## Delegated slice briefs

### phase4b-watchdog-runtime-loop

- do-not-edit surfaces:
  - `apps/api/autoclaw/**`
  - docs/**
- required reads:
  - all Phase 4B mandatory docs listed in the header block
  - merged Phase 4A lifecycle/transport surfaces
  - current watchdog tests and runtime rows
- required validators:
  - `./.venv/bin/ruff check apps/api/app/runtime/watchdog apps/api/tests/integration/phase4b/watchdog`
  - `./.venv/bin/mypy apps/api/app/runtime/watchdog apps/api/tests/integration/phase4b/watchdog`
  - `./.venv/bin/pytest -q apps/api/tests/integration/phase4b/watchdog`
- expected outputs:
  - real watchdog recovery execution
  - classification ordering that protects foreground-owned slots
- dependencies:
  - Phase 4A integrated and green
- evidence to return:
  - changed file list
  - narrow validator/test outputs
- parent-owned decisions:
  - final runtime-effective proof and closure status
- stop conditions:
  - any need for operator/node wrapper ownership or public API/CLI widening

### phase4b-operator-mcp-wrapper

- do-not-edit surfaces:
  - `apps/api/autoclaw/openclaw/node_server.py`
  - `apps/api/autoclaw/openclaw/bindings.py`
  - `apps/api/app/runtime/watchdog/**`
  - docs/**
- required reads:
  - all Phase 4B mandatory docs listed in the header block
  - Phase 3 shared runtime write seam and callback/node-operation seam for context
  - current operator MCP tests
- required validators:
  - `./.venv/bin/ruff check apps/api/autoclaw/openclaw/common.py apps/api/autoclaw/openclaw/operator_server.py apps/api/app/runtime/effects/writes.py apps/api/tests/integration/phase4b/mcp/test_operator_server.py apps/api/tests/integration/phase4b/mcp/support.py`
  - `./.venv/bin/mypy apps/api/autoclaw/openclaw/common.py apps/api/autoclaw/openclaw/operator_server.py apps/api/app/runtime/effects/writes.py apps/api/tests/integration/phase4b/mcp/test_operator_server.py apps/api/tests/integration/phase4b/mcp/support.py`
  - `./.venv/bin/pytest -q apps/api/tests/integration/phase4b/mcp/test_operator_server.py`
- expected outputs:
  - operator MCP writes use the shared controller-owned runtime write boundary
  - operator-side proof shows lifecycle/effect wakeups, not DB-only mutation
- dependencies:
  - Phase 4A integrated and green
- evidence to return:
  - changed file list
  - narrow validator/test outputs
- parent-owned decisions:
  - final profile/session proof and closure status
- stop conditions:
  - any need for node-server or redesign-doc ownership

### phase4b-node-mcp-wrapper

- do-not-edit surfaces:
  - `apps/api/autoclaw/openclaw/common.py`
  - `apps/api/autoclaw/openclaw/operator_server.py`
  - `apps/api/app/runtime/watchdog/**`
  - docs/**
- required reads:
  - all Phase 4B mandatory docs listed in the header block
  - the integrated Phase 3 shared node-operation seam
  - current node MCP tests
- required validators:
  - `./.venv/bin/ruff check apps/api/autoclaw/openclaw/node_server.py apps/api/autoclaw/openclaw/bindings.py apps/api/app/runtime/control/node_operations.py apps/api/tests/integration/phase4b/mcp/test_node_server.py apps/api/tests/integration/phase4b/mcp/support.py`
  - `./.venv/bin/mypy apps/api/autoclaw/openclaw/node_server.py apps/api/autoclaw/openclaw/bindings.py apps/api/app/runtime/control/node_operations.py apps/api/tests/integration/phase4b/mcp/test_node_server.py apps/api/tests/integration/phase4b/mcp/support.py`
  - `./.venv/bin/pytest -q apps/api/tests/integration/phase4b/mcp/test_node_server.py`
- expected outputs:
  - node MCP uses the shared node-operation seam
  - node-facing proof checks behavior and stale-binding rejection
- dependencies:
  - Phase 4A integrated and green
  - Phase 3 shared node-operation seam integrated
- evidence to return:
  - changed file list
  - narrow validator/test outputs
- parent-owned decisions:
  - final support-state freeze and closure status
- stop conditions:
  - any need for operator-server or redesign-doc ownership

### phase4b-review

- do-not-edit surfaces:
  - all repo-tracked files
- required reads:
  - all Phase 4B mandatory docs listed in the header block
  - merged watchdog/MCP/support-state changes
  - touched Phase 4B tests
- required validators:
  - inspect delegated edit-slice proof and run only narrow spot-checks if needed
  - do not run full pytest or make test-api-db
- expected outputs:
  - independent findings and verdict
  - draft review artifact content for the matching Phase 4B review file
- dependencies:
  - `phase4b-watchdog-runtime-loop`
  - `phase4b-operator-mcp-wrapper`
  - `phase4b-node-mcp-wrapper`
- evidence to return:
  - findings with exact refs
  - draft review artifact content
- parent-owned decisions:
  - final profile/security proof, final evidence transcription, and final closure status
- stop conditions:
  - stop if proving a finding requires broad full-suite validation or redesign-doc ownership
