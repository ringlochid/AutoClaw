# Next Implementation Plan

## Goal

Finish the remaining reliability-first work in small, file-bounded slices, with targeted tests and an explicit review pass after each slice.

## Read-light rules for this pass

- Prefer narrow file reads over broad repo scans.
- Change one slice at a time, then run only the tests that prove that slice.
- Do not reopen Phase 11 or broader Phase 12 scope while Phase 8/10 reliability gaps remain.
- Treat already-landed local-first and runtime-layer work as stable unless a targeted bug appears.

## Already landed, do not rebuild unless a bug is found

These areas look live enough that the next pass should only touch them if a failing test or review finds a real gap:

- `apps/api/app/paths.py`
- `apps/api/app/runtime/resources.py`
- `apps/api/app/runtime/packaging.py`
- `apps/api/app/db/models/runtime.py`
- `apps/api/app/api/routes/registry.py`
- `apps/api/app/registry/publish.py`
- `apps/api/app/registry/audit.py`
- `apps/api/alembic/versions/20260418_0004_registry_definition_write_audit.py`
- `autoclaw-bridge-plugin/src/plugin-tools.ts` capability split and registry write audit forwarding

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
Freeze timeout/failure/escalation semantics and make governance/review evidence first-class instead of prompt-luck.

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
- Timeout states are classified consistently across runtime, watchdog, and docs.
- No new hidden control semantics are introduced through transcript text.

---

## Slice 3, Bounded but semantics-thick plugin query surface

### Goal
Add the next worker/operator read surface needed for deterministic replan/review work, without expanding control authority.

### Files to change

- `autoclaw-bridge-plugin/src/plugin-tools.ts`
  - Add only the next high-value query/bundle tools for runtime, manifests, checkpoints, approvals, and recent event/log slices.
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

Recommended final verification set:

- `cd ~/leo/projects/autoclaw/apps/api && . .venv/bin/activate && pytest apps/api/tests/unit/test_openclaw_integration.py apps/api/tests/integration/test_flow_runtime_db.py apps/api/tests/integration/test_runtime_api.py apps/api/tests/unit/test_effective_node_merge.py apps/api/tests/integration/test_compiler_resource_semantics.py -q`
- `cd ~/leo/projects/autoclaw/apps/api && . .venv/bin/activate && ruff check <touched api files>`
- `cd ~/leo/projects/autoclaw-bridge-plugin && npm test`

### Final review checklist

- No broad Phase 11 or Phase 12 work was smuggled into a reliability pass.
- Each changed behavior is backed by a targeted test.
- Docs reflect the actual landed contract.
- Worktrees are cleaned to a commit-ready state before calling the pass done.

---

## Explicitly not in the next pass

Do not treat these as part of the immediate implementation plan unless a preceding slice forces them:

- broad graph/operator UI expansion
- n8n-style workflow editing
- broad OpenClaw-side operator automation beyond the bounded query surface
- Docker-first runtime backend work
- large local-first redesign of already-landed task/runtime layer files
