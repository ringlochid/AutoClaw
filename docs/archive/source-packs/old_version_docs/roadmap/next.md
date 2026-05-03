# Next Backend Work

Status: active backend-only follow-on checklist
Last verified: 2026-04-20

This file tracks unfinished backend/runtime work using unchecked boxes.
UI/editor/authoring work does not belong here.

## Remaining work by phase

### Phase 5 and Phase 7 — runtime control, recovery, and governance

- [ ] Reuse the flow-boundary snapshot outside `runner.py`, especially in watchdog and bridge-related control paths
- [ ] Concentrate “latest visible checkpoint / last progress / next checkpoint sequence” logic behind one runtime owner
- [ ] Add focused DB tests for watchdog candidate selection and ordering
- [ ] Extract more explicit policy-driven loop/governance rules instead of leaving them implicit in runtime branches
- [ ] Improve downstream evidence propagation so review/governance flows need fewer operator nudges

### Phase 8 — bridge/runtime mutation and read surfaces

- [ ] Split OpenClaw bridge responsibilities between runtime-side candidate/session claiming and transport-side request sending
- [ ] Move `publish_context_item` mutation prep fully out of the route layer into a runtime owner
- [ ] Move the remaining worker-bundle/context-item preparation out of routes and into runtime/read-model helpers
- [ ] Add and record a fresh live bridge smoke in a stable backend/runbook note

### Phase 9 and Phase 13 — task/runtime ownership cleanup

- [ ] Introduce one typed owner for task materialization roots and task key derivation
- [ ] Stop storing `_task_key` inside `Task.input_payload`
- [ ] Split `_upsert_task_compose()` into smaller value-building and persistence steps
- [ ] Decide whether `workflow.entrypoint` should be implemented or removed after the current explicit rejection phase
- [ ] Move task-route post-start/post-upload readback behind a clearer runtime/application owner

### Phase 10 — compiler/runtime contract cleanup

- [ ] Replace more `dict[str, Any]`-heavy runtime schemas with typed nested Pydantic models where the shape is known
- [ ] Reduce presenter patching of partially loaded ORM shapes by making read models more complete
- [ ] Add direct tests for read-model normalization and presenter slice assembly
- [ ] Continue narrowing runtime-side code that still depends on stringly typed task/resource specs

### Phase 13 — remaining backend closeout

- [ ] Continue decomposing `runner.py` so it is less of a large central owner
- [ ] Decide and document the migration-history cleanup/rebaseline strategy explicitly
- [ ] Remove remaining duplicated load forests in approvals/checkpoints/replan once a small set of named load profiles exists

## Rules

- [ ] Do not widen this file into UI/editor/product design work
- [ ] When an item is completed, move it to `current.md` as a checked item rather than leaving it here
- [ ] If an item is no longer active and becomes a true deferral, move it to `backlog.md`
