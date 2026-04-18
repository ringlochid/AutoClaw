# Next Implementation Plan

## Goal

Finish the remaining reliability-first work in small, file-bounded slices, with targeted tests and an explicit review pass after each slice. Keep the pass focused on execution reliability, clear authority boundaries, scalable typed read surfaces, and truth-sync with the intended design only after the code proves it.

## Authoritative ordered plan, all 7 steps stay visible

1. **Bridge trust and callback identity**
2. **Recovery + typed handoff**
3. **Local-first defaults**
4. **Logical task/runtime layer**
5. **Bounded but semantics-thick plugin**
6. **Phase 10 semantics**
7. **Phase 11 and later Phase 12**

This file must keep the full 7-step order visible even when some steps are already largely landed.
For this pass, Steps 1, 2, 5, and 6 are the active implementation focus.
Steps 3 and 4 remain explicit plan gates, but should be treated as verify-and-fix-only unless a targeted bug appears.
Step 7 remains explicitly later, after Steps 1 through 6 are stable.

## Status after review in this pass

- **Step 1, Bridge trust and callback identity:** complete for this pass, with callback/binding behavior re-proved through the runtime DB and API suites.
- **Step 2, Recovery + typed handoff:** complete for this pass, with `response.failed`, watchdog recovery behavior, worker bundle evidence, and `publish_context_item` flows covered by unit/API tests.
- **Step 3, Local-first defaults:** verify-only in this pass, no targeted bug found, so the already-landed files stayed closed.
- **Step 4, Logical task/runtime layer:** verify-only in this pass, no targeted bug found, so the already-landed files stayed closed.
- **Step 5, Bounded but semantics-thick plugin:** complete for this pass, with operator-lane query expansion now including runtime/timeline slices while worker-lane default remains bounded.
- **Step 6, Phase 10 semantics:** complete for this pass, with effective-node/resource semantics re-verified through the unit and DB-backed compiler/runtime suites.
- **Step 7, Phase 11 and later Phase 12:** still intentionally later.

## Read-light rules for this pass

- Prefer narrow file reads over broad repo scans.
- Change one slice at a time, then run only the tests that prove that slice.
- Do not reopen Phase 11 or broader Phase 12 scope while Phase 8/10 reliability gaps remain.
- Treat already-landed local-first and runtime-layer work as stable unless a targeted bug appears.

## Verification rules for this pass

- Keep unit-only and DB-backed integration runs separate.
- Before any DB-backed integration run, make sure the test Postgres is actually up. A connection refusal is infra noise, not product evidence.
- Do not advance to the next slice until the current slice has passing proving tests and an explicit review against its checklist.

## Already landed, do not rebuild unless a bug is found

These areas correspond mainly to Steps 3 and 4 in the ordered plan. Keep them visible in the plan, but only reopen them if a failing test or review finds a real gap:

- `apps/api/app/paths.py`
- `apps/api/app/runtime/resources.py`
- `apps/api/app/runtime/packaging.py`
- `apps/api/app/db/models/runtime.py`
- `apps/api/app/api/routes/registry.py`
- `apps/api/app/registry/publish.py`
- `apps/api/app/registry/audit.py`
- `apps/api/alembic/versions/20260418_0004_registry_definition_write_audit.py`
- `autoclaw-bridge-plugin/src/plugin-tools.ts` capability split and registry write audit forwarding

Recheck the plugin-side assumption before Slice 3 if the bridge-plugin repo has been reset or rebased, because it lives in a separate repo.

---

## Slice 1, Bridge trust and callback identity

### Goal
Close the remaining trust/binding gap so callback handling is deterministically tied to the real delegated execution identity.

### Files to change

- `apps/api/app/runtime/callback_bindings.py`
  - Make this the single binding authority for `provider_session_key`, `manifest_hash`, attempt identity, and `ack_checkpoint_id` checks.
  - Tighten stale/late callback rejection paths and make failure reasons explicit.

- `apps/api/app/runtime/checkpoints.py`
  - Recheck `record_checkpoint` against the binding helper.
  - Make resume/retry lineage rules explicit around `ack_checkpoint_id`.

- `apps/api/app/runtime/approvals.py`
  - Align approval callback validation with the same binding contract.

- `apps/api/app/runtime/replan.py`
  - Align replan callback validation with the same binding contract.

- `apps/api/app/runtime/dispatcher.py`
  - Verify issuance/update semantics for `ack_checkpoint_id` are deterministic across projected, acked, resumed, and retried states.

- `apps/api/app/services/openclaw_bridge.py`
  - Ensure the bootstrap/debug envelope and resumed-worker envelope both surface the exact binding fields operators and tests should rely on.

- `apps/api/app/api/routes/flows.py`
  - Tighten any route-level worker-bundle or callback-related query contract that still allows weaker identity than the runtime helpers.

### Tests

Run only this slice first:

- `apps/api/tests/integration/test_flow_runtime_db.py`
- `apps/api/tests/integration/test_runtime_api.py`

If needed, add a new narrow unit/integration test near the runtime callback path rather than expanding large end-to-end coverage.

### Review checklist

- Every callback path uses the same binding helper, not one-off checks.
- A stale callback fails closed with a clear error.
- `ack_checkpoint_id` is not treated as optional once the worker is in acked execution.
- Resume/retry semantics are deterministic, not best-effort.

---

## Slice 2, Recovery rules, typed handoff, and governance evidence

### Goal
Freeze timeout/failure/escalation semantics, make typed handoff first-class, and keep governance/review evidence on typed surfaces instead of prompt residue.

### Files to change

- `apps/api/app/integrations/openclaw.py`
  - Freeze `response.failed` and timeout classification rules.
  - Keep transport/runtime failure categories explicit.

- `apps/api/app/runtime/watchdog.py`
  - Truth-sync same-session wake vs inspect-before-retry vs escalation behavior.
  - Keep ambiguous timeout states resumable where intended.

- `apps/api/app/api/routes/flows.py`
  - Extend typed handoff/evidence publication only where needed.
  - Keep `publish_context_item` as the explicit handoff path, not prompt residue.

- `apps/api/app/api/presenters/runtime.py`
  - Surface the evidence/governance payload the next node actually needs.

- `apps/api/app/schemas/runtime.py`
  - Add any missing typed response fields required by the evidence/bundle contract.

- `autoclaw-bridge-plugin/src/plugin-tools.ts`
  - Only adjust worker-bundle or handoff tool UX if the API contract changes.

### Tests

- `apps/api/tests/unit/test_openclaw_integration.py`
- `apps/api/tests/integration/test_runtime_api.py`

Focus especially on:
- `response.failed`
- wake timeout
- wake failure
- blocked / needs-approval evidence propagation
- worker bundle + `publish_context_item`

### Review checklist

- Review/governance nodes can consume typed evidence without prompt whispering.
- Downstream handoff state is available through typed context items or bundles, not hidden transcript residue.
- Timeout states are classified consistently across runtime, watchdog, and docs.
- No new hidden control semantics are introduced through transcript text.

---

## Slice 3, Bounded but semantics-thick plugin query surface

### Goal
Add the smallest next worker/operator read surface needed for deterministic replan/review work, using typed server-side bundles instead of many fragile round trips, without expanding control authority.

### Files to change

- `autoclaw-bridge-plugin/src/plugin-tools.ts`
  - Add only the next high-value query/bundle tools for runtime, manifests, checkpoints, approvals, and recent event/log slices, preferring a few stable bundles over many tiny round trips.
  - Keep write/control ownership in AutoClaw.

- `autoclaw-bridge-plugin/src/index.test.ts`
  - Add direct tool registration and callback-shape coverage for each new tool.

- `autoclaw-bridge-plugin/openclaw.plugin.json`
  - Add config hints only if a new capability gate or parameter is really needed.

- `autoclaw-bridge-plugin/README.md`
  - Truth-sync the new tool surface and worker/operator lane guidance.

- `apps/api/app/api/routes/flows.py`
  - Add the backing typed endpoints if they do not already exist.

- `apps/api/app/api/presenters/runtime.py`
  - Assemble stable bundles server-side.

- `apps/api/app/schemas/runtime.py`
  - Define the typed read models for those bundles.

### Tests

- `cd ~/leo/projects/autoclaw-bridge-plugin && npm test`
- `apps/api/tests/integration/test_runtime_api.py`

Prefer adding one focused integration test per new bundle/query endpoint rather than one huge scenario.

### Review checklist

- The plugin remains authority-thin.
- Worker-lane default stays bounded.
- Operator-query expansion is opt-in, not ambient.
- Server-side joins are deterministic and typed.
- Replan/review flows do not depend on transcript scraping or many fragile client-side joins.

---

## Slice 4, Phase 10 compiler semantics before richer authoring work

### Goal
Finish the semantic contract the runtime depends on before expanding graph/operator UI.

### Files to change

- `apps/api/app/compiler/resolve.py`
  - Lock down effective-node precedence across role, workflow, node, and replan overlays.

- `apps/api/app/compiler/validate.py`
  - Make merged semantic validation fail closed where resource/skill semantics are ambiguous.

- `apps/api/app/schemas/registry.py`
  - Add only the schema fields needed for stronger compiled/effective-node meaning.

- `apps/api/app/api/presenters/runtime.py`
  - Expose the compiled/effective meaning cleanly if runtime/read models need it.

### Tests

- `apps/api/tests/unit/test_effective_node_merge.py`
- `apps/api/tests/integration/test_compiler_resource_semantics.py`
- `apps/api/tests/integration/test_phase456_runtime_db.py`

### Review checklist

- Precedence is deterministic and documented by tests.
- `RuntimeImage` meaning can be derived from compiled output, not raw authoring rereads.
- Resource and skill semantics fail closed on ambiguity.

---

## Slice 5, Docs truth-sync and final review

This slice is the final truth-sync pass across Steps 1 through 6. Step 7 stays queued unless one of the earlier slices proves the boundary wording wrong.

### Goal
After the code slices land, update the docs to describe the real system, not the intended one.

### Files to change

- `docs/roadmap/current.md`
- `docs/roadmap/08-phase-8-production-openclaw-bridge-and-native-plugin-adapter.md`
- `docs/architecture/06-openclaw-runtime-bridge.md`
- `docs/roadmap/10-phase-10-effective-node-compiler-semantics-and-authoring-safety.md`
- `autoclaw-bridge-plugin/README.md`

Only touch `docs/roadmap/11-*` or `12-*` if the implemented boundary materially changes their wording.

### Tests / verification

- Re-run the narrow targeted suites from the slices above, not a giant blanket run by default.
- Run targeted lint/checks only on touched files.
- Keep unit-only and DB-backed integration commands separate, and start the test Postgres before the DB-backed suites.

Recommended final verification set:

- `cd ~/leo/projects/autoclaw && ./.venv/bin/pytest apps/api/tests/unit/test_openclaw_integration.py apps/api/tests/unit/test_effective_node_merge.py -q`
- `cd ~/leo/projects/autoclaw && ./.venv/bin/pytest apps/api/tests/integration/test_flow_runtime_db.py apps/api/tests/integration/test_runtime_api.py apps/api/tests/integration/test_compiler_resource_semantics.py -q`
- `cd ~/leo/projects/autoclaw && ./.venv/bin/ruff check <touched api files>`
- `cd ~/leo/projects/autoclaw-bridge-plugin && npm test`

### Final review checklist

- No broad Phase 11 or Phase 12 work was smuggled into a reliability pass.
- Each changed behavior is backed by a targeted test.
- Already-landed local-first/runtime-layer files were only touched for proven bugs.
- Docs reflect the actual landed contract.
- Worktrees are cleaned to a commit-ready state before calling the pass done.

## Latest proving results from this pass

- `cd ~/leo/projects/autoclaw && ./.venv/bin/pytest apps/api/tests/unit/test_openclaw_integration.py apps/api/tests/unit/test_effective_node_merge.py -q` → `10 passed`
- `cd ~/leo/projects/autoclaw && ./.venv/bin/pytest apps/api/tests/integration/test_flow_runtime_db.py apps/api/tests/integration/test_runtime_api.py apps/api/tests/integration/test_compiler_resource_semantics.py apps/api/tests/integration/test_phase456_runtime_db.py -q` → `47 passed`
- `cd ~/leo/projects/autoclaw && ./.venv/bin/ruff check apps/api/app/api/presenters/runtime.py apps/api/app/api/routes/flows.py apps/api/app/schemas/runtime.py apps/api/tests/integration/test_runtime_api.py` → `All checks passed!`
- `cd ~/leo/projects/autoclaw-bridge-plugin && npm test` → `12 passed`

---

## Explicitly not in the next pass

Do not treat these as part of the immediate implementation plan unless a preceding slice forces them:

- broad graph/operator UI expansion
- n8n-style workflow editing
- broad OpenClaw-side operator automation beyond the bounded query surface
- Docker-first runtime backend work
- large local-first redesign of already-landed task/runtime layer files
