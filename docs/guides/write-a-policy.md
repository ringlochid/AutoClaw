# Write a policy

Status: Reference

Write a policy when you need reusable guardrails, budgets, or capabilities for a node. A policy constrains how work proceeds; it should not replace the role.

Use policies to make authority explicit. Human requests and command runs are separate capabilities, so grant only the one the node actually needs.

## First decide if you need one

Do not write a new policy because the role is different. A reviewer, engineer, researcher, planner, or release operator can all use `standard-worker` when they are doing ordinary bounded worker work with no human wait and no command-run capability.

Use an existing standard policy when only the specialist work changes:

- ordinary root closure: `standard-root`
- ordinary parent routing: `standard-parent`
- ordinary worker assignment: `standard-worker`
- human wait needed: use the matching `*-human-request` policy
- long command work needed: use `standard-worker-command-run`

Write a new policy only when at least one reusable rule differs:

- compatible node kind
- retry or child-assignment budget
- human-request permission or allowed kinds
- command-run permission
- a hard authority rule that many nodes should share
- a concrete prohibition that is not just role behavior

If the difference is "what work should this specialist do?", write a role or workflow node instruction instead.

## Know the required fields

A policy file needs:

- `kind: policy`
- `id`
- `title`
- `description`
- `applies_to`
- optional `budget_spec`
- optional `capabilities`
- optional `labels`
- optional `instruction`

Use `description` for a short purpose summary. `instruction` is optional. Omit it when `applies_to`, `budget_spec`, and `capabilities` already express the full policy.

## Decide what the policy controls

Before writing YAML, answer:

- which node kind can use this policy?
- can this node ask a human for direction, approval, input, or review?
- can this node start controller-managed long command runs?
- how should retry or child assignment be bounded?
- what evidence must appear before closure?
- what actions should be explicitly out of scope?
- what ambiguity should block, route, or trigger a human request?

Keep identity out of the policy. "Reviewer", "engineer", or "researcher" behavior belongs in a role. The policy should say what is allowed and how tightly the node must behave.

## Use a simple decision flow

For each node, choose policy in this order:

1. Pick by node kind: root, parent, or worker.
2. Ask whether the node may wait on a human. If yes, use a human-request policy for that node kind.
3. Ask whether the node may start controller-managed long commands. If yes, use a command-run-enabled worker policy or write a deliberately narrow one.
4. Use the base standard policy when both capabilities are denied.
5. Write a new policy only if the shipped standard fields are the wrong authority contract.

Do not add policy `instruction` while following this flow unless the capability grant needs a usage rule.

## Set `applies_to`

`applies_to` names compatible node kinds:

- `root`
- `parent`
- `worker`

There is no separate `leaf` value. A leaf worker is a `worker` node with no children.

Use one node kind unless the same authority rules genuinely fit several kinds. Most policies should stay narrow.

Good:

```yaml
applies_to:
    - worker
```

Risky:

```yaml
applies_to:
    - root
    - parent
    - worker
```

Broad compatibility often hides budget and authority mistakes.

## Set `budget_spec`

Budget is a controller guardrail, not a time limit and not a success criterion.

Use `retry_limit` only for worker policies:

```yaml
budget_spec:
    retry_limit: 1
```

Use `child_assignment_limit` only for root or parent policies:

```yaml
budget_spec:
    child_assignment_limit: 4
```

Do not put both fields in one policy. Workers retry; parents and roots assign children.

## Grant capabilities separately

Human requests are for human judgment. Command runs are for long-running command work. A node can have one, both, or neither.

```yaml
kind: policy
id: worker-human-review
title: Worker Human Review
description: Guardrails for worker assignments that may require human review.
applies_to:
    - worker
budget_spec:
    retry_limit: 1
capabilities:
    human_request:
        mode: allow
        allowed_kinds:
            - review
    command_run: deny
instruction: >-
  Use human_request only when human review is required for honest closure and current evidence cannot replace that review. Do not use human_request for status or long command work.
```

## Use human requests for judgment

Allow human requests only where a human decision is part of the workflow.

Use:

- `direction` when the next route depends on human judgment
- `approval` before an irreversible or externally visible action
- `input` when required facts cannot be discovered from current evidence
- `review` when human review is part of closure

Do not use a human request for status updates, ordinary progress, or long command work.

## Use command runs for long commands

Grant command-run capability only when command work is expected to outlive a normal dispatch. Ordinary shell commands should finish inline and comfortably under about two minutes.

If a workflow frequently needs long commands, put them in a dedicated worker with a command-run-enabled policy. Do not grant command-run permission to every node just in case.

Command-run policies should usually apply to `worker`. Parent and root nodes should assign a command-run-enabled worker when long command work is needed.

## Use the standard policy family

Start from one of the shipped generic policies:

| Policy                        | Use when                                               |
| ----------------------------- | ------------------------------------------------------ |
| `standard-root`               | root owns final closure without waits                  |
| `standard-root-human-request` | root may need human judgment                           |
| `standard-parent`             | parent routes a subtree without waits                  |
| `standard-parent-human-request` | parent may need human judgment while routing        |
| `standard-worker`             | worker performs one bounded assignment                 |
| `standard-worker-human-request` | worker may need human judgment                       |
| `standard-worker-command-run` | worker may need controller-managed long command work   |

Write a new policy when the fields or capability-use rule differ, not when only the specialist role differs.

## Use instruction sparingly

Most base policies do not need instructions. `standard-root`, `standard-parent`, and `standard-worker` are field-only policies because compatibility, budget, and denied capabilities already say the whole rule.

Use policy `instruction` only when the fields need an extra operational rule, usually for a capability:

```yaml
instruction: >-
  Use command_run only for commands expected to be long, asynchronous, or log-heavy enough that inline execution is the wrong surface.
```

Keep research, ambiguity classification, specialist behavior, and workflow routing in roles and workflow nodes unless the policy is explicitly granting the capability that handles that case.

Good field-only policy:

```yaml
kind: policy
id: standard-worker
title: Standard Worker
description: Guardrails for bounded worker assignments without human waits or command runs.
applies_to:
    - worker
budget_spec:
    retry_limit: 1
capabilities:
    human_request:
        mode: deny
        allowed_kinds: []
    command_run: deny
```

Bad policy instruction:

```yaml
instruction: >-
  Review the implementation, check the tests, and write a release note.
```

That belongs in a role or workflow node because it describes the job, not the authority.

## Check policy versus role

If a sentence starts with a job verb such as review, design, fix, research, verify, triage, or release, it probably belongs in a role or workflow node.

If a sentence only restates `applies_to`, `budget_spec`, or `capabilities`, omit it. If it explains how to use a granted capability safely, it can belong in policy `instruction`.

## Good policy checklist

- capability grants are explicit and minimal
- `applies_to` uses only valid node kinds
- `retry_limit` appears only on worker policies
- `child_assignment_limit` appears only on root or parent policies
- budget is not described as time, tokens, or quality
- human request kinds match real workflow gates
- command-run permission is not granted by default
- ordinary commands stay inline and under about two minutes
- retry or assignment posture is clear when relevant
- base policies omit unnecessary `instruction`
- capability policies explain only capability use
- forbidden actions are concrete
- the policy does not duplicate role identity
- material ambiguity has a route

## Related pages

- [Write layered instructions](write-layered-instructions.md)
- [Write a role](write-a-role.md)
- [Write a workflow](write-a-workflow.md)
- [Capability model](../concepts/capability-model.md)
- [Policy model](../concepts/policy-model.md)
- [Policy reference examples](../reference/definitions/policies/README.md)
