# Authoring model

AutoClaw authoring separates reusable definitions from one concrete launch. Roles, policies, and workflows are reusable. Task-compose is the launch input for one task.

## Authoring objects

| Object | Plain meaning | Owns | Should not own |
| --- | --- | --- | --- |
| Role | specialist lens | behavior posture, evidence-reading habits, output style | one task's paths, secrets, launch details |
| Policy | authority rules | node kind, budgets, capabilities, guardrails | specialist identity or node tree |
| Workflow | evidence path | node tree, criteria, consumes, produces, routing intent | live runtime state |
| Task-compose | this launch | task instruction, selected workflow, optional root bindings | reusable doctrine |

## Roles

Use roles for durable specialist posture:

- what kind of work the node can do
- what evidence it should read first
- what it should publish
- what it should avoid doing
- how it should surface uncertainty

Good role names are specific enough to review: `bug-fix-engineer`, `scope-reviewer`, `market-researcher`.

## Policies

Policies describe what a node is allowed to do.

Use policies for:

- `applies_to`: `root`, `parent`, or `worker`
- retry or child-assignment budget posture
- human request capability
- command-run capability
- concrete authority rules and prohibitions

Do not create a policy just because the role changes. A planner, reviewer, researcher, and engineer can all use the same ordinary worker policy when their authority is the same.

## Workflows

Workflows describe the evidence path for a purpose.

Use workflows for:

- root, parent, and worker node tree
- node-local missions
- criteria that can block closure
- consumed artifacts or criteria
- produced artifacts
- parent/root routing and release posture

A workflow is not a runtime log. It does not own checkpoints, dispatch state, operator decisions, or live currentness.

## Task-compose

Task-compose names one concrete task, selects a workflow, gives task-specific instruction, and can bind roots such as `workspace` and `context`. If roots are omitted, AutoClaw uses task-owned defaults.

Task-compose is intentionally separate from reusable definitions. It is the thing you start.

## Criteria, consumes, and produces

These three fields make workflows evidence-driven:

- **criteria** describe hard requirements
- **consumes** declare what a node must read
- **produces** declare what a node must leave behind

For fixed workflows, make handoffs explicit. For dynamic workflows, keep artifacts broad and stable so parents can route from current evidence.

## Provider skills

Provider skills can add task-specific instructions to the harness loop. Use them when the agent needs specialized local guidance, such as security review, frontend visual verification, PDF reading, browser triage, or release safety.

Skills should support the role and node mission. They should not replace workflow criteria or controller-owned evidence.

## Related pages

- [Core concepts](core-concepts.md)
- [Policy model](policy-model.md)
- [Task-compose model](task-compose-model.md)
- [Design workflows and instructions](../guides/design-workflows-and-instructions.md)
- [Write a role](../guides/write-a-role.md)
- [Write a policy](../guides/write-a-policy.md)
- [Write a workflow](../guides/write-a-workflow.md)
