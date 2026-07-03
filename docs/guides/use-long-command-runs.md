# Use long command runs

Use command runs for controller-managed long-running command work. Do not use them for ordinary quick shell commands.

Ordinary inline commands should finish comfortably under about two minutes. If a command is likely to exceed that, use a command-run-enabled policy or redesign the assignment so the dispatch does not stall.

## Use a command run when

- command work is expected to outlive a normal dispatch
- the operator may need progress, logs, terminal state, or cancellation
- the task should wait on command completion without losing controller truth
- output is log-heavy enough that an operator needs a durable command-run surface

## Do not use a command run when

- a normal command should finish quickly
- the node only needs human judgment
- the command would expose secrets or private data outside the task boundary
- the workflow should be split into smaller assignments instead

## Author the policy gate

Grant command-run capability only to nodes that need it:

```yaml
capabilities:
    human_request:
        mode: deny
        allowed_kinds: []
    command_run: allow
```

Keep the instruction clear about the inline boundary:

```yaml
instruction: >-
    Use controller-managed command runs only for commands expected to be long, asynchronous, or log-heavy enough that inline execution is the wrong surface. Normal shell commands should stay inline and comfortably under two minutes.
```

If duration is ambiguous, estimate from command history, repo size, cache state, test size, and local convention before choosing the surface.

## Operator follow-up

Operators can inspect command runs, read logs when a log ref exists, and request cancellation of the current active command run without cancelling the whole task.

## Related pages

- [Capability model](../concepts/capability-model.md)
- [Operator model](../concepts/operator-model.md)
- [Write a policy](write-a-policy.md)
- [Handle ambiguity and incidents](handle-ambiguity-and-incidents.md)
- [Inspect and control a task](inspect-and-control-a-task.md)
