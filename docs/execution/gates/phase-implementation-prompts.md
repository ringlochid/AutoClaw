# Phase prompts

Status: Reference

Use these reusable prompts to route redesign implementation work. This file is an implementation-control surface, not a phase-local prompt catalog. Shared agent policy lives in [AGENTS.md](../../../AGENTS.md). Coding standards live in [STYLE.md](../../../STYLE.md).

## Prompt families

The execution pack uses exactly three prompt families:

1. pre-implementation review
2. phase plan
3. post-implementation review

Phase-local goals, deliverables, milestones, work packages, and exit evidence live on the selected current phase page plus the implementation file lock map. Do not mirror that phase-local detail here.

Record the approved phase plan under [../plans/README.md](../plans/README.md), executed validator or test proof under [../evidence/README.md](../evidence/README.md), and review outputs under [../reviews/README.md](../reviews/README.md).

There is no separate execute-mode prompt in this pack. After plan approval, Codex executes using default behavior plus `AGENTS.md`, `STYLE.md`, the current phase page, the implementation file lock map, and the approved phase plan.

The execution pack does not keep a separate repo-global active-phase marker. Pre-implementation review must select the current phase using the phase selection rule in `docs/execution/phases/overview.md` and name that phase page explicitly before planning starts.

Compatibility note: the frozen CLI contract still includes `autoclaw definitions import ...` under Phase 5A.

## Shared router rule

- treat the current phase page as the sole phase-local implementation contract
- treat the current phase page as the sole phase-local delivery contract
- treat [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map
- use [AGENTS.md](../../../AGENTS.md) for shared read order, answer hierarchy, delegation, TDD, and closeout rules
- use [STYLE.md](../../../STYLE.md) for measurable coding and refactor standards
- when the selected phase touches docs tooling under `scripts/docs/*`, include `ruff check scripts/docs` and `mypy scripts/docs` as required scoped gates
- read the primary redesign pages named by the phase page before touching code
- read the required supporting redesign reads named by the phase page when live target semantics, durable decisions, how-to guidance, or tutorial coverage matter
- read the required current-contrast pages named by the phase page when migration truth, current routes, or current package or DB behavior matter
- read the required examples and diagrams named by the phase page when they define behavior, generated surfaces, or evidence flow
- read any appendix owners named by the phase page when exact API, schema, prompt, or payload detail matters
- common appendix owners include `docs/redesign/workflows/workflow-schema-appendix.md`, `docs/redesign/interfaces/api-schema-appendix.md`, and `docs/redesign/prompt-layer/prompt-resource-usage-appendix.md` when the selected phase points there
- when the selected phase changes shipped prompt-source ownership, treat app-owned prompt assets, prompt owner docs, generated prompt examples, prompt-catalog references, and any narrow package-data entry needed to ship those assets as one coordinated surface
- use `docs/execution/maps/redesign-code-landing-map.md` when the selected phase must land target owners, examples, or proof gates in code
- build phase-local goals, success criteria, deliverables, milestones, ordered work packages, and exit evidence from the selected phase page plus the lock map rather than mirroring unrelated phase pages here
- if code work uncovers a silent target contract, update canon before treating the behavior as settled

## Pre-implementation review prompt

```text
All the phases descriptions are in docs/execution.

Run the pre-implementation review for the current redesign phase.

Should read ALL related code, docs including interfaces, examples and diagrams.

Tasks:
1. Select the current phase that owns the blocker and name the current phase
   page.
2. Re-read AGENTS.md, STYLE.md, the current phase page, the implementation
   file lock map, and the primary redesign references named by the phase page.
3. Re-read any required supporting redesign reads, required current-contrast
   pages, required examples, and required diagrams named by the phase page for
   this blocker.
4. Re-read any named appendix owners only when exact API/schema/prompt/payload
   detail matters for the blocking issue.
5. Use `docs/execution/maps/redesign-code-landing-map.md` when the blocker
   concerns whether target owner docs, examples, or proof gates are fully
   represented in code.
6. Decide whether the current blocker is:
   - docs gap
   - code gap
   - stale logic survivor
   - cleanup/reset issue
   - test gap
   - phase mismatch
   - locked-surface mismatch
7. If docs are not decision-complete, stop implementation and list the canon
   fixes required first.
8. If the requested work falls outside the locked implementation surfaces for
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
In plan mode, give me the plan for the current phase.

The read list below is the mandatory minimum read set for the selected phase; add more canon, code, tests, examples, or diagrams when completeness requires it, but do not treat the named reads as optional. The selected current phase page plus `docs/execution/maps/file-priority-map.md` remain authoritative for phase-local requirements, reads, and owned surfaces. Do not treat implementation surfaces as suggestions; if the work needs edits outside them, stop and either patch canon first, re-scope the work package, or move the change to the owning phase.

Subagents are strongly suggested for large phase or stage tasks. You can have at most 25 subagents in one run and at most 5 in one wave. Use WBS-style decomposition and rich context sharing in the subagents briefs, and act as the router, validator, manager, and final gate or fixer.

If there are subagents, all the subagents must read ALL related code, docs including interfaces, examples and diagrams. Follow the `AGENTS.md` subagent brief standard: every slice must declare slice type (`edit` or `review-only`), selected phase, owned surfaces, do-not-edit surfaces, required reads, expected outputs, required tests or validators, dependencies, evidence to return, parent-owned decisions, and stop conditions. Review-only slices must not edit files. The parent must not edit while a wave is running, must wait for the full wave, and must review and revert any out-of-scope or review-only edits before integration. A subagent must not advance work into another phase or later work package on its own.

Read:
- AGENTS.md
- STYLE.md
- the selected current phase page
- docs/execution/maps/file-priority-map.md
- docs/execution/README.md
- the primary redesign pages named by the phase page
- the required supporting redesign reads named by the phase page
- the required current-contrast pages named by the phase page
- the required examples and diagrams named by the phase page
- any named appendix owners when exact API/schema/prompt/payload detail matters,
  including `docs/redesign/workflows/workflow-schema-appendix.md`,
  `docs/redesign/interfaces/api-schema-appendix.md`, and
  `docs/redesign/prompt-layer/prompt-resource-usage-appendix.md` when the
  selected phase points there
- `docs/execution/maps/redesign-code-landing-map.md` when the phase must land
  target owners, examples, or proof gates in code

Tasks:
- restate the phase-local goal, success criteria, deliverables, milestones, and
  dependency-critical path from the selected phase page
- lock the owned and allowed collateral surfaces from the implementation file
  lock map
- define the ordered work packages needed for the selected phase only
- name the plan artifact path under `docs/execution/plans/` and the matching evidence/review artifact paths under `docs/execution/evidence/` and `docs/execution/reviews/`
- define the subagents decision, wave plan, validation checkpoints, required
  tests, required docs/examples, exit evidence, and rollback or stop
  conditions
- if subagents are used, define the slice type, bounded ownership, do-not-edit
  surfaces, evidence-to-return contract, wave safety rule, and phase barrier
  behavior explicitly
- define any required SQLite, Postgres+Docker, package, or reset verification
  lanes explicitly when the phase touches runtime persistence, package-install
  truth, or public API/CLI truth
- do not mirror unrelated phase pages or invent phase-local contract detail
  outside the selected phase page

thinking following:
- Goal
- Phase-local contract
- Locked implementation surfaces
- Required reads
- Unresolved questions
- Confidence
- Success criteria
- Deliverables
- Milestones
- Dependency-critical path
- Ordered work packages
- subagents
- Wave plan
- Validation checkpoints
- Required tests
- Required docs/examples
- Exit evidence
- Rollback/stop conditions
```
