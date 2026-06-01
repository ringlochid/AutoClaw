# Progressive e2e workflow lanes

Status: Reference

This page defines the canonical minimal, normal, and maximal end-to-end workflow lanes for design implementation.

## Lanes

### Minimal lane

- workflow reference: [Minimal workflow reference](../../../design/v1/workflows/examples/minimal.md)
- proving goal: prompt/runtime/bootstrap and one parent-owned leaf execution path
- minimum evidence:
  - task create/start succeeds
  - one bounded worker dispatch emits the required artifacts
  - parent/root reread, `release_green`, and terminal close path succeed

### Normal lane

- workflow reference: [Normal workflow reference](../../../design/v1/workflows/examples/normal.md)
- proving goal: parent-owned execution subtree, parent-first verification, and bounded root closure
- minimum evidence:
  - execution subtree runs
  - parent/root control-tool decisions and redispatch path are visible
  - parent verification consumes the required evidence
  - root closure path completes

### Maximal lane

- workflow reference: [Maximal workflow reference](../../../design/v1/workflows/examples/maximal.md)
- proving goal: multiple subtrees plus review and replan-ready control
- minimum evidence:
  - multiple subtrees execute
  - parent/root reread and control-tool decisions aggregate current subtree outcomes
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

## Non-e2e proof rule

These workflow lanes are necessary but not sufficient when a phase changes runtime persistence, package-install truth, or public API/CLI truth.

In those cases, the current phase page and reset gate must also name:

- SQLite local smoke when viable
- Postgres + Docker strong verification when viable
- package or reset smoke when applicable
