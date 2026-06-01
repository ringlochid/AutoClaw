# Use this pack for implementation

Status: Reference

This page explains how to navigate the canonical execution pack. Shared execution policy lives in [AGENTS.md](../../../../AGENTS.md). Coding standards live in [STYLE.md](../../../../STYLE.md).

## Fast path

1. Read [AGENTS.md](../../../../AGENTS.md).
2. Read [STYLE.md](../../../../STYLE.md).
3. Select the current phase using the phase-selection rule in [Phase and gate overview](../phases/overview.md).
4. If stale repo shape still dominates target-facing behavior, start with [Phase 0.5 total code hard reset baseline](../phases/phase-0.5-cleanup-and-salvage-baseline.md).
5. Run the pre-implementation review flow from [Phase prompts](../gates/phase-implementation-prompts.md).
6. If the review passes, read the [implementation file lock map](../maps/file-priority-map.md) and the current phase page together.
7. Read every required supporting design page, required current-contrast page, required example, and required diagram named by the current phase page.
8. Use the [Design-to-code landing map](../maps/design-code-landing-map.md) when the phase must land design owners, supporting live references, examples, tutorials, or proof gates in code.
9. Build the approved phase plan and WBS, including the subagents decision, wave plan, validation checkpoints, and any required DB or package verification lanes, and record the approved artifact under [Plans home](../plans/README.md).
10. Execute only after plan approval, record validator or test output under [Evidence home](../evidence/README.md), and then run post-implementation review, reset when applicable, and phase-done checks.

## Execution record home

- [Plans home](../plans/README.md) stores approved phase plans and WBS artifacts.
- [Evidence home](../evidence/README.md) stores executed validator, test, gate, reset, and smoke evidence.
- [Reviews home](../reviews/README.md) stores mandatory review outputs, closeout reviews, and explicit exceptions.

## Phase 0-3 local-tool-first rule

- treat Phase 0-3 as one-process local-tool-first execution
- MQ or distributed-safe compatibility is a non-goal note until canon explicitly reopens it
- exact case-sequence timing and sync/async ownership belong to the owning Phase 2 or Phase 3 page plus the named owner docs, not shared Phase 0 execution prose

## Execution artifact header

Use one exact top-of-file execution-record block immediately after `Status:` on phase plans, evidence artifacts, mandatory reviews, and historical summaries:

```text
selected phase: ...
current phase page: ...
selected work packages: ...
summary-only: no|yes
delegated slices: none|listed
```

When delegated slices are listed, append one contiguous four-line block per slice in this exact order: `slice id:`, `slice type:`, `owned surfaces:`, `touched surfaces:`.

Use `summary-only: no` for authoritative phase-scoped artifacts.

Use `summary-only: yes` for historical artifacts, and keep their `## Authoritative replacements` links truthful:

- if the historical artifact still belongs to one selected phase, keep the real selected phase, current phase page, and selected work packages
- if the historical artifact is cross-phase or aggregate only, use `selected phase: none`, `current phase page: none`, and `selected work packages: none`

Cross-phase program summaries follow the same `summary-only: yes` rule as aggregate closeout artifacts, cannot substitute for phase-scoped closure, and should be deleted once the authoritative phase-scoped replacements and router pages make them redundant.

## Procedure

1. Read [AGENTS.md](../../../../AGENTS.md), [STYLE.md](../../../../STYLE.md), [Phase and gate overview](../phases/overview.md), and the selected current phase page.
2. Read the primary design pages named by that phase page before touching code.
3. Read the required supporting design reads named by the current phase page when they sharpen live target semantics, durable decisions, onboarding, recovery, or teaching coverage for the blocker.
4. Treat any named layer index page, machine catalog, generated inventory, or reference-only historical search router as required when the blocker involves exact routing, exact prompt-family ownership, or stale-vocabulary cleanup.
5. Read [Implementation file lock map](../maps/file-priority-map.md) to confirm the owned, collateral, and deferred surfaces for the phase.
6. Read the required current-contrast pages named by the current phase page when migration truth, current routes, or current package or DB behavior matters.
7. Read the required examples and diagrams named by the current phase page when they define behavior, generated surfaces, or evidence flow.
8. Read named appendix owners when the phase page or design pages point to them for exhaustive detail.
9. If the blocker depends on exact case-sequence timing or sync/async ownership, route that detail to the owning Phase 2 or Phase 3 page before planning.
10. Start in [Glossary and boundaries](../../../design/v1/architecture/glossary-and-boundaries.md) if you need to lock vocabulary before reading narrower contract pages.
11. Run the pre-implementation review prompt from [Phase prompts](../gates/phase-implementation-prompts.md).
12. If the review says canon is still incomplete, patch docs first.
13. If the review passes, use the [Design-to-code landing map](../maps/design-code-landing-map.md) to confirm target owners, supporting live references, examples, tutorials, historical search routers, and proof gates for the phase.
14. If the review passes, build the phase WBS and approved plan, including the subagents decision and wave integration loop.
15. Execute only after plan approval.
16. Use [Current implementation docs](../../../current/v1/README.md) only for migration truth or shipped-behavior checks.
17. Use repo code and tests after the design and current docs pass.
18. Use archive or source packs only when [AGENTS.md](../../../../AGENTS.md) fallback rules apply.

## Appendix-owner rule

Use the named appendix owners when exact detail matters:

- API request, response, and nested payload detail -> [../../design/v1/interfaces/api-schema-appendix.md](../../../design/v1/interfaces/api-schema-appendix.md)
- authored workflow, task compose, local replan patch, and schema atom detail -> [../../design/v1/workflows/workflow-schema-appendix.md](../../../design/v1/workflows/workflow-schema-appendix.md)
- prompt section inventory, root usage, and continuation behavior -> [../../design/v1/prompt-layer/prompt-resource-usage-appendix.md](../../../design/v1/prompt-layer/prompt-resource-usage-appendix.md)
- cleanup hard-reset decisions -> [../maps/repo-salvage-matrix.md](../maps/repo-salvage-matrix.md)
- design-owner landing coverage, required supporting design reads, required examples, tutorials, and proof gates -> [../maps/design-code-landing-map.md](../maps/design-code-landing-map.md)

## Stale-removal rule

When current code and target canon disagree:

- treat design canon as the target truth
- remove stale target-facing logic and nouns aggressively
- do not preserve parallel legacy behavior unless canon explicitly keeps a compatibility lane

## Doc-gap rule

If implementation work uncovers a required target behavior that canon does not state explicitly:

1. confirm the gap
2. update canonical docs first
3. only then treat the behavior as settled implementation truth

## Phase selection

- use [Phase and gate overview](../phases/overview.md) to select the current phase for the bounded work package
- the execution pack does not keep a separate repo-global active-phase marker
- record the selected phase explicitly in the approved plan before execution
- use Phase 0.5 before Phase 1 when stale repo shape still dominates and the current code cannot be trusted
- use the current phase page as the sole phase-local contract
- use the current phase page as the sole phase-local delivery contract
- use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map
- use [Progressive e2e workflow lanes](../phases/progressive-e2e-workflow-lanes.md) to know which e2e lanes are mandatory

## Docs generation and validation

If you will change app-owned shipped prompt assets, canonical prompt docs, `docs-internal/design/v1/prompt-layer/prompt-catalog.yaml`, or generated prompt pages:

1. run `python -m scripts.docs.prompt_catalog.cli validate` before the change if the tooling is present
2. run the generator after prompt-asset, prompt-catalog, or other prompt-generation input changes
3. rerun validation after the change
4. run `python -m scripts.docs.docs_freeze.cli` before phase closeout
5. if the slice touched `scripts/docs/*`, run `ruff check scripts/docs` and `mypy scripts/docs`
6. record the generation or validation evidence under [Evidence home](../evidence/README.md) for the current slice

## Current vs design rule

If a current page and design page disagree, treat that as an expected migration boundary:

- `current/` describes what exists
- `design/` describes what to build

## Completeness rule

If the selected phase changes target behavior, do not stop at owner docs only.

Read and track:

- the required supporting design reads named by the phase page
- any named layer index pages, machine catalogs, generated inventories, and reference-only historical search routers needed for the blocker
- the required current-contrast pages named by the phase page
- the required examples and diagrams named by the phase page
- the corresponding rows in [Design-to-code landing map](../maps/design-code-landing-map.md)

The selected phase is not ready to claim done unless the required design owners, required supporting design reads, required examples or diagrams, and required proof gates for that phase are all covered explicitly.

## Surface rule

Use this page to navigate the pack. Use [AGENTS.md](../../../../AGENTS.md) for shared execution rules and [STYLE.md](../../../../STYLE.md) for coding standards.
