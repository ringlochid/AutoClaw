# Phase 4B Session Bound Node MCP And Support State Closeout Plan

Status: Reference

selected phase: Phase 4B
current phase page: docs/execution/phases/phase-4b-watchdog-operator-plugin-and-support-state.md
selected work packages: P4B-WP1, P4B-WP2, P4B-WP3
summary-only: no
delegated slices: listed
slice id: phase4b-docs-and-support-freeze
slice type: edit
owned surfaces: docs/redesign/interfaces/mcp-plugin-and-cli-boundary.md, docs/redesign/interfaces/plugin-tool-reference.md, docs/redesign/interfaces/human-and-operator-control-surface.md, docs/redesign/interfaces/api-surface-and-trust-lane-map.md, docs/redesign/architecture/openclaw-worker-and-gateway-contract.md, docs/redesign/architecture/runtime-observability-and-boundary-log.md, docs/redesign/architecture/watchdog-and-recovery-contract.md, docs/execution/phases/phase-4b-watchdog-operator-plugin-and-support-state.md, docs/execution/maps/file-priority-map.md
touched surfaces: docs/redesign/interfaces/mcp-plugin-and-cli-boundary.md, docs/redesign/interfaces/plugin-tool-reference.md, docs/redesign/interfaces/human-and-operator-control-surface.md, docs/redesign/interfaces/api-surface-and-trust-lane-map.md, docs/redesign/architecture/openclaw-worker-and-gateway-contract.md, docs/redesign/architecture/runtime-observability-and-boundary-log.md, docs/redesign/architecture/watchdog-and-recovery-contract.md, docs/execution/phases/phase-4b-watchdog-operator-plugin-and-support-state.md, docs/execution/maps/file-priority-map.md
slice id: phase4b-node-session-bound-ingress
slice type: edit
owned surfaces: apps/api/autoclaw/openclaw/__init__.py, apps/api/autoclaw/openclaw/common.py, apps/api/autoclaw/openclaw/operator_server.py, apps/api/autoclaw/openclaw/bindings.py, apps/api/autoclaw/openclaw/node_server.py, apps/api/tests/integration/phase4b/mcp/support.py, apps/api/tests/integration/phase4b/mcp/test_node_server.py, apps/api/tests/integration/phase4b/mcp/test_main_app_mcp_mounts.py, apps/api/tests/integration/phase4b/mcp/test_operator_server.py
touched surfaces: apps/api/autoclaw/openclaw/__init__.py, apps/api/autoclaw/openclaw/common.py, apps/api/autoclaw/openclaw/operator_server.py, apps/api/autoclaw/openclaw/bindings.py, apps/api/autoclaw/openclaw/node_server.py, apps/api/tests/integration/phase4b/mcp/support.py, apps/api/tests/integration/phase4b/mcp/test_node_server.py, apps/api/tests/integration/phase4b/mcp/test_main_app_mcp_mounts.py, apps/api/tests/integration/phase4b/mcp/test_operator_server.py
slice id: phase4b-watchdog-reconciliation
slice type: edit
owned surfaces: apps/api/app/runtime/watchdog/**, apps/api/tests/integration/phase4b/watchdog/**
touched surfaces: apps/api/app/runtime/watchdog/classification.py, apps/api/app/runtime/watchdog/service.py, apps/api/tests/integration/phase4b/watchdog/test_recovery_actions.py, apps/api/tests/integration/phase4b/watchdog/test_stale_classification.py, apps/api/tests/integration/phase4b/watchdog/test_foreground_guards.py
slice id: phase4b-review
slice type: review-only
owned surfaces: apps/api/autoclaw/openclaw/**, apps/api/app/runtime/watchdog/**, apps/api/tests/integration/phase4b/**, docs/execution/plans/phase-4b-session-bound-node-mcp-and-support-state-closeout.md, docs/execution/evidence/phase-4b-session-bound-node-mcp-and-support-state-closeout.md, docs/execution/reviews/phase-4b-session-bound-node-mcp-and-support-state-closeout.md
touched surfaces: none

## Goal

Close the remaining Phase 4B gaps:

- mounted node MCP must be session-bound, not operator bearer + `task_id`
- node MCP gets current-only definition lookup
- support-state freeze includes exact `provider-events.ndjson`
- watchdog runtime matches the frozen trigger-family set

## Ordered Work

1. Patch the Phase 4B trust/support docs first.
2. Replace the mounted node ingress with session-bound lookup plus optional task consistency checks.
3. Add current-only `search_definitions` / `get_definition` to the node lane.
4. Reconcile the watchdog trigger-family runtime implementation and tests.

## Validation

- focused node MCP mount/auth/inventory tests
- focused watchdog tests
- live feasible operator/node MCP proof on the current repo state

## Delegated Slice Briefs

### phase4b-docs-and-support-freeze

- do-not-edit surfaces:
  - app code and tests
  - execution evidence/reviews
- required reads:
  - Phase 4B page, trust-lane docs, support-state docs, watchdog docs
- expected outputs:
  - session-bound node MCP canon
  - exact four-file support-state docs freeze
- required validators:
  - docs validators in the parent integration loop
- dependencies:
  - selected node/session-bound design fixed
- parent-owned decisions:
  - exact node current-only lookup boundary
  - exact support-state freeze wording
- evidence to return:
  - changed file list
  - doc decisions made
- stop conditions:
  - if code/test changes are required

### phase4b-node-session-bound-ingress

- do-not-edit surfaces:
  - operator MCP code
  - public API/CLI
  - docs and execution artifacts
- required reads:
  - Phase 4B page, node/callback trust docs, current node server/binding/tests, shared definition service
- expected outputs:
  - session-bound mounted ingress
  - current-only `role` / `policy` lookup on node MCP
- required validators:
  - focused node MCP mount/auth/inventory tests
- dependencies:
  - shared definition service available
- parent-owned decisions:
  - primary session binding key
  - whether optional task consistency remains allowed
- evidence to return:
  - changed file list
  - focused command outcomes
- stop conditions:
  - if docs or broader operator surfaces need changes

### phase4b-watchdog-reconciliation

- do-not-edit surfaces:
  - MCP surfaces
  - docs and execution artifacts
- required reads:
  - Phase 4B page, watchdog contract docs, runtime watchdog code/tests
- expected outputs:
  - runtime trigger-family implementation aligned to canon
- required validators:
  - focused watchdog tests
- dependencies:
  - docs freeze of trigger-family set complete
- parent-owned decisions:
  - interpretation of rebound and first-callback trigger boundaries
- evidence to return:
  - changed file list
  - focused command outcomes
- stop conditions:
  - if canon is too underspecified to implement safely

### phase4b-review

- do-not-edit surfaces:
  - all repo-tracked files
- required reads:
  - Phase 4B page, plan, evidence, touched code/tests/docs
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

- mounted node ingress is session-bound
- node current-only lookup tools are live
- watchdog kinds match canon
- support-state docs explicitly freeze all four readbacks
