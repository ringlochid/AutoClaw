# Policy model

Policies describe node authority. They say which node kinds a policy can attach to, which controller capabilities the node may use, and which budget guardrails bound repeated work.

A policy should not describe specialist identity. Put engineer, reviewer, planner, researcher, release, and triage behavior in roles or workflow-node instructions.

## When not to write a new policy

Most nodes should use the shipped standard policies. Do not create a new policy for each role, domain, or workflow stage.

Use a new policy only when reusable authority changes:

- compatible node kind
- retry or child-assignment budget
- human-request permission or allowed kinds
- command-run permission
- shared prohibition or capability-use rule

If only the job changes, keep the policy and change the role or node instruction.

## `applies_to`

`applies_to` is the node-kind compatibility list:

- `root`: top node that owns whole-task closure
- `parent`: non-root node with children and subtree control authority
- `worker`: bounded executable node

There is no separate `leaf` policy value. A leaf is a `worker` node with no children.

## Budget

`budget_spec` is a controller guardrail. It is not a time limit, token limit, quality target, or acceptance criterion.

| Field | Valid on | What it controls | Suggested starting value |
| --- | --- | --- | --- |
| `retry_limit` | `worker` | additional attempts for the same worker assignment | `1` for ordinary work, `0` for no retry, `2` only when failure analysis is cheap |
| `child_assignment_limit` | `root`, `parent` | child assignments opened by this assignment | `3` for small root nodes, `5-8` for moderate routing, higher only for batch parents |

Rules:

- omitted `budget_spec` means no controller budget counter for that budget family: repeated work is unlimited
- `retry_limit` belongs on worker policies; retry opens another attempt at the same assignment
- `child_assignment_limit` belongs on root or parent policies; `assign_child` is a parent/root tool
- one policy must not mix both fields

Budget exhaustion should force an honest routing decision: close with evidence, ask for human direction when allowed, replan, or block.

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

Defaults:

- omitted `capabilities` denies human requests and command runs
- omitted `capabilities.human_request` defaults to `mode: deny`
- omitted `capabilities.command_run` defaults to `deny`
- `human_request.mode: allow` requires at least one `allowed_kinds` entry

Use human requests for human judgment. Use command-run capability only for controller-managed long command work.

## Standard policy family

The shipped policies are intentionally small:

| Policy | Use when |
| --- | --- |
| `standard-root` | root owns final closure without waits |
| `standard-root-human-request` | root may need human direction, approval, input, or review |
| `standard-parent` | parent routes a subtree without waits |
| `standard-parent-human-request` | parent may need human judgment while routing |
| `standard-worker` | worker performs one bounded assignment |
| `standard-worker-human-request` | worker may need human judgment |
| `standard-worker-command-run` | worker may need controller-managed long command work |

The standard family is deliberately generic. Put job differences in roles, workflow node missions, criteria, and artifacts.

## Good policy shape

Many policies do not need `instruction`. A field-only policy is good when `applies_to`, `budget_spec`, and `capabilities` already say everything.

Use policy instructions only when a capability or guardrail needs extra operational guidance:

- when a human request is allowed
- when a command run is allowed
- what the capability must not be used for
- what evidence the capability must leave behind

Avoid policy instructions that sound like "review the patch", "plan the campaign", "fix the bug", or "research the market." Those are role or node responsibilities.

## Related pages

- [Authoring model](authoring-model.md)
- [Capability model](capability-model.md)
- [Write a policy](../guides/write-a-policy.md)
- [Write layered instructions](../guides/write-layered-instructions.md)
