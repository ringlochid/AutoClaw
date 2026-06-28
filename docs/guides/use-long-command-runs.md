# Use long command runs

Status: Reference

Use command runs for controller-managed long-running command work. Do not use them for ordinary quick shell commands.

Ordinary inline commands should finish comfortably under about two minutes. If a command is likely to exceed that, use a command-run-enabled policy or redesign the assignment so the dispatch does not stall.

## Use a command run when

- command work is expected to outlive a normal dispatch
- the operator may need progress, logs, terminal state, or cancellation
- the task should wait on command completion without losing controller truth

## Do not use a command run when

- a normal command should finish quickly
- the node only needs human judgment
- the command would expose secrets or private data outside the task boundary
- the workflow should be split into smaller assignments instead

## Operator follow-up

Operators can inspect command runs, read logs when a log ref exists, and request cancellation of the current active command run without cancelling the whole task.

## Related pages

- [Capability model](../concepts/capability-model.md)
- [Operator model](../concepts/operator-model.md)
- [Inspect and control a task](inspect-and-control-a-task.md)
