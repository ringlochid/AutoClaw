# Recover or replan a task

Status: Reference

Use recovery when runtime state needs operator action. Use replan when the current workflow shape no longer fits the work.

## Start with inspection

Before changing anything, inspect:

- the workflow manifest
- the current assignment
- latest relevant checkpoints
- published artifacts
- operator snapshot and trace
- pending human requests or command runs

Do not treat a quiet dispatch as proof that the task is stuck. Read controller state first.

## Retry when

- the assignment shape is still correct
- the failure is recoverable
- a new attempt can make progress with the same criteria and expected outputs

Retry is another attempt at the same shape.

## Replan when

- the current node tree is missing needed work
- the dependency path is wrong
- repeated failures show the assignment shape is wrong
- a parent/root cannot honestly release or block with the current structure

Replan changes shape. It is not a substitute for ordinary retry.

## Block when

- required facts, permissions, tools, or external state are unavailable
- the workflow cannot make honest progress from current evidence
- retrying would repeat the same failure

Blocked closure should have a terminal checkpoint explaining the evidence and blocker.

## Related pages

- [Runtime model](../concepts/runtime-model.md)
- [Capability model](../concepts/capability-model.md)
- [Inspect and control a task](inspect-and-control-a-task.md)
