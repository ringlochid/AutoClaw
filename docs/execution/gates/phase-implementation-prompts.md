# Phase prompts

Status: Reference

Use these reusable prompts to route redesign implementation work. This file is an implementation-control surface, not a phase-local prompt catalog. Shared agent policy lives in [AGENTS.md](../../../AGENTS.md). Coding standards live in [STYLE.md](../../../STYLE.md).

## Prompt families

The execution pack uses exactly three prompt families:

1. pre-implementation review
2. phase plan
3. post-implementation review

Phase-local goals, deliverables, milestones, work packages, and exit evidence live on the selected current phase page plus the implementation file lock map. Do not mirror that phase-local detail here.

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
- common appendix owners include `docs/redesign/workflows/workflow-schema-appendix.md`, `docs/redesign/interfaces/api-schema-appendix.md`, and `docs/redesign/prompt-layer/prompt-resource-usage-appendix.md` when the selected phase points there
- build phase-local goals, success criteria, deliverables, milestones, ordered work packages, and exit evidence from the selected phase page plus the lock map rather than mirroring unrelated phase pages here
- if code work uncovers a silent target contract, update canon before treating the behavior as settled

## Pre-implementation review prompt

```text
Run the pre-implementation review for the current redesign phase.

Tasks:
1. Select the current phase that owns the blocker and name the current phase
   page.
2. Re-read AGENTS.md, STYLE.md, the current phase page, the implementation
   file lock map, and the primary redesign references named by the phase page.
3. Re-read any named appendix owners only when exact API/schema/prompt/payload
   detail matters for the blocking issue.
4. Decide whether the current blocker is:
   - docs gap
   - code gap
   - stale logic survivor
   - cleanup/reset issue
   - test gap
   - phase mismatch
   - locked-surface mismatch
5. If docs are not decision-complete, stop implementation and list the canon
   fixes required first.
6. If the requested work falls outside the locked implementation surfaces for
   the phase, stop and say whether the next action is:
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

## Phase-plan prompt

```text
Build the plan for the current phase.

Use:
- AGENTS.md
- STYLE.md
- the selected current phase page
- docs/execution/maps/file-priority-map.md
- docs/execution/README.md
- the primary redesign pages named by the phase page
- any named appendix owners when exact API/schema/prompt/payload detail matters,
  including `docs/redesign/workflows/workflow-schema-appendix.md`,
  `docs/redesign/interfaces/api-schema-appendix.md`, and
  `docs/redesign/prompt-layer/prompt-resource-usage-appendix.md` when the
  selected phase points there

Tasks:
- restate the phase-local goal, success criteria, deliverables, milestones, and
  dependency-critical path from the selected phase page
- lock the owned and allowed collateral surfaces from the implementation file
  lock map
- define the ordered work packages needed for the selected phase only
- define the subagents decision, wave plan, validation checkpoints, required
  tests, required docs/examples, exit evidence, and rollback or stop
  conditions
- do not mirror unrelated phase pages or invent phase-local contract detail
  outside the selected phase page

Return using this structure:
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
