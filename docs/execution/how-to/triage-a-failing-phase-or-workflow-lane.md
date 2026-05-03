# Triage a failing phase or workflow lane

Status: Target

This page defines the canonical triage workflow for a failed phase gate, failed test, or failed minimal, normal, or maximal workflow lane.

## Procedure

1. Identify the failing phase and failing gate or lane.
2. Classify the failure by contract area.
3. Decide whether it is a contract gap, code bug, stale logic survivor, missing test, cleanup baseline issue, quality-gate failure, or reset issue.
4. Gather the required evidence.
5. Route the failure to the correct prompt family, phase review, or reset guide.

## Contract-area classification

- authoring or compiler
- prompt, manifest, or artifact
- runtime, review, or replan
- gateway, session, watchdog, or monitor
- ingest, API, CLI, or package

## Failure-type rule

- contract gap:
  - canonical docs do not answer the behavior clearly enough
- code bug:
  - docs are clear but code or test behavior is wrong
- stale logic survivor:
  - older core logic still survives in parallel
- cleanup baseline issue:
  - stale repo shape, stale contract tests, migration-history replacement, or plugin rebuild boundary is not actually settled yet
- missing test:
  - required unit, integration, or e2e lane is absent or too weak
- quality-gate failure:
  - required repo-native lint, type, build, or test gate failed or a clean-code review found unresolved touched-area refactor issues
- reset issue:
  - DB, schema, package, or public-surface reset behavior failed or was undocumented

## Routing

- failed phase review -> rerun the current phase only after fixing the review findings
- failed code quality gate -> use the code-quality gate and rerun the current phase quality checks
- failed reset gate -> use [Reset DB, schema, and package state](reset-db-schema-and-package-state.md)
- failed minimal, normal, or maximal lane -> use [Progressive e2e workflow lanes](../phases/progressive-e2e-workflow-lanes.md) plus the current phase plan and post-review prompts
- contract gap -> update the canonical redesign docs before continuing implementation
- cleanup baseline issue -> route to [Phase 0.5 total code hard reset baseline](../phases/phase-0.5-cleanup-and-salvage-baseline.md), [Cleanup and salvage checklist](../gates/cleanup-and-salvage-checklist.md), and [Repo salvage matrix](../maps/repo-salvage-matrix.md)

## Minimum evidence to gather

- failing phase
- failing gate or lane
- failing command or workflow path
- expected result
- actual result
- logs, manifests, checkpoints, prompt artifacts, or package/install evidence as applicable

## Related guides

- [Track a redesign bug](track-a-redesign-bug.md)
- [Reset DB, schema, and package state](reset-db-schema-and-package-state.md)
- [Phase and gate overview](../phases/overview.md)
- [Progressive e2e workflow lanes](../phases/progressive-e2e-workflow-lanes.md)
