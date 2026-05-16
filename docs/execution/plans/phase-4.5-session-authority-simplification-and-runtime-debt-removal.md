# Phase 4.5 Session-Authority Simplification And Runtime Debt Removal Plan

Status: Reference

selected phase: Phase 4.5
current phase page: docs/execution/phases/phase-4.5-session-authority-simplification-and-mcp-runtime-continuity-cleanup.md
selected work packages: P4.5-WP1, P4.5-WP2, P4.5-WP3
summary-only: no
delegated slices: listed
slice id: phase45-authority-and-db-truth
slice type: edit
owned surfaces: apps/api/app/runtime/**, apps/api/app/db/**, apps/api/app/schemas/**, docs/redesign/architecture/runtime-records-and-lifecycle.md, docs/redesign/architecture/runtime-database-and-object-contract.md, docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md, docs/redesign/architecture/openclaw-session-lifecycle.md, docs/redesign/architecture/watchdog-and-recovery-contract.md, docs/execution/plans/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md
touched surfaces: apps/api/app/runtime/**, apps/api/app/db/**, apps/api/app/schemas/**, docs/redesign/architecture/runtime-records-and-lifecycle.md, docs/redesign/architecture/runtime-database-and-object-contract.md, docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md, docs/redesign/architecture/openclaw-session-lifecycle.md, docs/redesign/architecture/watchdog-and-recovery-contract.md, docs/execution/plans/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md
slice id: phase45-mcp-callback-contract
slice type: edit
owned surfaces: apps/api/autoclaw/openclaw/**, apps/api/app/api/routes/callback.py, apps/api/app/runtime/control/node_operations.py, apps/api/app/runtime/control/dispatch/callbacks.py, docs/redesign/interfaces/mcp-plugin-and-cli-boundary.md, docs/redesign/interfaces/plugin-tool-reference.md, docs/redesign/interfaces/api-surface-and-trust-lane-map.md, docs/redesign/interfaces/api-schema-appendix.md
touched surfaces: apps/api/autoclaw/openclaw/**, apps/api/app/api/routes/callback.py, apps/api/app/runtime/control/node_operations.py, apps/api/app/runtime/control/dispatch/callbacks.py, docs/redesign/interfaces/mcp-plugin-and-cli-boundary.md, docs/redesign/interfaces/plugin-tool-reference.md, docs/redesign/interfaces/api-surface-and-trust-lane-map.md, docs/redesign/interfaces/api-schema-appendix.md
slice id: phase45-prompt-and-send-mode-cleanup
slice type: edit
owned surfaces: apps/api/app/runtime/prompt/**, apps/api/app/runtime/contract_models/prompt.py, apps/api/app/runtime/projection/dispatch/prompt.py, apps/api/app/runtime/task_root/writes.py, docs/redesign/prompt-layer/**, scripts/docs/prompt_catalog/**, scripts/docs/docs_freeze/content/markers_redesign.py
touched surfaces: apps/api/app/runtime/prompt/**, apps/api/app/runtime/contract_models/prompt.py, apps/api/app/runtime/projection/dispatch/prompt.py, apps/api/app/runtime/task_root/writes.py, docs/redesign/prompt-layer/**, scripts/docs/prompt_catalog/**, scripts/docs/docs_freeze/content/markers_redesign.py
slice id: phase45-watchdog-and-support-state
slice type: edit
owned surfaces: apps/api/app/runtime/watchdog/**, apps/api/app/runtime/control/observability.py, apps/api/app/runtime/projection/dispatch/materialization.py, apps/api/tests/integration/phase4b/watchdog/**, apps/api/tests/integration/phase3/routes/observability_support.py, docs/redesign/architecture/runtime-observability-and-boundary-log.md, docs/redesign/architecture/watchdog-and-provider-recovery.md, docs/redesign/how-to/debug-a-stalled-node.md, docs/redesign/how-to/recover-a-provider-session.md
touched surfaces: apps/api/app/runtime/watchdog/**, apps/api/app/runtime/control/observability.py, apps/api/app/runtime/projection/dispatch/materialization.py, apps/api/tests/integration/phase4b/watchdog/**, apps/api/tests/integration/phase3/routes/observability_support.py, docs/redesign/architecture/runtime-observability-and-boundary-log.md, docs/redesign/architecture/watchdog-and-provider-recovery.md, docs/redesign/how-to/debug-a-stalled-node.md, docs/redesign/how-to/recover-a-provider-session.md
slice id: phase45-schema-test-debt-cleanup
slice type: edit
owned surfaces: apps/api/tests/integration/runtime_schema_contract/**, apps/api/tests/integration/phase3/**, apps/api/tests/integration/phase4a/**, apps/api/tests/integration/phase4b/**, apps/api/tests/e2e/**, docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md
touched surfaces: apps/api/tests/integration/runtime_schema_contract/**, apps/api/tests/integration/phase3/**, apps/api/tests/integration/phase4a/**, apps/api/tests/integration/phase4b/**, apps/api/tests/e2e/**, docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md
slice id: phase45-review
slice type: review-only
owned surfaces: apps/api/**, docs/redesign/**, docs/execution/plans/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md, docs/execution/evidence/phase-4.5-*.md, docs/execution/reviews/phase-4.5-*.md
touched surfaces: none

## Purpose

Execute the locked Phase 4.5 target as an aggressive simplification/removal
program instead of a narrow auth patch. The implementation must collapse
authority onto `NodeSession.session_key`, preserve parent/root same-attempt
redispatch, narrow watchdog to lineage-preserving stability recovery, and
remove redundant persisted/runtime/support-state/schema/test ballast that does
not contribute to actual behavior.

## Whole-Codebase Debt Sweep Outcomes

Confirmed removal targets from repo-wide review:

- `DispatchTurn.phase` and `DISPATCH_PHASE_VALUES`
- `DispatchTurn.status` when `delivery_status` + `control_state` already own
  runtime behavior truth
- `DispatchTurn.staged_continuation_kind` when
  `staged_child_assignment_id` + boundary/release truth already define the
  live continuation basis
- `DispatchDeliveryState.send_mode`
- `DispatchDeliveryState.controller_observation_state`
- `DispatchContinuityState.previous_response_id`
- broad `DispatchContinuityState.continuity_state` catalogs beyond the narrow
  observability needed by live watchdog behavior
- `DispatchCallbackBindingModel`
- `NodeMcpBinding`
- `callback_session_key` / separate callback-token authority split
- live runtime selection of `same_session_continue`
- prompt/runtime/schema/test/support ballast that exists only to preserve the
  old hidden-binding node-MCP model

Confirmed narrow-to-observability-only targets:

- `DispatchContinuityState.session_key_present`
- `DispatchContinuityState.invalidation_reason`
- minimal continuity readback around session presence/invalidation
- `DispatchWatchdogState.recovery_action` values narrowed to
  `redispatch_same_attempt | escalate | null`

Confirmed keep targets because they still drive behavior:

- `NodeSessionModel`
- `DispatchTurn.gateway_session_key`
- `DispatchTurn.gateway_run_id`
- `DispatchTurn.control_state`
- `DispatchTurn.control_state_reason`
- `DispatchTurn.control_deadline_at`
- `DispatchTurn.abort_requested_at`
- `DispatchTurn.fenced_at`
- `DispatchWatchdogState.current_watchdog_kind`
- `DispatchWatchdogState.current_watchdog_reason`
- `DispatchWatchdogState.recovery_reason`
- `DispatchWatchdogState.recovery_dispatch_id`

## Ordered Work

1. Replace callback-binding authority with one `NodeSession.session_key` /
   Gateway `sessionKey` authority path.
   Remove hidden callback-binding authority from runtime, MCP wrapper, and
   callback HTTP write validation.
2. Land explicit-arg `node MCP` and callback parity on the shared semantic
   node-operation service.
   `session_key + task_id` become the public node/callback semantic contract;
   `dispatch_id`, callback-binding ids, and hidden wrapper authority disappear.
3. Preserve parent/root same-attempt redispatch with same session and fresh
   run while removing non-live continuation plumbing.
   Live controller path emits `full_prompt` only; `same_session_continue`,
   `previous_response_id`, and persisted send-mode branching are removed or
   demoted to current/debt compatibility only until fully deleted.
4. Narrow watchdog to lineage-preserving stability recovery only.
   Automatic watchdog recovery becomes `redispatch_same_attempt | escalate`;
   watchdog no longer auto-mints a new attempt and never consumes authored
   retry budget.
5. Remove redundant persisted/runtime/support-state fields that do not drive
   behavior.
   This includes dispatch `phase`, dispatch `status` if it remains only a
   shadow, `staged_continuation_kind`, support `send_mode`,
   support-side observation mirrors, and broad continuity-state catalogs.
6. Delete or rewrite schema/test/support fixtures that still freeze the old
   hidden-binding model as contract truth.
   Runtime schema contract tests, phase3/4 helpers, e2e supports, and MCP
   tests must align to the simplified authority/runtime model.

## Validation

- Python gates on touched backend surfaces:
  - `ruff format`
  - `ruff check`
  - `mypy`
  - `make pyright-api`
  - `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
- Docs/prompt validators when prompt/docs surfaces change:
  - `./.venv/bin/python -m scripts.docs.prompt_catalog.cli generate`
  - `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate`
  - `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- Focused behavior tests:
  - callback/node-MCP explicit-arg validation tests
  - parent/root same-session redispatch tests
  - watchdog same-attempt redispatch versus escalation tests
  - observability/support-state shape tests after continuity/send-mode
    narrowing
- Broad proof:
  - `pytest`
  - viable minimal, normal, and maximal e2e lanes
  - Docker/Postgres verification when runtime persistence truth changes

## Stop conditions

- stop if code outside the owned or allowed-collateral surfaces becomes
  necessary to land the simplification
- stop if removing a candidate debt family would change actual behavior rather
  than removing inert or duplicated state
- stop if any recovery or continuity choice would require reopening canon
  beyond the locked Phase 4.5 direction
