# Use this pack for implementation

Status: Target

This page explains how to navigate the canonical execution pack. Shared execution policy lives in [AGENTS.md](../../../AGENTS.md). Coding standards live in [STYLE.md](../../../STYLE.md).

## Fast path

1. Read [AGENTS.md](../../../AGENTS.md).
2. Read [STYLE.md](../../../STYLE.md).
3. Identify the active phase in [Phase and gate overview](../phases/overview.md).
4. If stale repo shape still dominates target-facing behavior, start with [Phase 0.5 cleanup and salvage baseline](../phases/phase-0.5-cleanup-and-salvage-baseline.md).
5. Run the pre-implementation review flow from [Phase prompts](../gates/phase-implementation-prompts.md).
6. If the review passes, read the [implementation file lock map](../maps/file-priority-map.md) and the current phase page together.
7. Build the approved phase plan and WBS, including the subagents decision, wave plan, and validation checkpoints.
8. Execute only after plan approval, then run post-implementation review, reset when applicable, and phase-done checks.

## Procedure

1. Read [AGENTS.md](../../../AGENTS.md), [STYLE.md](../../../STYLE.md), [Phase and gate overview](../phases/overview.md), and the current phase page.
2. Read the primary redesign pages named by that phase page before touching code.
3. Read [Implementation file lock map](../maps/file-priority-map.md) to confirm the owned, collateral, and deferred surfaces for the phase.
4. Read named appendix owners when the phase page or redesign pages point to them for exhaustive detail.
5. Start in [Glossary and boundaries](../../redesign/architecture/glossary-and-boundaries.md) if you need to lock vocabulary before reading narrower contract pages.
6. Run the pre-implementation review prompt from [Phase prompts](../gates/phase-implementation-prompts.md).
7. If the review says canon is still incomplete, patch docs first.
8. If the review passes, build the phase WBS and approved plan, including the subagents decision and wave integration loop.
9. Execute only after plan approval.
10. Use [Current implementation docs](../../current/README.md) only for migration truth or shipped-behavior checks.
11. Use repo code and tests after the redesign and current docs pass.
12. Use archive or source packs only when [AGENTS.md](../../../AGENTS.md) fallback rules apply.

## Appendix-owner rule

Use the named appendix owners when exact detail matters:

- API request, response, and nested payload detail -> [../../redesign/interfaces/api-schema-appendix.md](../../redesign/interfaces/api-schema-appendix.md)
- authored workflow, task compose, local replan patch, and schema atom detail -> [../../redesign/workflows/workflow-schema-appendix.md](../../redesign/workflows/workflow-schema-appendix.md)
- prompt section inventory, root usage, and continuation behavior -> [../../redesign/prompt-layer/prompt-resource-usage-appendix.md](../../redesign/prompt-layer/prompt-resource-usage-appendix.md)
- cleanup keep/rewrite/delete/quarantine decisions -> [../maps/repo-salvage-matrix.md](../maps/repo-salvage-matrix.md)

## Stale-removal rule

When current code and target canon disagree:

- treat redesign canon as the target truth
- remove stale target-facing logic and nouns aggressively
- do not preserve parallel legacy behavior unless canon explicitly keeps a compatibility lane

## Doc-gap rule

If implementation work uncovers a required target behavior that canon does not state explicitly:

1. confirm the gap
2. update canonical docs first
3. only then treat the behavior as settled implementation truth

## Phase selection

- use [Phase and gate overview](../phases/overview.md) to pick the active phase
- use Phase 0.5 before Phase 1 when stale repo shape still dominates
- use the current phase page as the sole phase-local contract
- use the current phase page as the sole phase-local delivery contract
- use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map
- use [Progressive e2e workflow lanes](../phases/progressive-e2e-workflow-lanes.md) to know which e2e lanes are mandatory

## Docs generation and validation

If you will change canonical docs, prompt-pack inputs, `docs/redesign/prompt-layer/prompt-catalog.yaml`, or generated prompt pages:

1. run `python scripts/docs/prompt_catalog_tools.py validate` before the change if the tooling is present
2. run the generator after prompt-catalog or prompt-pack input changes
3. rerun validation after the change
4. run `python scripts/docs/docs_freeze_validate.py` before phase closeout
5. keep the generation or validation evidence with the phase

## Current vs redesign rule

If a current page and redesign page disagree, treat that as an expected migration boundary:

- `current/` describes what exists
- `redesign/` describes what to build

## Surface rule

Use this page to navigate the pack. Use [AGENTS.md](../../../AGENTS.md) for shared execution rules and [STYLE.md](../../../STYLE.md) for coding standards.
