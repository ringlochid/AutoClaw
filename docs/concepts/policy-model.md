# Policy model

Status: Reference

Policies describe node authority. They say which node kinds a policy can attach to, which controller capabilities the node may use, and which budget guardrails bound repeated work.

A policy should not describe specialist identity. Put engineer, reviewer, planner, researcher, release, and triage behavior in roles or workflow-node instructions.

## When not to write a new policy

Most nodes should use the shipped standard policies. Do not create a new policy for each role, domain, or workflow stage.

Use a new policy only when the reusable authority changes:

- a different compatible node kind
- a different retry or child-assignment budget
- different human-request permission or allowed kinds
- different command-run permission
- a concrete shared prohibition or capability-use rule

If only the job changes, keep the policy and change the role or node instruction.

## `applies_to`

`applies_to` is the node-kind compatibility list. Current valid values are:

- `root`: the top node that owns whole-task closure
- `parent`: a non-root node with children and subtree control authority
- `worker`: a bounded executable node

AutoClaw does not have a separate `leaf` value in policy YAML. A leaf is a `worker` node with no children.

Use the narrowest compatible list. A worker policy should usually say:

```yaml
applies_to:
    - worker
```

## Budget spec

`budget_spec` is a controller guardrail. It is not a time budget, token budget, quality target, or acceptance criterion.

Current budget fields are:

| Field                    | Valid on          | Meaning                                      |
| ------------------------ | ----------------- | -------------------------------------------- |
| `retry_limit`            | `worker`          | same-assignment worker retry budget          |
| `child_assignment_limit` | `root`, `parent`  | child assignments the node may open          |

Do not mix both fields in one policy. A worker retries its own assignment; a parent or root opens child assignments.

Good worker budget:

```yaml
budget_spec:
    retry_limit: 1
```

Good parent budget:

```yaml
budget_spec:
    child_assignment_limit: 4
```

## Capabilities

Capabilities grant explicit controller powers.

Human requests and command runs are separate:

```yaml
capabilities:
    human_request:
        mode: allow
        allowed_kinds:
            - direction
            - approval
    command_run: deny
```

Use human requests for human judgment:

- `direction`: the next route depends on human choice
- `approval`: work should not continue without permission
- `input`: required facts are missing
- `review`: human review is part of closure

Use command-run capability only for controller-managed long command work. Ordinary commands should run inline and finish comfortably under about two minutes.

## Standard policy family

The shipped policies are intentionally small:

| Policy                        | Use when                                               |
| ----------------------------- | ------------------------------------------------------ |
| `standard-root`               | root owns final closure without waits                  |
| `standard-root-human-request` | root may need human direction, approval, input, review |
| `standard-parent`             | parent routes a subtree without waits                  |
| `standard-parent-human-request` | parent may need human judgment while routing        |
| `standard-worker`             | worker performs one bounded assignment                 |
| `standard-worker-human-request` | worker may need human judgment                       |
| `standard-worker-command-run` | worker may need controller-managed long commands       |

The standard family is deliberately generic. Put the real job difference in roles, workflow node missions, criteria, and artifacts.

## Good policy shape

Many policies do not need `instruction`. A field-only policy is good when `applies_to`, `budget_spec`, and `capabilities` already say everything.

Use policy instructions only when a capability or guardrail needs extra operational guidance, such as:

- when a human request is allowed
- when a command run is allowed
- what the capability must not be used for
- what evidence the capability must leave behind

Avoid policy instructions that sound like:

- "review the patch"
- "plan the campaign"
- "fix the bug"
- "research the market"

Those are role or node responsibilities. A policy should say what the node may do while carrying that responsibility, and should stay silent when the fields already say it.

## Related pages

- [Authoring model](authoring-model.md)
- [Capability model](capability-model.md)
- [Write a policy](../guides/write-a-policy.md)
- [Write layered instructions](../guides/write-layered-instructions.md)
