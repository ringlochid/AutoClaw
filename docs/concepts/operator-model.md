# Operator model

Status: Reference

Operators inspect and steer running tasks. They use read and control surfaces over controller-owned runtime state.

An operator is not the worker and not the controller. The operator is the trusted human or tool principal that can inspect task state, resolve waits, and apply recovery controls.

## What operators inspect

Operators usually start from:

- runtime task list and task readbacks
- task-root files such as workflow manifest, assignment, checkpoints, and artifacts
- operator snapshot for current state and top actionable items
- operator trace for dispatch, checkpoint, boundary, and event history
- control reads for human requests and command runs

Read models are views. Controller-owned runtime state remains the authority.

## What operators control

Operators can use control surfaces to:

- pause, continue, or cancel a task
- resolve a pending human request
- inspect command runs and logs
- request command-run cancellation
- recover from task or dispatch issues when supported by the runtime

Use the narrowest control that matches the problem. Cancelling a command run is not the same as cancelling the whole task.

## Related pages

- [Runtime model](runtime-model.md)
- [Inspect and control a task](../guides/inspect-and-control-a-task.md)
- [Operator reference](../reference/operator/README.md)
