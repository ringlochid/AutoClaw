# Progressive e2e workflow lanes

Status: Target

This page defines the canonical minimal, normal, and maximal end-to-end workflow lanes for redesign implementation.

## Lanes

### Minimal lane

- workflow reference: [Minimal workflow reference](../../redesign/workflows/examples/minimal.md)
- proving goal: prompt/runtime/bootstrap and one parent-owned leaf execution path
- minimum evidence:
  - task create/start succeeds
  - one bounded worker dispatch emits the required artifacts
  - parent-gate release succeeds

### Normal lane

- workflow reference: [Normal workflow reference](../../redesign/workflows/examples/normal.md)
- proving goal: parent-owned execution subtree, parent-first verification, and bounded root closure
- minimum evidence:
  - execution subtree runs
  - parent gate decisions are visible
  - parent verification consumes the required evidence
  - root closure path completes

### Maximal lane

- workflow reference: [Maximal workflow reference](../../redesign/workflows/examples/maximal.md)
- proving goal: multiple subtrees plus review and replan-ready control
- minimum evidence:
  - multiple subtrees execute
  - parent gate aggregates subtree outcomes
  - review outputs, when authored, are assembled from current subtree evidence
  - replan and boundary handling remain coherent

## Progressive phase matrix

| Phase     | Required lanes                                       |
| --------- | ---------------------------------------------------- |
| Phase 0   | none                                                 |
| Phase 0.5 | none                                                 |
| Phase 1   | none unless a lane is already viable in preview form |
| Phase 2   | minimal when viable                                  |
| Phase 3   | minimal + normal when viable                         |
| Phase 4A  | minimal + normal when viable                         |
| Phase 4B  | minimal + normal + maximal when viable               |
| Phase 5A  | all viable lanes                                     |
| Phase 5B  | all viable lanes plus package/install/DB/reset smoke |
