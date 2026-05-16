# Phase 4.5 Session-Authority Simplification And Runtime Debt Removal Plan

Status: Reference

selected phase: Phase 4.5
current phase page: docs/execution/phases/phase-4.5-session-authority-simplification-and-mcp-runtime-continuity-cleanup.md
selected work packages: P4.5-WP1, P4.5-WP2, P4.5-WP3, P4.5-WP4, P4.5-WP5, P4.5-WP6
summary-only: no
delegated slices: listed
slice id: phase45-docs-execution
slice type: edit
owned surfaces: docs/execution/**, docs/redesign/prompt-layer/**, docs/redesign/prompt-layer/generated/*, docs/redesign/prompt-layer/prompt-catalog.yaml, docs/current/interfaces/api-trust-lanes.md, docs/current/architecture/openclaw-dispatch-and-session-contract.md, docs/current/architecture/runtime-control-plane.md
touched surfaces: docs/execution/**, docs/redesign/prompt-layer/**, docs/redesign/prompt-layer/generated/*, docs/redesign/prompt-layer/prompt-catalog.yaml, docs/current/interfaces/api-trust-lanes.md, docs/current/architecture/openclaw-dispatch-and-session-contract.md, docs/current/architecture/runtime-control-plane.md
slice id: phase45-authority-runtime-db
slice type: edit
owned surfaces: apps/api/app/runtime/**, apps/api/app/db/**, apps/api/app/schemas/**, apps/api/tests/integration/phase3/**, apps/api/tests/integration/phase4a/**, apps/api/tests/integration/runtime_schema_contract/**, docs/redesign/architecture/runtime-records-and-lifecycle.md, docs/redesign/architecture/runtime-database-and-object-contract.md, docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md, docs/redesign/architecture/openclaw-session-lifecycle.md
touched surfaces: apps/api/app/runtime/**, apps/api/app/db/**, apps/api/app/schemas/**, apps/api/tests/integration/phase3/**, apps/api/tests/integration/phase4a/**, apps/api/tests/integration/runtime_schema_contract/**, docs/redesign/architecture/runtime-records-and-lifecycle.md, docs/redesign/architecture/runtime-database-and-object-contract.md, docs/redesign/architecture/runtime-boundary-and-controller-loop-contract.md, docs/redesign/architecture/openclaw-session-lifecycle.md
slice id: phase45-node-mcp-callback
slice type: edit
owned surfaces: apps/api/autoclaw/openclaw/**, apps/api/app/api/routes/callback.py, apps/api/app/runtime/control/node_operations.py, apps/api/app/runtime/control/dispatch/callbacks.py, apps/api/tests/integration/phase4b/mcp/**, docs/redesign/interfaces/mcp-plugin-and-cli-boundary.md, docs/redesign/interfaces/plugin-tool-reference.md, docs/redesign/interfaces/api-surface-and-trust-lane-map.md, docs/redesign/interfaces/api-schema-appendix.md
touched surfaces: apps/api/autoclaw/openclaw/**, apps/api/app/api/routes/callback.py, apps/api/app/runtime/control/node_operations.py, apps/api/app/runtime/control/dispatch/callbacks.py, apps/api/tests/integration/phase4b/mcp/**, docs/redesign/interfaces/mcp-plugin-and-cli-boundary.md, docs/redesign/interfaces/plugin-tool-reference.md, docs/redesign/interfaces/api-surface-and-trust-lane-map.md, docs/redesign/interfaces/api-schema-appendix.md
slice id: phase45-watchdog-observability
slice type: edit
owned surfaces: apps/api/app/runtime/watchdog/**, apps/api/app/runtime/projection/**, apps/api/tests/integration/phase4b/**, apps/api/tests/integration/runtime_schema_contract/**, apps/api/tests/e2e/**, docs/redesign/architecture/runtime-observability-and-boundary-log.md, docs/redesign/architecture/watchdog-and-provider-recovery.md, docs/current/architecture/runtime-control-plane.md
touched surfaces: apps/api/app/runtime/watchdog/**, apps/api/app/runtime/projection/**, apps/api/tests/integration/phase4b/**, apps/api/tests/integration/runtime_schema_contract/**, apps/api/tests/e2e/**, docs/redesign/architecture/runtime-observability-and-boundary-log.md, docs/redesign/architecture/watchdog-and-provider-recovery.md, docs/current/architecture/runtime-control-plane.md
slice id: phase45-prompt-runtime-assets
slice type: edit
owned surfaces: apps/api/app/runtime/prompt/**, apps/api/app/runtime/contract_models/**, apps/api/app/runtime/projection/dispatch/prompt.py, apps/api/app/runtime/task_root/**, apps/api/tests/unit/runtime_prompt_rendering/**, apps/api/tests/integration/phase3/**, docs/redesign/prompt-layer/**, docs/redesign/prompt-layer/generated/*, docs/redesign/prompt-layer/prompt-catalog.yaml
touched surfaces: apps/api/app/runtime/prompt/**, apps/api/app/runtime/contract_models/**, apps/api/app/runtime/projection/dispatch/prompt.py, apps/api/app/runtime/task_root/**, apps/api/tests/unit/runtime_prompt_rendering/**, apps/api/tests/integration/phase3/**, docs/redesign/prompt-layer/**, docs/redesign/prompt-layer/generated/*, docs/redesign/prompt-layer/prompt-catalog.yaml
slice id: phase45-qa-gate-review
slice type: review-only
owned surfaces: apps/api/**, docs/redesign/**, docs/current/**, docs/execution/plans/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md, docs/execution/evidence/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md
touched surfaces: none
slice id: phase45-strict-closeout-review
slice type: edit
owned surfaces: docs/execution/reviews/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md
touched surfaces: docs/execution/reviews/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md

## Master-program alignment

- summary-only master orchestration: `docs/execution/plans/phase-0-to-4.5-make-it-work-master-program.md`
- authoritative Phase 0 addendum prerequisite: `docs/execution/plans/phase-0-phase45-execution-unblock-canon-fix.md`
- final closure authority remains the Phase 4.5 plan, evidence, and review triplet rather than the master-program summary or the Phase 0 addendum

## Slice identity

- owner: parent-integrated delegated slices
- date: 2026-05-16
- work package or slice: Phase 4.5 make-it-work closure after the Phase 0 execution-unblock addendum

## Subagents decision

- delegated slices: run one docs-first edit slice, three Wave 1 code slices, one Wave 2 prompt/runtime edit slice, one Wave 3 review-only QA slice, and one Wave 4 strict closeout review edit slice

## Wave integration rule

- parent no-edit during wave: yes
- full-wave wait rule: yes
- ownership-boundary and slice-type review: required after every wave
- revert rule for out-of-scope or review-only edits: required before integration
- validation and review before next wave: required

## Goal

- phase-local goal: make the simplified authority, explicit-arg node MCP, same-session redispatch, prompt cleanup, watchdog narrowing, redundant-state deletion, and proof lanes work in code and runtime rather than only in docs

## Phase-local contract

- current phase page: `docs/execution/phases/phase-4.5-session-authority-simplification-and-mcp-runtime-continuity-cleanup.md`
- implementation file lock map: `docs/execution/maps/file-priority-map.md`
- required reads completed: Phase 4.5 page, lock map, landing map, mandatory review gate, reset gate, prior Phase 0 canon-fix plan, prior Phase 4.5 plan, and the master-program packet

## Locked surfaces

- owned surfaces: `apps/api/app/runtime/**`, `apps/api/app/db/**`, `apps/api/app/schemas/**`, `apps/api/autoclaw/openclaw/**`, touched Phase 3/4A/4B/runtime-schema/e2e/prompt proof surfaces under `apps/api/tests/**`, prompt owner docs plus generated prompt docs and prompt-catalog inputs, exact redesign/current doc collateral reopened by the phase page, and the selected Phase 4.5 execution artifacts
- allowed collateral surfaces: `apps/api/app/main.py`, `apps/api/app/config.py`, exact current-contrast repair, and the final strict closeout review artifact only
- do not edit or defer surfaces: Phase 5A public noun-family work, Phase 5B packaging/release/install work beyond proof-harness support, and unrelated registry/frontend/plugin work

## Whole-codebase deletion targets

- `DispatchCallbackBindingModel`
- `NodeMcpBinding`
- callback-session-key and hidden-binding authority split
- live runtime selection of `same_session_continue`
- live dependence on `previous_response_id`
- `DispatchTurn.phase`
- `DispatchTurn.send_mode`
- `DispatchTurn.status`
- `DispatchTurn.staged_continuation_kind`
- `DispatchDeliveryState.controller_observation_state`
- `DispatchDeliveryState.send_mode`
- broad `DispatchContinuityState.continuity_state` catalogs beyond narrow observability that still explains behavior
- prompt/runtime/schema/test/support ballast that exists only to preserve the old hidden-binding model

## Success criteria

- callback HTTP and node MCP both resolve authority from `NodeSession.session_key` plus task/currentness truth
- callback-binding authority is gone as live runtime truth
- hidden node binding is gone as live runtime truth
- parent/root same-attempt redispatch keeps the same `sessionKey`, gets a fresh `runId`, sends a fresh `idempotencyKey`, and emits `full_prompt`
- worker retry and semantic new-attempt flows remain fresh-session
- watchdog automatic recovery is only `redispatch_same_attempt | escalate`
- watchdog never auto-mints `create_new_attempt`
- watchdog never consumes authored retry budget
- non-behavioral runtime/support-state/readback/prompt compatibility debt is deleted rather than kept for compatibility theater
- minimal, normal, and maximal e2e lanes pass
- real host OpenClaw proof shows correct effective inventories and at least one real node-tool call

## Deliverables and milestones

- deliverables: docs-first canon repair, authority collapse, explicit-arg node MCP rewrite, callback parity rewrite, same-session redispatch, prompt/send-mode cleanup, watchdog narrowing, redundant state/schema/test deletion, coverage raise, full proof lanes, and strict closeout review
- milestones: Phase 0 addendum green, Phase 4.5 docs-first sync green, authority path unified, node/callback contract flipped, same-session redispatch landed, watchdog narrowed, redundant state removed, repo tests green, host proof green, strict closeout review green

## Ordered work packages

- `P4.5-WP1`: authority collapse under `NodeSession.session_key` plus task/currentness truth, including runtime/schema deletion prep
- `P4.5-WP2`: explicit-arg node MCP and callback parity on one semantic node-operation service
- `P4.5-WP3`: parent/root same-session redispatch with the same Gateway `sessionKey`, fresh `runId`, fresh `idempotencyKey`, and `full_prompt`
- `P4.5-WP4`: prompt and dispatch-state cleanup to full-prompt-only live behavior plus dispatch-local node tool context
- `P4.5-WP5`: watchdog narrowing and redundant state deletion in behavior-safe order
- `P4.5-WP6`: stale-test rewrite, coverage raise, DB/reset proof, full pytest, e2e proof, and real host OpenClaw proof

## Wave plan

- Wave 1: run the docs-first edit slice, the authority/runtime DB edit slice, the node-MCP/callback edit slice, and the watchdog/observability edit slice in parallel; the parent integrates them in `P4.5-WP1` through `P4.5-WP5` order
- Wave 2: after targeted integration proof, run the prompt/runtime asset edit slice for `P4.5-WP4` and the remaining prompt/runtime seams
- Wave 3: the parent runs the targeted proving suite and coverage pass, then the QA review-only slice returns pass-to-close or exact blockers without edits
- Wave 4: after final expensive proof lanes, the strict closeout review slice may write only the authoritative Phase 4.5 review artifact; if it cannot pass, it must stop and return findings instead

## Delegated slice briefs

### phase45-docs-execution

- do-not-edit surfaces:
  - `apps/**`
  - `scripts/**`
- required reads:
  - the full Phase 4.5 required-read packet from this plan and the phase page
- required tests/validators:
  - `./.venv/bin/python -m scripts.docs.prompt_catalog.cli generate` when prompt inputs change
  - `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate`
  - `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
- expected outputs:
  - docs-first canon stays truthful for the deletion-heavy closure
  - touched markdown files have no broken line-wrap problems
- dependencies:
  - Phase 0 addendum merged
- evidence to return:
  - touched docs inventory
  - validator blockers, if any
- parent-owned decisions:
  - exact deletion order once code work begins
- stop conditions:
  - stop if a truthful fix requires app-code edits

### phase45-authority-runtime-db

- do-not-edit surfaces:
  - `apps/api/autoclaw/openclaw/**`
  - prompt assets and prompt generated docs
- required reads:
  - the full Phase 4.5 required-read packet from this plan and the phase page
- required tests/validators:
  - focused authority and runtime-schema tests only
- expected outputs:
  - shared authority resolver rooted in `NodeSession.session_key`
  - callback-binding authority removed from live runtime truth
- dependencies:
  - docs-first sync green
- evidence to return:
  - touched code inventory
  - focused test results
- parent-owned decisions:
  - final removal timing for redundant state families
- stop conditions:
  - stop if MCP wrapper or prompt assets must be changed

### phase45-node-mcp-callback

- do-not-edit surfaces:
  - watchdog and prompt-runtime asset surfaces
- required reads:
  - the full Phase 4.5 required-read packet from this plan and the phase page
- required tests/validators:
  - focused MCP and callback tests only
- expected outputs:
  - explicit-arg node MCP
  - callback and node parity on one semantic node-operation service
- dependencies:
  - authority resolver available
- evidence to return:
  - touched code inventory
  - focused test results
- parent-owned decisions:
  - final OpenClaw host proof harness shape
- stop conditions:
  - stop if DB or watchdog surfaces must be changed outside owned scope

### phase45-watchdog-observability

- do-not-edit surfaces:
  - callback and MCP wrapper surfaces
  - prompt-runtime asset surfaces
- required reads:
  - the full Phase 4.5 required-read packet from this plan and the phase page
- required tests/validators:
  - focused watchdog, observability, and support-state tests only
- expected outputs:
  - watchdog narrowed to `redispatch_same_attempt | escalate`
  - redundant support-state/readback residue removed where no longer behavioral
- dependencies:
  - docs-first sync green
- evidence to return:
  - touched code inventory
  - focused test results
- parent-owned decisions:
  - final deletion timing for `DispatchTurn.status`
- stop conditions:
  - stop if authority or prompt-runtime surfaces must change outside owned scope

### phase45-prompt-runtime-assets

- do-not-edit surfaces:
  - authority resolver and MCP wrapper surfaces
- required reads:
  - the full Phase 4.5 required-read packet from this plan and the phase page
- required tests/validators:
  - prompt unit tests
  - Phase 2 bootstrap/materialization tests that touch prompt/runtime behavior
  - prompt-catalog generate and validate
- expected outputs:
  - full-prompt-only live runtime behavior
  - dispatch-local node-tool context for `task_id` and `session_key`
- dependencies:
  - authority and MCP contract stabilized
- evidence to return:
  - touched code/docs inventory
  - focused test and validator results
- parent-owned decisions:
  - whether any retained compatibility artifact must survive until a later patch in the same phase
- stop conditions:
  - stop if watchdog or DB deletion work is required outside owned scope

### phase45-qa-gate-review

- do-not-edit surfaces:
  - all repo-tracked files
- required reads:
  - the full Phase 4.5 required-read packet from this plan and the phase page
  - the integrated diff
  - the Phase 4.5 evidence draft
- required tests/validators:
  - none; inspect already-run proof only
- expected outputs:
  - exact remaining blockers or pass-to-close recommendation
- dependencies:
  - targeted proving suite and coverage pass complete
- evidence to return:
  - review memo only
- parent-owned decisions:
  - whether a final patch invalidates any expensive proof lane
- stop conditions:
  - stop and report only; do not edit files

### phase45-strict-closeout-review

- do-not-edit surfaces:
  - every repo-tracked file except `docs/execution/reviews/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md`
- required reads:
  - the full Phase 4.5 required-read packet from this plan and the phase page
  - the final Phase 4.5 evidence artifact
  - the final integrated diff
  - `docs/execution/gates/mandatory-review-gate.md`
  - `docs/execution/gates/reset-gate.md`
- required tests/validators:
  - none; inspect already-run proof only
- expected outputs:
  - the authoritative Phase 4.5 closeout review artifact, or a fail review with exact blockers
- dependencies:
  - all expensive proof lanes complete
- evidence to return:
  - final review text
- parent-owned decisions:
  - none beyond deciding whether returned blockers require another patch pass
- stop conditions:
  - stop and return findings instead of a pass review if any required proof lane, kill-list proof, reset proof, or docs answer-sourcing proof is missing

## Validation checkpoints

- baseline checks before edits: confirm docs-freeze status, current node-MCP failure shape, current prompt-unit baseline, and local OpenClaw MCP config drift
- docs-first checkpoint: run prompt-catalog generate when prompt inputs change, then prompt-catalog validate and docs-freeze
- targeted proving checkpoint: run authority/callback rejection tests, phase4b MCP tests, phase4b watchdog tests, runtime schema-contract tests, prompt unit tests, Phase 2 bootstrap/materialization tests, phase4a gateway/session integration tests, phase3 callback/control/runtime route compatibility tests, and e2e minimal/normal/maximal after interface-stable integration
- coverage checkpoint: run one targeted `pytest --cov` pass over the touched Phase 4.5 modules and use the missing-branch report to add tests before the full suite
- final expensive proof checkpoint: run `ruff format`, `ruff check`, `mypy`, `make pyright-api`, `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`, shipped-path SQLite init/upgrade/reset proof, `make test-api-db`, one full `./.venv/bin/pytest`, and the real OpenClaw host proof lane once at code freeze
- no-duplicate expensive-run rule: keep a pass matrix in the evidence artifact and do not rerun a green expensive lane unless a later patch invalidates it

## Required tests and validators

- unified authority rejection tests for stale/revoked/non-current session cases
- task mismatch and lineage mismatch tests
- explicit-arg node MCP schema tests
- mounted node MCP tests with no baked hidden `x-session-key` contract
- callback/node parity tests
- parent/root same-session redispatch tests asserting the same Gateway `sessionKey`, a fresh `runId`, and a fresh `idempotencyKey`
- worker retry fresh-session regression tests
- watchdog `redispatch_same_attempt | escalate` tests and no-authored-budget-consumption tests
- prompt hygiene tests for dispatch-local `task_id` / `session_key`
- prompt unit tests
- support/readback omission tests for removed fields
- runtime schema contract tests after field/table deletion
- Phase 2 bootstrap/materialization regression tests where Phase 4.5 runtime changes can invalidate them
- minimal, normal, and maximal e2e lanes
- shipped-path SQLite smoke/reset proof
- Postgres + Docker strong verification
- real OpenClaw host proof with correct effective inventories and one real node-tool call

## Required docs and examples

- Phase 0 addendum docs
- Phase 4.5 phase page, file lock map, and landing map when reopened
- runtime/session/continuity/watchdog/MCP redesign owners
- prompt-layer owner docs plus generated prompt inventory/examples
- touched current-contrast docs
- API schema appendix and any touched readback shapes
- every touched markdown file must be cleaned of broken line wraps inside sentences or bullets

## Exit evidence

- the final Phase 4.5 evidence artifact records exact green commands and dates
- the final Phase 4.5 evidence artifact records the pass matrix for targeted lanes, expensive lanes, and any valid no-rerun decisions
- docs-freeze and prompt-catalog proof is explicit where applicable
- targeted suite proof, coverage proof, SQLite shipped-path proof, Postgres + Docker proof, full pytest proof, e2e proof, and real OpenClaw host proof are explicit
- stale-logic search proof is explicit for `same_session_continue`, `create_new_attempt`, `DispatchCallbackBindingModel`, `NodeMcpBinding`, `DISPATCH_PHASE_VALUES`, and the removed runtime-state families
- the final Phase 4.5 review records the independent closeout result

## Rollback or stop conditions

- stop and execute the Phase 0 addendum first if canon still blocks support-state deletion or current-doc collateral
- stop if any candidate removal still drives actual runtime behavior after the rewrite
- stop if explicit-arg node MCP cannot satisfy the host OpenClaw lane without reintroducing hidden binding or baked per-dispatch headers
- stop if the host OpenClaw proof would require Phase 5B install/release ownership rather than an execution-time proof harness
- stop if the strict independent reviewer does not issue a pass

## Cross-links

- evidence artifact: `docs/execution/evidence/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md`
- review artifact: `docs/execution/reviews/phase-4.5-session-authority-simplification-and-runtime-debt-removal.md`
