# Capability model

Status: Reference

Capabilities are explicit policy-granted powers for a node. They are not generic chat permissions.

The two user-visible capability families are human requests and command runs. They are intentionally separate because some nodes may need one but not the other.

## Human request capability

Human requests are typed waits for human judgment.

Use them when a node cannot safely continue from current evidence:

- `direction`: the next path depends on human judgment
- `approval`: work should not continue without explicit permission
- `input`: required facts are missing
- `review`: a human review gate is part of the workflow

Human request capability should not be used as a generic status update or ordinary chat continuation.

## Command-run capability

Command runs are controller-managed long-running command work.

Use them when command work is expected to exceed a normal dispatch and needs controller ownership, logs, progress, terminal state, or cancellation.

Ordinary commands should run inline and finish comfortably under about two minutes. If that is unlikely, use a command-run-enabled policy or redesign the assignment.

## Replan and recovery

Replan changes workflow shape when the current structure cannot honestly complete the task. Retry keeps the same assignment shape and tries again.

Use replan for structural mismatch. Use retry for a recoverable failed attempt.

## Related pages

- [Runtime model](runtime-model.md)
- [Use human requests](../guides/use-human-requests.md)
- [Use long command runs](../guides/use-long-command-runs.md)
- [Recover or replan a task](../guides/recover-or-replan-a-task.md)
