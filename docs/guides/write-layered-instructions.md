# Write layered instructions

Status: Reference

Use this guide when you need to decide where wording belongs in a role, policy, workflow node, or task-compose file.

AutoClaw definitions work best as layered contracts. Each layer should own one kind of truth. If the same sentence could live in several places, put it in the narrowest stable layer that will still be true across runs.

## Use the right layer

| Layer                | Owns                                          | Should avoid                   |
| -------------------- | --------------------------------------------- | ------------------------------ |
| `title`              | human-readable name                           | behavior or process            |
| `description`        | short purpose summary                         | long procedure, paths, secrets |
| role `instruction`   | reusable specialist lens                      | task-specific scope            |
| policy `instruction` | authority, budgets, capabilities, guardrails  | role identity                  |
| node `instruction`   | local mission guidance for this workflow step | repeating role or policy       |
| task `instruction`   | one concrete launch request                   | reusable behavior rules        |
| `criteria`           | hard pass/fail gates                          | soft preferences               |
| `produces`           | durable outputs later nodes need              | status chatter                 |
| `consumes`           | required prior evidence                       | vague "read context" wording   |

Use this shortcut:

```text
Role = lens
Policy = rules
Node = mission
Criteria = done gate
Produces = leaves behind
Consumes = must read
Workflow = evidence path
Task-compose = this launch
```

## Separate summary from instruction

`description` should help a reader scan a list and understand why the object exists. It should not teach the agent how to act.

Good:

```yaml
description: Worker for one bounded defect fix.
```

Too procedural:

```yaml
description: Read triage, inspect tests, patch code, verify behavior, and report.
```

Put behavior in `instruction`:

```yaml
instruction: >-
  Read triage evidence and criteria before editing. Fix only the verified defect. If
  root cause remains ambiguous, publish the unresolved risk instead of widening the
  patch.
```

## Write role instructions as lenses

A role teaches the agent what kind of work it is doing across many tasks.

Good role instructions answer:

- what kind of evidence this specialist reads first
- what mode it is in: research, planning, implementation, review, verification, release, or coordination
- what output a parent/root can expect
- what the role refuses to widen
- what kind of ambiguity the role should surface

Do not put one run's paths, users, secrets, or launch detail in a role.

## Write policy instructions as authority

A policy teaches what the node may do and how tightly it must behave.

Use policies for:

- `applies_to` compatibility with `root`, `parent`, or `worker`
- human request capability
- command-run capability
- retry and child-assignment posture
- required checkpoint posture
- closure and blocked-state guardrails
- "do not publish", "do not implement", or "do not widen scope" boundaries

Do not make a policy sound like a second role. "Reviewer", "engineer", and "researcher" behavior belongs in roles. "May ask for approval" or "must not start long commands" belongs in policies.

Policy `instruction` is optional. If `applies_to`, `budget_spec`, and `capabilities` already express the whole rule, omit `instruction`. The base `standard-worker` policy is a good field-only policy.

Budget wording belongs in policies, but keep it precise:

- `retry_limit` is for worker retries only
- `child_assignment_limit` is for root or parent child assignment only
- budget is not a time limit, token limit, or quality bar

## Write node instructions as missions

A workflow node is the only layer that should mention the local purpose of a specific step.

Good node instructions answer:

- what this step must accomplish now
- which scope is accepted
- what should stay out of scope
- which current artifacts or criteria matter most
- what a green, retry, or blocked result should mean for this step

Do not copy the whole role or policy instruction into the node. If many nodes need the same behavior, move that behavior into a role or policy.

## Write task instructions as launch detail

Task-compose is for one concrete run. It can mention the real target, accepted constraints, local roots, and user-request detail.

Do not put reusable doctrine in task-compose. If the sentence should apply to many future tasks, move it into a role, policy, or workflow.

## Keep research and ambiguity useful

Research wording should explain when research changes the decision. It should not turn every role into a generic researcher.

Use this split:

- policy: shared ambiguity protocol and escalation rules
- role: domain evidence lens, such as code patterns, market sources, test oracle, or product acceptance signal
- workflow: where ambiguity routes next
- node: the local uncertainty that this step should resolve

Good:

```yaml
instruction: >-
  Research local contracts and nearby tests before editing. If the accepted scope
  conflicts with the current API contract, publish the conflict and residual risk
  instead of widening the patch.
```

Too vague:

```yaml
instruction: >-
  Do research first and solve any ambiguity.
```

## Keep agents purposeful

Instructions should give agents judgment inside clear boundaries.

Prefer wording such as:

- choose the smallest evidence path that proves the purpose
- challenge weak evidence before release
- publish artifacts only when later nodes need them
- propose the next useful action when blocked
- do not widen scope to make closure easier

Avoid wording such as:

- always create every artifact
- complete every step even when obsolete
- ask a parent for every uncertainty
- follow the current shape when evidence proves it is wrong

## Checklist

Before saving instructions, check:

- each `description` is short enough to scan
- each role has one stable specialist lens
- each policy owns authority rather than identity
- each policy uses valid `applies_to` and budget fields for its node kind
- each node has a local mission rather than copied boilerplate
- human request and command-run rules stay separate
- criteria can genuinely block closure
- produced artifacts are worth consuming later
- unresolved ambiguity has a route, not a hidden assumption

## Related pages

- [Design workflows and instructions](design-workflows-and-instructions.md)
- [Write a role](write-a-role.md)
- [Write a policy](write-a-policy.md)
- [Write a workflow](write-a-workflow.md)
- [Handle ambiguity and incidents](handle-ambiguity-and-incidents.md)
