# Supporting prompts

Status: Reference

Use these prompts while a phase is still in progress. Shared execution policy lives in [AGENTS.md](../../../AGENTS.md). Coding standards live in [STYLE.md](../../../STYLE.md).

These are narrow helper snippets. They do not create extra phase-local authority or a fourth execute-mode prompt family.

## Build the phase WBS

```text
Build the WBS for the current redesign phase.

Tasks:
- define the deliverables and milestones
- decompose the phase into ordered work packages
- name dependencies between work packages
- name the locked implementation surfaces for each work package
- name the required tests and docs per work package
- name unresolved questions, the dependency-critical path, and validation checkpoints
- name the subagents decision for each work package and the parent-owned decisions
- define exit evidence and rollback or stop conditions

Before stopping:
- list the work packages in dependency order
- list the locked implementation surfaces
- list the subagents decisions
- list the validation checkpoints
- list the exit evidence
```

## Hard-reset classification for this phase

```text
Run the Phase 0.5 hard-reset classification.

Tasks:
- classify each major subsystem as delete now, retain infra shell only, or plugin rebuild
- justify every retained infra shell explicitly
- name the later owner phase only when a retained infra shell exists to support it
- remove any ambiguous or compatibility-minded survivor decision
```

## Test-first setup for the current work package

```text
Set up test-first work for the current redesign work package.

Tasks:
- identify the behavior or contract that is changing
- identify the primary locked implementation surfaces and the primary tests that should expose the gap
- add or update failing or gap-revealing tests first where practical
- if failing-first is not practical, record the exact reason and still add the tests before work-package closeout

Before stopping:
- list the tests added or updated
- list what each test is expected to prove
- list any remaining missing coverage
```

## Docs-gap review

```text
Review whether the blocking issue is a docs gap rather than a code gap.

Tasks:
- identify the exact unanswered behavior
- name the canonical page that should own it
- confirm whether nearby docs conflict or merely omit the detail
- stop code execution if the target contract is still silent

Return:
- docs gap or not
- owning page
- exact wording or contract area that needs patching
```

## Locked-surface reroute review

```text
Review whether the requested work falls outside the selected phase's locked
implementation surfaces.

Tasks:
- compare the requested change against the current phase page and the implementation file lock map
- identify which part is owned, collateral, deferred, or out of phase
- decide whether the next action is re-scope, canon patch, or move to another phase

Return:
- in scope or out of scope
- exact locked-surface conflict, if any
- exact next action
```

## Plugin rebuild boundary review

```text
Review the plugin boundary for Phase 0.5 or Phase 4B.

Tasks:
- define the target-only plugin tool inventory from canon first
- identify which current plugin utilities are reusable
- identify which current tools and tests must be removed
- confirm the plugin is treated as a near-greenfield rebuild
```

## Subagents work package brief

```text
Prepare a bounded subagents work package brief.

Tasks:
- name the exact owned surfaces
- name the required docs, tests, and code the subagents slice must read before editing
- name the expected outputs
- name required tests and validators
- name required evidence to return
- name dependencies or blockers
- confirm which decisions remain with the parent Codex agent

Before stopping:
- output the bounded ownership brief
- output the evidence checklist
```

## Post-subagents wave integration review

```text
Review the results of the latest subagents wave before starting another wave.

Tasks:
- compare returned changes against the locked implementation surfaces
- confirm whether each subagents slice stayed inside owned surfaces
- confirm whether the returned evidence matches the requested tests and validators
- identify integration conflicts or missing follow-up

Return:
- keep or patch
- exact integration findings
- exact follow-up work before another wave
```

## Validation and patch follow-up

```text
Run the validation-and-patch follow-up for the current work package.

Tasks:
- read the latest review findings and test or validator failures
- map each failure back to the approved phase plan and owning work package
- patch only the missing items needed to satisfy the validation checkpoint
- rerun the relevant tests, validators, and review prompt

Before stopping:
- list the fixes made
- list the tests or validators rerun
- list any remaining blockers
```

## Recenter on the current work package

```text
Recenter execution on the already-approved current work package only.

This does not create a separate execute-mode prompt family.
It only restates the approved execution contract.

Tasks:
- use the current phase page, implementation file lock map, approved plan, AGENTS.md, and STYLE.md as the implementation contract
- use any appendix owners named by the current phase page when exact API/schema/prompt detail matters
- implement only the current work-package behavior needed to turn the tests green
- refactor the touched area when thresholds or stale semantics require it
- update docs and examples required by the current work package
- update named appendix owners when the changed behavior affects exhaustive API/schema/prompt detail

Before stopping:
- list the changed surfaces
- list the tests and validators that now pass
- list any still-failing tests, validators, or blockers
```

## Migration and reset safety review

```text
Review the current work for migration and reset safety.

Check:
- DB schema changes
- runtime record changes
- package-install path changes
- public CLI or API changes
- old-to-new field mapping or compatibility timing
- whether reset behavior and cleanup/drop timing are documented

Return:
- risk list
- required reset or migration fixes
```

## Clean-code review for touched code

```text
Review the touched code against STYLE.md.

Check:
- functions over 80 non-comment, non-blank lines
- touched files over 400 lines without a split review
- mixed-responsibility files
- vague names
- hidden side effects
- stale abstractions left alive to avoid refactoring
- async misuse
- ORM-loading or N+1 risk on fanout paths

Return:
- findings
- exact files or functions to refactor now
- which issues can remain only with an explicit phase-bounded exception
```

## Continue after failed review or failed e2e

```text
The current phase is not complete.

Do not start a new phase.
Continue the same phase only.

Tasks:
- read the latest review findings and test or e2e failures
- map each failure back to the approved phase plan and owning work package
- check whether the failure indicates a locked-surface mismatch
- fix only the missing items for this phase
- rerun the relevant review, reset, and verification flows
```
