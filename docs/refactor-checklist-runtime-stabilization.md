# AutoClaw refactor checklist — runtime stabilization closure record

Status: stabilization pass completed; broader architectural cleanup still partial
Last verified against local repo state: 2026-04-20
Scope: backend/runtime/compiler/resource/control-plane cleanup only

This file is now a closure record for the runtime-stabilization pass, not an implementation-prep tracker.
It should be read as:

- the stabilization pass is closed
- the current verification baseline is green
- some broader architectural cleanup goals from the original checklist are improved but not fully exhausted

## Closure verdict

- [x] The checklist is no longer in implementation-prep state.
- [x] Runtime stabilization landed strongly enough to treat this pass as closed.
- [x] The codebase now has a trustworthy verification baseline.
- [x] The front-door docs were rewritten so they no longer contradict the current repo state.
- [x] This closure record does **not** claim that every original architectural cleanup goal is fully exhausted.

## Verified baseline

- [x] `make format-api` passes.
- [x] `make check-api` passes.
- [x] `make test-api` passes.
- [x] `make test-api-db` passes.
- [x] The old stale registry bootstrap seed-count expectation was rebaselined to current packaged definitions.
- [x] The prior line-length failure in `tests/integration/test_runtime_api.py` is gone.
- [x] The current DB-backed suite is green on a fresh Postgres test database.

## Runtime identity and callback truth

- [x] Callback/session/manifest lineage checks are materially more centralized than they were when this checklist began.
- [x] A validated binding object now exists in `app/runtime/callback_bindings.py` and is reused by remaining callback-bound paths.
- [x] Checkpoint writes depend on the shared callback binding contract.
- [x] Approval creation uses the shared callback binding contract when callback-bound.
- [x] Replan requests use the shared callback binding contract when callback-bound.
- [x] Manifest acknowledgement uses the same binding vocabulary and error class.
- [x] Worker-bundle access uses the same binding vocabulary.
- [x] `publish_context_item` uses the same binding vocabulary.
- [x] Route-level callback invariant logic in `api/routes/flows.py` was reduced enough that routes are no longer the sole owners of runtime-domain validation.
- [x] Canonical UUID parsing remains the default in runtime/control entry paths.
- [x] Compatibility parsing is retained only on the one documented manifest-ack shim path.
- [x] Remaining caveat: this is still not a single canonical owner for every runtime-domain validation rule in the codebase.

## Runtime read truth and presenter cleanup

- [x] Runtime read truth is materially more centralized than it was when this checklist was opened.
- [x] Presenters are presentation-first and no longer own the key runtime invariants fixed in this pass.
- [x] Latest visible checkpoint selection now uses actual checkpoint recency instead of traversal order.
- [x] The old dead `current_runtime_view()` placeholder was removed instead of being preserved.
- [x] Placeholder `if False` runtime logic in the touched packaging path is gone.
- [x] Runtime summaries, worker bundle reads, and callback-bound reads now agree on manifest/session lineage.
- [x] Remaining caveat: loader/query ownership is still spread across `runtime/read_models.py` and a few route/runtime-specific query paths.

## Task/resource/compose truth

- [x] Task resource bindings remain the durable task resource truth.
- [x] `TaskCompose` is treated as the persisted launch snapshot/view rather than a competing durable resource truth layer.
- [x] Runtime session/container-ish state remains derived from runtime tables rather than a second canonical truth path.
- [x] Manifest files are treated as projections/audit artifacts rather than authority.
- [x] Task launch/resource truth now behaves coherently across the main runtime paths.
- [x] Create-task, task-compose start, upload refresh, and replan remint now share the same task/bootstrap/snapshot vocabulary.
- [x] Upload refresh no longer wipes compose launch provenance or explicit compose dependencies.
- [x] `tasks/composes/start` now actually honors requested root/bootstrap intent through the canonical bootstrap path.
- [x] Cross-module underscore-helper imports were removed from the touched task/runtime seam.
- [x] The `task_service.py` ↔ `resources.py` seam was turned into a real public boundary by promoting the needed helpers.
- [x] Upload/materialized-file writes now enforce resolved task-root containment and reject symlink/root escapes.
- [x] Task bootstrap, upload containment, and compose-refresh preservation are covered by tests.
- [x] Remaining caveat: ownership is still split across `app.paths`, `runtime/resources.py`, `runtime/packaging.py`, and `services/task_service.py`.

## Orchestration, readiness, and dispatch

- [x] Controller advancement now runs until the next real boundary instead of performing only a single scheduler hop.
- [x] Scheduler-owned next-node release logic is canonical in the touched code path.
- [x] The duplicate runner `_next_unstarted_node()` path was removed.
- [x] Node-path materialization remains explicit and regression-covered in the existing runtime/compiler test surface.
- [x] Approval resolution auto-advances through the controller path.
- [x] Manifest acknowledgement auto-advances through the controller path.
- [x] Watchdog logic is explicit, bounded, and backed by tests.
- [x] Same-session watchdog wake, timeout ambiguity, wake-budget exhaustion, and escalation paths are all covered by the current runtime/API test surface.
- [x] Dispatch/bridge/runtime behavior is materially cleaner and easier to explain than it was when this checklist opened.
- [x] Remaining caveat: `runtime/runner.py` is still a large central owner, so this is not full orchestration decomposition closure.

## Schema, compiler, and registry

- [x] The migration/schema checkpoint gate is closed strongly enough for this pass because the fresh Postgres-backed suite is green.
- [x] The current local/unit gate remains green alongside the DB-backed gate.
- [x] Compiler merge semantics remain strongly test-defined.
- [x] Runtime/replan no longer depends on compiler-private `_merge_*` imports.
- [x] Registry definition precedence is explicit, documented, and test-backed.
- [x] Seeded workflow truth and packaged/filesystem override behavior are aligned.
- [x] Remaining caveat: this is current-suite closure, not proof of a fully rebaselined migration-history strategy.

## Route surface and trust lanes

- [x] Public/operator, internal callback/controller, and browser bootstrap trust lanes are explicitly documented.
- [x] Browser-visible config no longer exposes a reusable operator API key.
- [x] `supportsAuthoring` remains `false` until a safer browser auth contract exists.
- [x] The route-surface doc now reflects current behavior instead of historical drift.

## Docs rewritten

- [x] `README.md` was truth-synced away from stale Phase 6.5 framing.
- [x] `ROADMAP.md` was truth-synced away from stale Phase 7 front-door framing.
- [x] `docs/roadmap/current.md` was updated with the actual current verification baseline.
- [x] `docs/flows/02-default-runtime-lifecycle.md` now matches current controller advancement behavior.
- [x] `docs/flows/04-approval-and-watchdog.md` now matches current approval auto-advance and watchdog semantics.
- [x] `docs/api-route-trust-lanes.md` carries a current “last verified” contract.
- [x] `docs/registry-definition-precedence.md` carries a current “last verified” contract.

## Suggested module outcomes — closure note

The earlier checklist proposed several possible extraction modules.
Those suggestions are now closed as design suggestions rather than remaining TODOs.
They are editorial closure calls, not proof that every architectural concern is fully exhausted.

- [x] `runtime/execution_binding.py` suggestion closed as superseded by strengthening `runtime/callback_bindings.py` with a real `ExecutionBinding` value object instead of adding file spam.
- [x] `runtime/runtime_snapshot.py` suggestion closed as superseded by strengthening `runtime/read_models.py` plus presenter/runtime snapshot selection rather than adding another thin layer.
- [x] `runtime/task_runtime.py` suggestion closed as superseded by strengthening the public boundaries in `runtime/resources.py`, `runtime/packaging.py`, and `services/task_service.py`.
- [x] `runtime/flow_runtime.py` suggestion closed as unnecessary for this pass because the runner/scheduler/control cleanup landed without needing another wrapper layer.
- [x] `runtime/manifest_lifecycle.py` suggestion closed as unnecessary for this pass because manifest/session ownership became understandable without creating another module.

## Anti-goals respected

- [x] No major console/UI refactor was mixed into the runtime stabilization pass.
- [x] No new workflow features were added as a substitute for ownership cleanup.
- [x] The touched areas did not keep duplicate code paths “for now” once a canonical owner was clear.
- [x] The pass did not mix internal package renaming with invariant cleanup.
- [x] The pass favored fewer clear ownership modules over file multiplication.

## Definition of done

- [x] The test suite is trustworthy again.
- [x] Delegated execution identity logic is centralized and reused across callback-bound runtime paths.
- [x] Worker-bundle and publish-context validation share the same binding contract as callback writes.
- [x] Runtime orchestration now has a clear enough owner path for the touched stabilization surfaces.
- [x] Read-path truth is selected coherently enough that presenters are no longer reconstructing the specific runtime truths fixed in this pass.
- [x] Node path / graph materialization semantics are test-locked strongly enough for this pass.
- [x] Task-compose / task-resource / filesystem materialization truth is coherent enough for this pass.
- [x] No duplicated launch-binding/remint decision logic remains in the touched runtime/presenter/API paths.
- [x] Watchdog logic is explicit and bounded.
- [x] The migration/schema checkpoint gate passes on the verified Postgres path, and the local fast gate is green.
- [x] Seeded workflow/docs/runtime truth for the exemplar graph is aligned.
- [x] API/query surfaces are materially cleaner and less duplicative than when this checklist began.
- [x] No cross-module imports of underscore-prefixed helpers remain in the touched areas.
- [x] No obviously dead transitional helper remains in the touched areas.
- [x] Browser/operator auth and secret exposure surfaces are safer and explicit.
- [x] Routes are thin enough, presenters are presentation-only enough, and runtime logic is runtime-owned enough to close this stabilization checklist.
- [x] The canonical local start/test path is simpler and verified after the refactor.

## Closure note

- [x] All checklist actions are now closed as landed, verified, or superseded by a cleaner implementation choice.
- [x] Any future work should start from a fresh tracker rather than reopening this historical refactor checklist in place.
