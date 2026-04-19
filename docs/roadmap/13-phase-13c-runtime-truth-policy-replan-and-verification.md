# 13C — Phase 13C: Runtime Truth, Policy/Replan, and Verification Closeout

## Goal

Finish the runtime-truth cleanup after persistence and launch are already clean.

Phase 13C makes runtime read surfaces honest, aligns policy/replan boundaries with the documented model, and closes the phase with final verification.

## Problem statement

After persistence truth and launch contract are fixed, the remaining risk is runtime/control ambiguity:

- inspect/bundle surfaces may still reflect legacy thinking
- policy may still blur into the wrong layer
- replan may still lack explicit remint rules
- bridge verification may still be unproven end-to-end

13C closes those gaps.

## Scope

### In scope

1. worker bundle / inspect cleanup
2. runtime truth derived from real runtime tables
3. policy boundary cleanup
4. replan remint rule cleanup
5. fresh live bridge smoke verification
6. final docs/test/runbook closeout

### Out of scope

- persistence-truth cleanup already completed by 13A
- launch-contract cleanup already completed by 13B

## Canonical gaps owned by 13C

13C closes these gaps from Phase 13:

- A2
- E1 (runtime-side parts)
- E2
- E3
- F1
- F2
- F3
- H1
- H2
- H3

## Required runtime/control decisions

### 1. Worker bundle target contract

Worker bundle must contain:

- flow
- task
- compiled_plan
- current_node
- current_attempt
- current_session
- current_manifest
- task_compose
- recent_checkpoints
- approvals
- recent_manifests
- context_items
- events

Worker bundle must not expose persisted runtime-container truth.

### 2. Policy boundary

Required rule:

- reusable policy meaning remains workflow / compiled-plan-node level
- task compose carries only small task-scoped start facts and launch constraints
- runtime state carries runtime-time facts only

### 3. Replan remint rule

Required rule:

- structural-only replan that changes flow topology/execution plan but not launch binding -> new flow revision only
- replan that changes starting workflow, entrypoint, task-owned roots/bindings, context refs, or explicit skill dependencies -> mint a new task compose

This must exist in code/tests/docs, not just prose. Replan API results should surface whether task compose was reminted or retained.

### 4. Bridge verification evidence

13C must record fresh bridge closeout evidence in a stable place.

Acceptable locations:

- an e2e/runbook doc
- a dedicated verification section
- roadmap closeout notes

## Concrete code surface inventory

13C should expect to touch, at minimum:

- inspect/bundle schemas
- presenters/read models
- inspect/bundle routes
- policy/replan lifecycle code
- runtime API tests
- bridge/e2e/runbook notes or tests
- final roadmap/docs closeout notes

## Explicit implementation plan

### Step 1. Rewrite runtime read surfaces around runtime truth

Implement:

- worker bundle / inspect surfaces derive live state from real runtime tables
- task compose appears as launch truth, not runtime-container persistence

Must be true before moving on:

- runtime read surfaces no longer depend on fake persisted runtime truth

### Step 2. Lock policy and replan boundaries

Implement:

- policy remains workflow/compiled-plan-node level
- task compose remains launch-bound
- replan remint rule is explicit in code and tests

Must be true before moving on:

- policy/replan boundaries are explicit enough that future changes cannot drift silently

### Step 3. Run final verification closeout

Implement:

- fresh live bridge smoke
- focused runtime/control tests
- final doc/runbook closeout

Must be true to finish 13C:

- bridge smoke passes
- focused tests pass
- evidence is recorded somewhere stable
- it is honest to say the runtime/control gaps owned by 13C are closed

## Done criteria

13C is only done when all of these are true:

- worker bundle / inspect surfaces reflect task compose plus derived runtime state
- policy and replan boundaries match the documented model
- structural-only replan vs launch-binding-changing replan is explicit in code/tests/docs
- fresh live bridge smoke passes and is recorded
- focused tests pass
- final docs are honest about the implemented state
