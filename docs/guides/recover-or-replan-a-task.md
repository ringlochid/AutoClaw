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

Good replan triggers:

- fixed workflow evidence shows a required step is missing
- dynamic parent keeps assigning the same failing child shape
- review or verification proves the current criteria are judging the wrong thing
- intent mismatch appears between the user purpose and current node tree
- a failure analyst identifies workflow-shape mismatch rather than weak execution

## Block when

- required facts, permissions, tools, or external state are unavailable
- the workflow cannot make honest progress from current evidence
- retrying would repeat the same failure

Blocked closure should have a terminal checkpoint explaining the evidence and blocker.

## Do not use recovery as design

Recovery and replan are runtime controls. Good definitions should still include the expected ambiguity route:

- workers surface material gaps
- parents route weak evidence to focused children
- roots compare whole-flow evidence with the original purpose
- human requests handle human judgment
- command runs handle long command work

If the same recovery pattern happens often, update the workflow or policy so future runs reach the right route directly.

## Related pages

- [Runtime model](../concepts/runtime-model.md)
- [Capability model](../concepts/capability-model.md)
- [Design workflows and instructions](design-workflows-and-instructions.md)
- [Handle ambiguity and incidents](handle-ambiguity-and-incidents.md)
- [Inspect and control a task](inspect-and-control-a-task.md)
