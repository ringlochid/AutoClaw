# Phase and gate overview

Status: Target

This page is the high-level redesign landing roadmap. Shared execution policy lives in [AGENTS.md](../../../AGENTS.md). Coding standards live in [STYLE.md](../../../STYLE.md).

## Shared lifecycle

Every phase follows the same high-level lifecycle:

1. run pre-implementation review
2. patch canon first if the review finds a docs gap
3. read the current phase page plus the implementation file lock map
4. build the phase WBS and approved plan while Codex is in Plan Mode
5. make an explicit subagents decision, wave plan, and validation loop
6. execute the approved work packages
7. run post-implementation review, reset when applicable, and phase-done checks before closing the phase

There is no separate execute-mode prompt in this pack. Execution starts only after the phase plan is approved.

## Phase selection rule

The execution pack does not keep a separate repo-global active-phase marker.

For each bounded work package:

1. select the phase that owns the next blocking redesign delta
2. prefer the earliest phase whose target contract and locked surfaces are still required to land that blocker safely
3. use Phase 0.5 before Phase 1 when stale repo shape, reset baseline ambiguity, stale tests, or plugin-boundary drift still dominate
4. record the selected phase explicitly in the approved plan

In the rest of this pack, `current phase page` means the selected phase page for the approved work package.

## Phase authority rule

- the current phase page is the sole phase-local implementation contract
- the current phase page is the sole phase-local delivery contract
- the implementation file lock map is the canonical owned-surface map across phases
- reusable prompts and gates must reference the phase page rather than silently re-defining it
- when a phase page names appendix owners, use them for exhaustive API/schema/prompt detail
- each phase page must name implementation surfaces, do-not-edit surfaces, subagents rules, a wave integration loop, a mandatory checklist, success criteria, deliverables, work packages, exit evidence, and kill-list terms

## Phase order

| Phase     | Focus                                                                     | Primary page                                                       |
| --------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Phase 0   | canonical docs root, root instruction surfaces, execution pack, docs tooling | [Phase 0](phase-0-docs-contract-freeze-and-setup.md)            |
| Phase 0.5 | cleanup baseline, fresh schema reset, test salvage, and plugin rebuild    | [Phase 0.5](phase-0.5-cleanup-and-salvage-baseline.md)             |
| Phase 1   | authoring model and compiler rewrite                                      | [Phase 1](phase-1-authoring-and-compiler-rewrite.md)               |
| Phase 2   | prompt, manifest, artifact, and bootstrap rewrite                         | [Phase 2](phase-2-prompt-manifest-artifact-bootstrap.md)           |
| Phase 3   | runtime records, parent/root review, closure, and replan rewrite          | [Phase 3](phase-3-runtime-parent-review-and-replan.md)             |
| Phase 4A  | OpenClaw gateway, session, continuity, and worker-lane integration         | [Phase 4A](phase-4a-openclaw-gateway-session-and-continuity.md)    |
| Phase 4B  | watchdog, operator/plugin lanes, and support-state readbacks               | [Phase 4B](phase-4b-watchdog-operator-plugin-and-support-state.md) |
| Phase 5A  | definition ingest, public API, and root CLI contracts                      | [Phase 5A](phase-5a-definition-ingest-api-and-cli.md)              |
| Phase 5B  | packaging, release, install/reset, docs cutover, and stale-doc cleanup     | [Phase 5B](phase-5b-packaging-release-and-docs-cutover.md)         |

## Progressive e2e rule

Use [Progressive e2e workflow lanes](progressive-e2e-workflow-lanes.md) to decide when minimal, normal, and maximal e2e lanes become mandatory.

## Related execution surfaces

- [Current-to-target mapping](../maps/current-to-target-mapping.md)
- [Implementation file lock map](../maps/file-priority-map.md)
- [Mandatory review gate](../gates/mandatory-review-gate.md)
- [Reset gate](../gates/reset-gate.md)
- [Verification prompts](../gates/verification-prompts.md)

## Surface rule

Use this page for phase sequence only. Use [AGENTS.md](../../../AGENTS.md) for shared policy, [STYLE.md](../../../STYLE.md) for coding standards, and the phase pages for phase-local requirements.
