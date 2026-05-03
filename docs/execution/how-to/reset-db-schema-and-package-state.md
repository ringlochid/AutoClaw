# Reset DB, schema, and package state

Status: Target

This page defines the canonical reset workflow when a redesign phase changes DB, schema, package, or public-surface truth.

## Use this guide when

- the phase changes DB schema
- the phase changes runtime record truth
- the phase changes package or install behavior
- the phase changes public CLI or API surfaces in a way that requires cleanup or reset

## Procedure

1. Confirm that the current phase triggers the [Reset gate](../gates/reset-gate.md).
2. Record whether the change needs full reset, reinstall, empty-baseline reset, or all three.
3. Reset DB state as required by the phase.
4. Leave the baseline intentionally empty unless the current phase explicitly requires seed data.
5. Reset package or install state as required by the phase.
6. Run the required smoke or integration checks again.
7. Record the reset evidence in the current work package and phase review.

## Phase 0.5 baseline specifics

- remove any carried migration root or packaged migration mirror from the Phase 0.5 baseline
- do not treat repo-root `definitions/*` or packaged definition mirrors as reset authority in Phase 0.5
- minimum Phase 0.5 smoke evidence is: successful DB accessibility after reset and rerun retained infra smoke checks

## Minimum reset evidence

- what changed
- whether DB reset was required
- whether the baseline was intentionally left empty
- whether package reinstall or reset was required
- what smoke checks were rerun
- what cleanup or drop timing remains deferred

## Reset rule

Do not defer a required reset check to the final release phase just because the current phase is inconvenient.

If the current phase changed persistence or install truth, the current phase owns the reset evidence.

Phase 0.5 is the explicit cleanup phase where old schema truth may be discarded intentionally rather than carried forward.

## Related guides

- [Triage a failing phase or workflow lane](triage-a-failing-phase-or-workflow-lane.md)
- [Testing and release checklist](../../redesign/interfaces/testing-and-release-checklist.md)
- [Reset gate](../gates/reset-gate.md)
