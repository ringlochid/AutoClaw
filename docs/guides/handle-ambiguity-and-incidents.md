# Handle ambiguity and incidents

Use this guide when a workflow must survive missing facts, unclear scope, contradictory evidence, unexpected failures, or intent mismatch.

AutoClaw should not make every worker improvise. Workers surface uncertainty. Parents and roots route it through focused children, replan, human requests, or honest blocked closure.

## Classify the uncertainty

Start by naming what kind of uncertainty exists.

| Type            | Meaning                                            | AutoClaw response                 |
| --------------- | -------------------------------------------------- | --------------------------------- |
| known known     | evidence and rule are present                      | execute and cite evidence         |
| known unknown   | missing fact is named                              | inspect, research, assign, or ask |
| hidden known    | constraint exists in docs, code, tests, or history | search authoritative local truth  |
| unknown unknown | surprising contradiction, failure, or incident     | contain, preserve evidence, route |

For authored definitions, use more concrete labels:

- missing input
- conflicting criteria
- unclear scope
- contract drift
- docs drift
- insufficient evidence
- child-output weakness
- workflow-shape mismatch
- approval or risk decision

These labels help a parent choose the next control action instead of repeating the same assignment.

## Worker behavior

Workers should stay inside the current assignment.

Give workers this posture through role and policy wording:

1. read current task truth first
2. research only when it can change the result or risk call
3. resolve ambiguity locally when safe
4. make the smallest low-risk assumption only when necessary
5. record the assumption as risk
6. report material ambiguity instead of widening scope
7. do not replan the workflow unless assigned to recommend a replan

Workers can recommend the next shape. Parent/root nodes own the control action.

## Parent and root behavior

Parents and roots are the routing layer.

Their instructions should say how to choose among:

- focused research child
- planner child
- reviewer or verifier child
- failure analyst child
- human request when policy allows it
- structural replan when the tree shape is wrong
- blocked closure when no honest progress remains

Parent/root nodes should treat child green as evidence to inspect, not as automatic release. They should treat child blocked as routing input, not as automatic whole-flow failure.

## Intent mismatch

Intent mismatch happens when the workflow is still moving but no longer serves the user's purpose.

Common signs:

- a worker is solving a broader problem than the task asked for
- implementation work starts before product or scope evidence exists
- review criteria judge the wrong output
- release evidence proves a different thing than the root purpose
- a fixed workflow keeps running after the route should have changed

Root and parent instructions should require this check:

```text
Compare current workflow shape with user purpose, accepted scope, current
criteria, and surfaced evidence. If they diverge, replan or ask for direction
instead of forcing the current assignment to fit.
```

## Incident posture

An incident is not just a failed node. It is a condition where the task may be causing harm, losing control, or proving that the current assumptions are wrong.

Incident-capable workflows should prefer this order:

1. contain the blast radius
2. preserve current evidence
3. identify affected scope
4. assign triage or failure analysis
5. choose fix, retry, replan, or block
6. verify recovery
7. publish the lesson or residual risk

Do not optimize before containment. Do not hide surprising behavior by turning it into a normal retry.

## Human requests

Use human requests for human judgment, not for normal status.

Good request points:

- direction when multiple valid paths remain
- approval before irreversible or externally visible action
- input when required facts cannot be discovered
- review when human review is part of the closure path

If the issue is only long-running command work, use command-run capability instead. Human request and command-run capability are separate.

## Long command runs

Use command-run capability only when command work is expected to outlive a normal dispatch. Ordinary commands should stay inline and comfortably under about two minutes.

When runtime duration is ambiguous, the worker should estimate from command history, repo size, cache state, test size, and local convention. If the command is likely to exceed the inline window, use a command-run-enabled policy or report the need instead of stalling the dispatch.

## Definition checklist

Before saving a workflow that may hit ambiguity, check:

- workers know what uncertainty to report
- parents know how to route gaps
- roots know when intent mismatch requires replan
- review and verification nodes treat unclear criteria as gaps
- incident paths preserve evidence before retry
- human request kinds match real decision points
- long command runs are isolated to nodes that need them
- blocked closure requires current evidence, not frustration

## Related pages

- [Design workflows and instructions](design-workflows-and-instructions.md)
- [Write layered instructions](write-layered-instructions.md)
- [Use human requests](use-human-requests.md)
- [Use long command runs](use-long-command-runs.md)
- [Recover or replan a task](recover-or-replan-a-task.md)
