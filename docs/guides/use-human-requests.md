# Use human requests

Status: Reference

Use human requests when a node needs human judgment before it can safely continue.

Human requests are policy-granted capabilities. They are not a generic way to keep chatting with the operator.

## Use a human request when

- the next direction depends on human judgment
- explicit approval is required before continuing
- required input is missing from available evidence
- human review is part of the workflow's closure path

## Choose the request kind

- `direction`: ask which path to take next
- `approval`: ask whether to proceed with a specific action
- `input`: ask for facts the node cannot discover from current context
- `review`: ask for human review of evidence or output

## Avoid human requests when

- the node already has enough evidence to proceed
- the request is only a status update
- the workflow should block honestly instead
- the issue is a long command that should use command-run capability

## Operator follow-up

Operators inspect and resolve pending requests through the control or operator surfaces. After resolution, the controller resumes the waiting task path from runtime truth.

## Related pages

- [Capability model](../concepts/capability-model.md)
- [Operator model](../concepts/operator-model.md)
- [Inspect and control a task](inspect-and-control-a-task.md)
