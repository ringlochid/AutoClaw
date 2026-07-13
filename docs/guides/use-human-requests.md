# Use human requests

Use human requests when a node needs human judgment before it can safely continue.

Human requests are policy-granted capabilities. They are not a generic way to keep chatting with the operator.

## Use a human request when

- the next direction depends on human judgment
- explicit approval is required before continuing
- required input is missing from available evidence
- human review is part of the workflow's closure path
- an unresolved risk decision cannot be settled from current artifacts

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
- a parent/root should route the ambiguity to research, review, verification, failure analysis, or replan

## Author the policy gate

Grant only the kinds this node actually needs:

```yaml
capabilities:
    human_request:
        mode: allow
        allowed_kinds:
            - direction
            - approval
    command_run: deny
```

Keep the policy instruction specific about when the node may ask:

```yaml
instruction: >-
  Ask for approval only before externally visible action. Ask for direction only when current evidence leaves multiple valid routes with different risk.
```

Do not bundle human-request and command-run capability by default. A node can have human request only, command run only, both, or neither.

## Operator follow-up

Operators inspect and resolve pending requests through the control or operator surfaces. After resolution, the controller resumes the waiting task path from runtime truth.

## Related pages

- [Capability model](../concepts/capability-model.md)
- [Operator model](../concepts/operator-model.md)
- [Write a policy](write-a-policy.md)
- [Handle ambiguity and incidents](handle-ambiguity-and-incidents.md)
- [Inspect and control a task](inspect-and-control-a-task.md)
