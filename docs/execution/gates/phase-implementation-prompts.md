# Phase prompts

Status: Reference

Use these prompts to route redesign implementation work. Shared agent policy lives in [AGENTS.md](../../../AGENTS.md). Coding standards live in [STYLE.md](../../../STYLE.md).

## Prompt families

The execution pack uses exactly three prompt families:

1. pre-implementation review
2. phase plan
3. post-implementation review

There is no separate execute-mode prompt in this pack. After plan approval, Codex executes using default behavior plus `AGENTS.md`, `STYLE.md`, the current phase page, the implementation file lock map, and the approved phase plan.

The execution pack does not keep a separate repo-global active-phase marker. Pre-implementation review must select the current phase using the phase selection rule in `docs/execution/phases/overview.md` and name that phase page explicitly before planning starts.

Compatibility note: the frozen CLI contract still includes `autoclaw definitions import ...` under Phase 5A.

## Shared router rule

- treat the current phase page as the sole phase-local implementation contract
- treat the current phase page as the sole phase-local delivery contract
- treat [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map
- use [AGENTS.md](../../../AGENTS.md) for shared read order, answer hierarchy, delegation, TDD, and closeout rules
- use [STYLE.md](../../../STYLE.md) for measurable coding and refactor standards
- read the primary redesign pages named by the phase page before touching code
- read any appendix owners named by the phase page when exact API, schema, prompt, or payload detail matters
- if code work uncovers a silent target contract, update canon before treating the behavior as settled

## Pre-implementation review prompt

```text
Run the pre-implementation review for the current redesign phase.

Tasks:
1. Select the current phase that owns the blocker and name the current phase
   page.
2. Re-read AGENTS.md, STYLE.md, the current phase page, the implementation file lock map, and the primary redesign references named by the phase page.
3. Re-read any named appendix owners only when exact API/schema/prompt/payload detail matters for the blocking issue.
4. Decide whether the current blocker is:
   - docs gap
   - code gap
   - stale logic survivor
   - cleanup/reset issue
   - test gap
   - phase mismatch
   - locked-surface mismatch
5. If docs are not decision-complete, stop implementation and list the canon fixes required first.
6. If the requested work falls outside the locked implementation surfaces for the phase, stop and say whether the next action is:
   - re-scope the work package
   - patch canon first
   - move the change to a different phase

Return:
- selected phase
- required reads complete or incomplete
- docs gap yes or no
- confidence
- blocking criteria
- pass or fail
- docs-first or code-first
- exact next prompt family to use
```

## Phase-plan prompt format

Every phase-plan prompt should use this structure:

```text
Goal:
Phase-local contract:
Locked implementation surfaces:
Required reads:
Unresolved questions:
Confidence:
Success criteria:
Deliverables:
Milestones:
Dependency-critical path:
Ordered work packages:
subagents:
Wave plan:
Validation checkpoints:
Required tests:
Required docs/examples:
Exit evidence:
Rollback/stop conditions:
```

## Phase 0 prompt

```text
Build the approved phase plan for Phase 0 of the redesign landing plan.

Goal:
- harden the docs root, root instruction surfaces, execution-pack authority split, and docs validation flow before code rewrite begins

Phase-local contract:
- docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md

Locked implementation surfaces:
- root instruction surfaces, execution pack docs, execution routers, and docs validation tooling from the implementation file lock map

Required reads:
- AGENTS.md
- STYLE.md
- current phase page
- docs/execution/maps/file-priority-map.md
- docs/execution/README.md
- docs/redesign/README.md

Unresolved questions:
- whether any execution or prompt-family authority still lives outside the canonical surfaces

Confidence:
- high only if the authority split and validator story are decision-complete

Success criteria:
- AGENTS.md is canonical
- STYLE.md is canonical for code standards
- execution routers, prompts, and gates no longer mirror conflicting authority
- docs validation and prompt-catalog validation paths are deterministic

Deliverables:
- root instruction surfaces
- execution router and prompt-family docs
- consistent docs tooling references

Milestones:
- root authority surfaces aligned
- execution pack aligned
- docs validation passes

Dependency-critical path:
- root authority surfaces -> execution router alignment -> docs validation

Ordered work packages:
- align root authority surfaces
- normalize execution routing and prompt-family ownership
- normalize docs validation and router references

subagents:
- either `no subagents` or bounded docs-only slices such as router normalization or validator cleanup

Wave plan:
- keep each wave limited to one docs ownership slice, then integrate and validate before another wave

Validation checkpoints:
- docs routing is canonical
- prompt-family wording is aligned
- validators pass

Required tests:
- docs routing and validation checks
- prompt-catalog validation when prompt authorities changed

Required docs/examples:
- root docs routers
- execution pack front doors

Exit evidence:
- exact files changed
- docs validators passed
- repo-wide search shows AGENTS.md and STYLE.md are canonical in execution surfaces

Rollback/stop conditions:
- stop and patch canon first if authority split or validator ownership is still ambiguous
```

## Phase 0.5 prompt

```text
Build the approved phase plan for Phase 0.5 of the redesign landing plan.

Goal:
- establish the cleanup baseline before redesign implementation continues
- lock fresh-baseline DB/schema reset, test rewrite policy, and plugin rebuild scope

Phase-local contract:
- docs/execution/phases/phase-0.5-cleanup-and-salvage-baseline.md

Locked implementation surfaces:
- salvage matrix, cleanup checklist, reset how-to pages, and cleanup routing surfaces from the implementation file lock map

Required reads:
- AGENTS.md
- STYLE.md
- current phase page
- docs/execution/maps/file-priority-map.md
- current-schema-route-and-plugin-migration-appendix.md
- repo-salvage-matrix.md
- cleanup-and-salvage-checklist.md
- primary redesign pages named by the phase page

Unresolved questions:
- whether any subsystem, test family, or plugin surface still has an ambiguous salvage disposition

Confidence:
- high only if no cleanup bucket remains vague

Success criteria:
- every major subsystem has an intentional salvage disposition
- one redesign baseline migration strategy is explicit
- stale-contract tests are classified and routed
- plugin rebuild boundary is target-only and bounded

Deliverables:
- salvage matrix updates
- cleanup checklist completion
- reset and plugin-boundary decisions

Milestones:
- subsystem classification complete
- stale-test classification complete
- reset boundary and plugin boundary complete

Dependency-critical path:
- subsystem classification -> reset/plugin boundary -> stale-test routing

Ordered work packages:
- classify subsystems
- classify test inventory
- freeze reset baseline
- freeze plugin rebuild boundary

subagents:
- either `no subagents` or bounded inventory-only slices such as subsystem inventory, stale-test inventory, or plugin-boundary inventory

Wave plan:
- integrate each inventory wave into the salvage matrix before starting another classification wave

Validation checkpoints:
- no ambiguous bucket remains
- reset consequences are explicit
- plugin boundary is target-only

Required tests:
- redesign-agnostic infra tests kept and rerun where applicable
- stale contract tests rewritten or deleted intentionally
- reset/reseed/bootstrap smoke evidence exists

Required docs/examples:
- salvage matrix
- cleanup checklist
- reset/reseed instructions

Exit evidence:
- completed checklist
- named keep/rewrite/delete/quarantine/plugin-rebuild decisions
- reset evidence requirements named

Rollback/stop conditions:
- stop if any subsystem, test family, or plugin boundary remains ambiguous
```

## Phase 1 prompt

```text
Build the approved phase plan for Phase 1 of the redesign landing plan.

Goal:
- land the tree-only authoring model and compiler rewrite

Phase-local contract:
- docs/execution/phases/phase-1-authoring-and-compiler-rewrite.md

Locked implementation surfaces:
- schema, compiler, workflow definitions, examples, and workflow schema appendix surfaces from the implementation file lock map

Required reads:
- AGENTS.md
- STYLE.md
- current phase page
- docs/execution/maps/file-priority-map.md
- primary redesign pages named by the phase page
- workflow-schema-appendix.md

Unresolved questions:
- whether any authored schema, compiler legality, or example still teaches stale target semantics

Confidence:
- high only if schema, compiler, and examples can all be kept in lockstep

Success criteria:
- tree-only workflow authoring is canonical in docs and code
- typed inputs are the hard dependency surface
- stale authored-edge and generic skill-ref semantics are removed from target behavior

Deliverables:
- schema and compiler alignment
- example alignment
- removal of stale target authoring semantics

Milestones:
- schemas aligned
- compiler aligned
- examples and fixtures aligned

Dependency-critical path:
- schema contract -> compiler legality -> examples and fixtures

Ordered work packages:
- align schema contracts
- align compiler normalization and validation
- align examples and fixture coverage

subagents:
- either `no subagents` or bounded schema-only, compiler-only, or examples-and-fixtures slices

Wave plan:
- finish one contract slice, integrate, run tests, review, and patch before the next slice

Validation checkpoints:
- schema docs and code agree
- compiler legality matches canon
- examples are copy-safe and current

Required tests:
- schema/compiler unit tests
- compile/validation integration tests
- regression coverage for removed target authoring semantics

Required docs/examples:
- minimal, normal, and maximal workflow examples
- schema docs and appendix owners

Exit evidence:
- compiler behavior matches docs
- stale authoring semantics are rejected or isolated
- required tests passed

Rollback/stop conditions:
- stop if authoring docs, compiler contract, and examples still disagree
```

## Phase 2 prompt

```text
Build the approved phase plan for Phase 2 of the redesign landing plan.

Goal:
- land prompt, render, manifest, task-root, artifact, and bootstrap rewrite

Phase-local contract:
- docs/execution/phases/phase-2-prompt-manifest-artifact-bootstrap.md

Locked implementation surfaces:
- prompt-layer owners and generated examples, runtime materialization surfaces, manifest/task-root/artifact docs, and prompt validation tooling from the implementation file lock map

Required reads:
- AGENTS.md
- STYLE.md
- current phase page
- docs/execution/maps/file-priority-map.md
- primary redesign pages named by the phase page
- workflow-schema-appendix.md
- prompt-resource-usage-appendix.md

Unresolved questions:
- whether prompt, manifest, task-root, or generated example behavior still relies on hidden continuity or filesystem-primary assumptions

Confidence:
- high only if the prompt docs, runtime code, and generated examples can move together

Success criteria:
- lean task compose launch behavior is canonical
- prompt/render/manifest/task-root contracts are explicit and test-backed
- runtime examples match landed behavior

Deliverables:
- prompt/render contract alignment
- manifest and task-root behavior alignment
- bootstrap/materialization alignment

Milestones:
- prompt/render logic aligned
- manifest/task-root semantics aligned
- bootstrap path aligned

Dependency-critical path:
- prompt contract -> manifest/task-root semantics -> bootstrap/materialization behavior

Ordered work packages:
- align prompt/render logic
- align manifest/task-root behavior
- align bootstrap/materialization behavior

subagents:
- either `no subagents` or bounded prompt/render, manifest/task-root, or bootstrap integration slices

Wave plan:
- integrate one prompt/runtime slice at a time, regenerate or revalidate prompt artifacts, then run tests before the next wave

Validation checkpoints:
- prompt examples match code
- manifest and task-root behavior are reproducible
- prompt validators and minimal-lane evidence pass when viable

Required tests:
- prompt/render unit tests
- bootstrap/materialization integration tests
- minimal e2e lane when viable

Required docs/examples:
- prompt-layer examples
- manifest/task-root docs
- runtime examples

Exit evidence:
- prompt/runtime examples match behavior
- minimal lane evidence exists when viable
- filesystem-primary truth is not retained accidentally

Rollback/stop conditions:
- stop if generated-root or prompt-contract semantics remain ambiguous in canon
```

## Phase 3 prompt

```text
Build the approved phase plan for Phase 3 of the redesign landing plan.

Goal:
- land runtime graph, parent review, closure, and structural replan semantics

Phase-local contract:
- docs/execution/phases/phase-3-runtime-parent-review-and-replan.md

Locked implementation surfaces:
- runtime persistence/control, runtime schemas/presenters, and runtime/review/replan owner docs from the implementation file lock map

Required reads:
- AGENTS.md
- STYLE.md
- current phase page
- docs/execution/maps/file-priority-map.md
- primary redesign pages named by the phase page
- workflow-schema-appendix.md
- api-schema-appendix.md

Unresolved questions:
- whether any runtime transition, closure, or replan rule still depends on stale checkpoint-only or gate-era behavior

Confidence:
- high only if runtime graph truth and parent-owned boundary rules are decision-complete

Success criteria:
- one attempt equals one bounded assignment attempt
- review outputs and closure rules match canon
- parent-owned structural replan is explicit and test-backed

Deliverables:
- runtime record/transition alignment
- parent/review/replan alignment
- closure evidence alignment

Milestones:
- runtime transitions aligned
- review and parent behavior aligned
- structural replan aligned

Dependency-critical path:
- runtime transitions -> review and closure -> replan adoption

Ordered work packages:
- align runtime record transitions
- align parent/review/closure behavior
- align structural replan adoption

subagents:
- either `no subagents` or bounded runtime transitions, review/closure, or replan slices

Wave plan:
- finish one runtime-control slice, integrate, run tests, review findings, and patch before another slice

Validation checkpoints:
- runtime truth matches docs
- review and closure behavior are explicit
- replan stays under parent authority

Required tests:
- runtime transition/replan/report unit tests
- runtime graph/boundary integration tests
- normal e2e lane when viable

Required docs/examples:
- runtime records and lifecycle
- review/replan docs
- closure and evidence examples

Exit evidence:
- runtime truth matches canonical docs
- normal lane evidence exists when viable
- stale checkpoint-only closure logic is gone

Rollback/stop conditions:
- stop if review, closure, or replan semantics still need canon changes
```

## Phase 4A prompt

```text
Build the approved phase plan for Phase 4A of the redesign landing plan.

Goal:
- land OpenClaw gateway, session lifecycle, continuity, and worker-lane integration contracts

Phase-local contract:
- docs/execution/phases/phase-4a-openclaw-gateway-session-and-continuity.md

Locked implementation surfaces:
- OpenClaw integration, bridge service, session/continuity runtime services, and gateway/session/continuity docs from the implementation file lock map

Required reads:
- AGENTS.md
- STYLE.md
- current phase page
- docs/execution/maps/file-priority-map.md
- primary redesign pages named by the phase page
- api-schema-appendix.md
- prompt-resource-usage-appendix.md

Unresolved questions:
- whether worker-lane dispatch, session, or continuity behavior still depends on mixed worker/operator assumptions

Confidence:
- high only if gateway/session/continuity boundaries are explicit and test-backed

Success criteria:
- worker-lane dispatch, session, and continuity behavior match canon
- gateway and bridge normalization boundaries are explicit
- continuity preserves the single-live-run invariant

Deliverables:
- gateway integration alignment
- session lifecycle alignment
- continuity alignment

Milestones:
- gateway behavior aligned
- session lifecycle aligned
- continuity path aligned

Dependency-critical path:
- gateway dispatch -> session lifecycle -> continuity behavior

Ordered work packages:
- align gateway dispatch and bridge normalization
- align session lifecycle behavior
- align continuity and worker-lane behavior

subagents:
- either `no subagents` or bounded gateway integration, session lifecycle, or continuity slices

Wave plan:
- integrate one worker-lane slice at a time, run session/continuity tests, then review and patch before another wave

Validation checkpoints:
- gateway and session docs match code
- continuity rules are explicit
- viable minimal and normal lanes pass

Required tests:
- worker-lane, session, and continuity tests
- viable minimal and normal e2e lanes

Required docs/examples:
- gateway contract docs
- session lifecycle docs
- continuity docs

Exit evidence:
- docs and code agree on gateway, session, and continuity behavior
- worker-lane integration is explicit and test-backed
- no stale mixed worker/operator assumptions remain in the worker contract

Rollback/stop conditions:
- stop if worker-lane or continuity behavior still needs canon changes
```

## Phase 4B prompt

```text
Build the approved phase plan for Phase 4B of the redesign landing plan.

Goal:
- land watchdog recovery, operator/plugin lane behavior, and exact support-state readbacks

Phase-local contract:
- docs/execution/phases/phase-4b-watchdog-operator-plugin-and-support-state.md

Locked implementation surfaces:
- watchdog services, plugin source, operator/support-state docs, and support-state example surfaces from the implementation file lock map

Required reads:
- AGENTS.md
- STYLE.md
- current phase page
- docs/execution/maps/file-priority-map.md
- primary redesign pages named by the phase page
- api-schema-appendix.md
- prompt-resource-usage-appendix.md

Unresolved questions:
- whether watchdog recovery, operator lane scope, or support-state files still rely on inferred rather than frozen semantics

Confidence:
- high only if watchdog, operator/plugin, and support-state behavior are explicit and bounded

Success criteria:
- watchdog and recovery behavior match canon
- worker lane, operator lane, and support tooling stay distinct
- exact support-state readback shapes are frozen and support-only

Deliverables:
- watchdog/recovery alignment
- operator/plugin lane alignment
- exact support-state readback contracts

Milestones:
- watchdog model aligned
- operator/plugin lane aligned
- support-state shapes frozen

Dependency-critical path:
- watchdog recovery -> operator/plugin scope -> support-state freeze

Ordered work packages:
- align watchdog recovery behavior
- align operator/plugin lane behavior
- freeze support-state readbacks and examples

subagents:
- either `no subagents` or bounded watchdog, operator/plugin, or support-state schema/example slices

Wave plan:
- integrate one watchdog/operator slice at a time, run integration tests and schema/example verification, then review and patch before another wave

Validation checkpoints:
- watchdog behavior is explicit
- operator/plugin scope is bounded
- support-state examples are frozen

Required tests:
- watchdog/operator/plugin integration tests
- support-state schema/example verification
- viable minimal, normal, and maximal e2e lanes

Required docs/examples:
- watchdog and recovery docs
- operator/plugin docs
- support-state examples

Exit evidence:
- docs and code agree on watchdog, operator/plugin, and support-state behavior
- exact support-state examples are frozen
- no stale worker/operator mixing remains

Rollback/stop conditions:
- stop if support-state or watchdog semantics are still inferred rather than frozen
```

## Phase 5A prompt

```text
Build the approved phase plan for Phase 5A of the redesign landing plan.

Goal:
- land definition ingest, public API surfaces, and the canonical root CLI contract

Phase-local contract:
- docs/execution/phases/phase-5a-definition-ingest-api-and-cli.md

Locked implementation surfaces:
- ingest services, API routes/presenters, root CLI entrypoints, and ingest/API/CLI owner docs from the implementation file lock map

Required reads:
- AGENTS.md
- STYLE.md
- current phase page
- docs/execution/maps/file-priority-map.md
- primary redesign pages named by the phase page
- api-schema-appendix.md

Unresolved questions:
- whether any public noun family or CLI/API example still teaches stale route or ingest vocabulary

Confidence:
- high only if ingest, API, and CLI contracts can be taught from canon alone

Success criteria:
- definition ingest and public nouns match canon
- the canonical root CLI contract is explicit and test-backed
- stale public vocabulary is removed from the standard target surface

Deliverables:
- ingest alignment
- public API alignment
- root CLI alignment

Milestones:
- ingest nouns aligned
- API surface aligned
- CLI contract aligned

Dependency-critical path:
- ingest contract -> API nouns -> root CLI contract

Ordered work packages:
- align ingest and public noun families
- align public API routes and presenters
- align the root CLI contract and examples

subagents:
- either `no subagents` or bounded ingest/API, CLI contract, or public-docs example slices

Wave plan:
- integrate one public-surface slice at a time, run tests and viable lanes, then review and patch before another wave

Validation checkpoints:
- ingest docs match code
- public route families are explicit
- root CLI examples are current

Required tests:
- ingest/API/CLI unit and integration tests
- all viable e2e lanes

Required docs/examples:
- ingest docs
- CLI/API examples
- onboarding examples for public nouns

Exit evidence:
- public surfaces match canonical docs
- the root CLI contract is explicit and test-backed
- stale public vocabulary is removed

Rollback/stop conditions:
- stop if public noun families are still ambiguous in canon
```

## Phase 5B prompt

```text
Build the approved phase plan for Phase 5B of the redesign landing plan.

Goal:
- land packaging, install/reset/release behavior, final docs cutover, and stale-doc cleanup

Phase-local contract:
- docs/execution/phases/phase-5b-packaging-release-and-docs-cutover.md

Locked implementation surfaces:
- package and script surfaces, install/release docs, root/router docs, and archive cleanup surfaces from the implementation file lock map

Required reads:
- AGENTS.md
- STYLE.md
- current phase page
- docs/execution/maps/file-priority-map.md
- primary redesign pages named by the phase page
- api-schema-appendix.md when package or reset behavior changes public examples

Unresolved questions:
- whether any package, reset, onboarding, or docs-routing behavior still forces implementers into stale packs

Confidence:
- high only if package behavior and canonical routing are explicit enough for clean cutover

Success criteria:
- package/install/reset behavior is explicit and test-backed
- release and onboarding docs match shipped package behavior
- stale guidance is removed or archived so canonical routing stays clean

Deliverables:
- package/install/reset alignment
- release and onboarding alignment
- final docs cutover and archive cleanup

Milestones:
- packaging and install behavior aligned
- release docs aligned
- docs cutover complete

Dependency-critical path:
- package and reset behavior -> release and onboarding docs -> archive cleanup and final routing

Ordered work packages:
- align package, install, and reset behavior
- align release and onboarding docs
- complete docs cutover and archive cleanup

subagents:
- either `no subagents` or bounded package/install, release-docs, or docs cutover and archive cleanup slices

Wave plan:
- integrate one packaging or docs-cutover slice at a time, run smoke checks and docs validators, then review and patch before another wave

Validation checkpoints:
- package/install/reset smoke checks pass
- canonical routers point only to final surfaces
- archive and stale-doc cleanup is intentional

Required tests:
- package/install/reset smoke checks
- docs consistency and validation checks
- all viable e2e lanes when packaging or reset changes can invalidate prior evidence

Required docs/examples:
- release/install docs
- onboarding examples
- archive routing and cutover docs

Exit evidence:
- packaging and release docs match install and reset behavior
- canonical docs route implementers to the final surfaces only
- stale guidance no longer survives as live canonical routing

Rollback/stop conditions:
- stop if package/reset behavior or docs cutover routing is still ambiguous
```
