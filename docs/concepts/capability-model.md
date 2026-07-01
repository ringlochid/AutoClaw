# Capability model

Capabilities are explicit policy-granted powers for a node. They are not generic chat permissions and they do not replace budgets.

The two user-visible capability families are human requests and command runs. They are intentionally separate because many nodes need one but not the other.

## Human request capability

Human requests are typed waits for human judgment.

Use them when a node cannot safely continue from current evidence:

- `direction`: the next path depends on human judgment
- `approval`: work should not continue without explicit permission
- `input`: required facts are missing
- `review`: a human review gate is part of the workflow

Do not use human requests for status updates, ordinary progress, hidden chat continuation, or long command work.

## Command-run capability

Command runs are controller-managed long-running command work.

Use them when command work is expected to exceed a normal dispatch and needs controller ownership, logs, progress events, terminal state, or cancellation.

Ordinary commands should run inline and finish comfortably under about two minutes. If that is unlikely, use a command-run-enabled worker policy or redesign the assignment.

Command-run capability is usually a worker policy concern. Parent and root nodes should route long command work to a command-run-enabled worker instead of owning the process themselves.

## Budget is separate from capability

Budget fields limit repeated work. They do not grant tools.

- `retry_limit` belongs on worker policies
- `child_assignment_limit` belongs on root or parent policies
- omitted `budget_spec` means no controller budget counter for that family

A policy can have a budget without granting human requests or command runs. A capability-enabled policy still needs the right budget for its node kind.

## Replan and recovery

Replan changes workflow shape when the current structure cannot honestly complete the task. Retry keeps the same assignment shape and tries again.

Use retry for recoverable failed attempts. Use replan for structural mismatch.

## Related pages

- [Runtime model](runtime-model.md)
- [Policy model](policy-model.md)
- [Use human requests](../guides/use-human-requests.md)
- [Use long command runs](../guides/use-long-command-runs.md)
- [Recover or replan a task](../guides/recover-or-replan-a-task.md)
