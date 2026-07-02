# Write a policy

Write a policy when you need reusable authority, budgets, or capabilities for a node. A policy constrains how work proceeds; it should not replace the role.

Use policies to make authority explicit. Human requests and command runs are separate capabilities, so grant only the one the node actually needs.

## Recommended decision flow

1. Pick by node kind: `root`, `parent`, or `worker`.
2. Decide whether repeated work needs a budget.
3. Decide whether the node may open human requests.
4. Decide whether the node may start controller-managed command runs.
5. Start from a shipped standard policy when the standard authority fits.
6. Write a custom policy only when reusable authority differs.

Do not write a new policy because the specialist role changed.

## Policy fields

| Field | Required | Default | Controls | Notes |
| --- | --- | --- | --- | --- |
| `kind` | yes | none | file wrapper | use `policy` |
| `id` | yes | none | stable policy key | keep it portable and descriptive |
| `title` | no | none | display name | useful in UI/readbacks |
| `description` | yes | none | short purpose | explain authority, not role identity |
| `applies_to` | yes | none | compatible node kinds | use `root`, `parent`, or `worker` |
| `budget_spec` | no | no controller budget counter | retry or child-assignment limit | do not mix budget families |
| `capabilities` | no | deny human requests and command runs | explicit controller powers | grant narrowly |
| `labels` | no | empty list | search/grouping metadata | optional |
| `instruction` | no | none | extra operational rule | use sparingly |

## Set `applies_to`

`applies_to` names compatible node kinds:

- `root`
- `parent`
- `worker`

There is no separate `leaf` value. A leaf worker is a `worker` node with no children.

Use one node kind unless the same authority rules genuinely fit several kinds.

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

Budget is a controller guardrail. It is not a time limit, token limit, quality target, or success criterion.

| Field | Valid on | Default when omitted | What happens when present | Suggested values |
| --- | --- | --- | --- | --- |
| `retry_limit` | `worker` | no controller retry counter | limits additional attempts for the same assignment | `0` for no retry, `1` for ordinary work, `2` for cheap/flaky work |
| `child_assignment_limit` | `root`, `parent` | no controller child-assignment counter | limits child assignments opened by this assignment | `3` small root, `5-8` moderate parent, higher only for batch parents |

Rules:

- use `retry_limit` only for worker policies
- use `child_assignment_limit` only for root or parent policies
- do not put both fields in one policy
- omitted `budget_spec` means no controller budget counter for that budget family: retries or child assignments are unlimited, so omit it deliberately

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

If a node exhausts its budget, the next move should be explicit: close with evidence, ask for human direction when allowed, replan, or block.

## Grant capabilities separately

Human requests are for human judgment. Command runs are for long-running command work. A node can have one, both, or neither.

Defaults:

- omitted `capabilities` denies human requests and command runs
- omitted `capabilities.human_request` defaults to `mode: deny`
- omitted `capabilities.command_run` defaults to `deny`
- `human_request.mode: allow` requires non-empty `allowed_kinds`
- `human_request.mode: deny` grants no human request permission even if `allowed_kinds` is present

Human-request example:

```yaml
capabilities:
    human_request:
        mode: allow
        allowed_kinds:
            - direction
            - approval
    command_run: deny
```

Command-run example:

```yaml
capabilities:
    human_request:
        mode: deny
        allowed_kinds: []
    command_run: allow
```

## Use human requests for judgment

Allow human requests only where a human decision is part of the workflow.

Use:

- `direction` when the next route depends on human judgment
- `approval` before an irreversible or externally visible action
- `input` when required facts cannot be discovered from current evidence
- `review` when human review is part of closure

Do not use human requests for status updates, ordinary progress, or long command work.

## Use command runs for long commands

Grant command-run capability only when command work is expected to outlive a normal dispatch or needs durable logs, terminal state, cancellation, or continuation.

Ordinary shell commands should finish inline and comfortably under about two minutes.

If a workflow frequently needs long commands, put them in a dedicated worker with a command-run-enabled policy. Parent and root nodes should assign a command-run-enabled worker instead of owning the process themselves.

## Use the standard policy family

Start from one of the shipped generic policies:

| Policy | Use when |
| --- | --- |
| `standard-root` | root owns final closure without waits |
| `standard-root-human-request` | root may need human judgment |
| `standard-parent` | parent routes a subtree without waits |
| `standard-parent-human-request` | parent may need human judgment while routing |
| `standard-worker` | worker performs one bounded assignment |
| `standard-worker-human-request` | worker may need human judgment |
| `standard-worker-command-run` | worker may need controller-managed long command work |

Write a new policy when the fields or capability-use rule differ, not when only the specialist role differs.

## Use instruction sparingly

Most base policies do not need instructions. `standard-root`, `standard-parent`, and `standard-worker` are field-only policies because compatibility, budget, and denied capabilities already say the whole rule.

Use policy `instruction` only when the fields need an extra operational rule, usually for a capability:

```yaml
instruction: >-
  Use command_run only for commands expected to be long, asynchronous, or log-heavy enough that inline execution is the wrong surface.
```

Keep research, ambiguity classification, specialist behavior, and workflow routing in roles and workflow nodes unless the policy is explicitly granting the capability that handles that case.

Bad policy instruction:

```yaml
instruction: >-
  Review the implementation, check the tests, and write a release note.
```

That belongs in a role or workflow node because it describes the job, not the authority.

## Full worker example

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

## Good policy checklist

- capability grants are explicit and minimal
- `applies_to` uses only valid node kinds
- `retry_limit` appears only on worker policies
- `child_assignment_limit` appears only on root or parent policies
- `budget_spec` is omitted only when unbounded repeated work is intentional
- human request kinds match real workflow gates
- command-run permission is not granted by default
- ordinary commands stay inline and under about two minutes
- base policies omit unnecessary `instruction`
- capability policies explain only capability use
- forbidden actions are concrete
- the policy does not duplicate role identity

## Related pages

- [Policy model](../concepts/policy-model.md)
- [Capability model](../concepts/capability-model.md)
- [Write layered instructions](write-layered-instructions.md)
- [Write a role](write-a-role.md)
- [Write a workflow](write-a-workflow.md)
