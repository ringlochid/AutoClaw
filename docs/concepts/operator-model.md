# Operator model

Operators inspect and steer running tasks. In AutoClaw docs, `operator` means a trusted external operator agent or operator-authorized client unless the text uses `human operator`.

In AutoClaw's intended product model, the primary operator is a trusted OpenClaw agent profile with operator MCP tools.

A human can also act as an operator, but through a different surface: humans use the UI, while operator agents use tools such as operator MCP. Both act over controller-owned runtime state, but they are not the same user experience or execution lane.

An operator is not the worker, parent/root node, or controller. Operator authority is for trusted runtime steering, not for ordinary node execution.

This distinction matters because node tools and operator tools have different authority. A worker cannot become an operator by writing a note, and a human operator should not act like a hidden worker by manually editing generated task files.

## Operator forms

- **Operator agent:** a trusted OpenClaw agent running with an operator-oriented profile. It uses operator MCP tools or equivalent trusted operator surfaces to inspect, launch, resolve, and recover work.
- **Human operator:** a human using the UI to inspect state, make decisions, approve actions, resolve waits, or request recovery. The UI should call trusted operator backend surfaces on the human's behalf.
- **Automation client:** a trusted integration that uses API-key-protected operator HTTP surfaces for automation. This is useful, but it is not the preferred human-facing product shape.

## What operators inspect

Operator agents usually inspect through operator MCP/readback tools. Human operators usually inspect the same controller truth through UI views.

Both surfaces read from:

- runtime task list and task readbacks
- generated task files such as workflow manifest, assignment, checkpoints, and artifacts
- operator snapshot for current state and top actionable items
- operator trace for dispatch, checkpoint, boundary, and event history
- control reads for human requests and command runs

Read models are views. Controller-owned runtime state remains the authority.

## What operators control

Operator agents can use operator tools to:

- pause, continue, or cancel a task
- resolve a pending human request
- inspect command runs and logs
- request command-run cancellation
- recover from task or dispatch issues when supported by the runtime

Human operators should do the same kind of work through UI controls, not by acting like a worker node or manually calling node tools.

Use the narrowest control that matches the problem. Cancelling a command run is not the same as cancelling the whole task.

## Related pages

- [Runtime model](runtime-model.md)
- [Set up OpenClaw agents and operator skills](../guides/set-up-openclaw-agents-and-skills.md)
- [Inspect and control a task](../guides/inspect-and-control-a-task.md)
- [Operator reference](../reference/operator/README.md)
