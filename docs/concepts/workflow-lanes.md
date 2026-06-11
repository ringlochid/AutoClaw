# Workflow lanes

Status: Reference

AutoClaw ships three common workflow shapes.

## Minimal

Use the minimal lane for one bounded implementation step with a fast proof loop.

- one focused worker path
- small scope
- quickest way to prove local launch and runtime materialization

## Normal

Use the normal lane for standard delivery work with a clearer review handoff.

- one implementation track
- explicit review before closure
- good default when one round of review should happen before release

## Maximal

Use the maximal lane for larger work that needs multiple coordinated tracks and shared closure evidence.

- multiple workstreams
- broader validation
- final coordination before release

## Exact examples

- [Guide examples for workflows](../guides/examples/workflows/minimal.md)
- [Reference workflow examples](../reference/definitions/workflows/README.md)
