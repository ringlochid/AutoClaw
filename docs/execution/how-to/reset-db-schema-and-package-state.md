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
2. Record whether the change needs migration, full reset, reinstall, reseed, or all three.
3. Reset schema or rerun migrations as required by the phase.
4. Reseed/bootstrap required definitions or baseline data when the reset would leave the system empty.
5. Reset package or install state as required by the phase.
6. Run the required smoke or integration checks again.
7. Record the reset evidence in the current work package and phase review.

## Minimum reset evidence

- what changed
- whether DB reset was required
- whether schema migration was required
- whether reseed/bootstrap was required
- whether package reinstall or reset was required
- what smoke checks were rerun
- what cleanup or drop timing remains deferred

## Reset rule

Do not defer a required reset check to the final release phase just because the current phase is inconvenient.

If the current phase changed persistence or install truth, the current phase owns the reset evidence.

Phase 0.5 is the explicit cleanup phase where old schema truth may be discarded intentionally rather than migrated forward.

## Related guides

- [Triage a failing phase or workflow lane](triage-a-failing-phase-or-workflow-lane.md)
- [Testing and release checklist](../../redesign/interfaces/testing-and-release-checklist.md)
- [Reset gate](../gates/reset-gate.md)
