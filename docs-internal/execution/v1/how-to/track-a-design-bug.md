# Track a design bug

Status: Reference

This page defines the canonical bug-tracking template and workflow for design implementation failures.

## Procedure

1. Name the failing phase and contract area.
2. Record the exact workflow lane, test, or manual path that failed.
3. Capture reproduction steps and the expected evidence.
4. Capture the actual evidence and the first failing boundary.
5. Link the bug to the canonical design page that should define the behavior.
6. Route the bug to the likely owning phase or subsystem.

## Bug template

```yaml
bug:
  title: string
  phase: phase_0 | phase_0_5 | phase_1 | phase_2 | phase_3 | phase_4 | phase_5
  contract_area: authoring | compiler | prompt | manifest | runtime | review | gateway | watchdog | ingest | api | cli | package
  workflow_lane: minimal | normal | maximal | none
  reproduction_steps:
    - step
  expected_evidence:
    - evidence item
  actual_evidence:
    - evidence item
  canonical_doc_ref: path/to/canonical/page.md
  likely_owner: compiler | runtime | gateway | ingest | package | docs
  likely_issue_type: code_bug | contract_gap | stale_logic | missing_test | quality_gate_failure | reset_issue
```

## Evidence checklist

- current phase
- current branch or change set under review
- failing test or workflow lane
- logs, checkpoints, manifests, or prompt artifacts as applicable
- whether the failure happened before or after a reset, migration, or package step

## Routing rule

- contract gap -> update canonical docs first
- code bug -> route to the current owning phase prompt
- stale logic survivor -> run stale-logic search and reopen the current phase
- cleanup-baseline issue -> reopen Phase 0.5 when stale repo shape, stale contract tests, migration-history replacement, or plugin rebuild boundary is the real source
- missing test -> route through the test-writing prompt
- quality-gate failure -> route through the repo-quality-gate prompt and code-quality gate
- reset issue -> route through the reset gate and reset how-to

## Related guides

- [Triage a failing phase or workflow lane](triage-a-failing-phase-or-workflow-lane.md)
- [Reset DB, schema, and package state](reset-db-schema-and-package-state.md)
- [Progressive e2e workflow lanes](../phases/progressive-e2e-workflow-lanes.md)
