# Authoring model

Status: Reference

AutoClaw authoring separates reusable behavior from one concrete launch. Roles, policies, and workflows are reusable definitions. Task-compose is the launch input for one task.

## Roles

Roles describe a stable capability profile and instruction contract.

Use roles for durable specialist posture:

- what kind of work the node can do
- what evidence it should read first
- what it should publish
- what it should avoid doing

Do not put one task's paths, secrets, or launch details in a role.

## Policies

Policies describe guardrails and capabilities for a node.

Use policies for:

- retry or child-assignment budget posture
- human request capability
- command-run capability
- evidence and checkpoint expectations
- boundaries such as "do not implement" or "do not publish externally"

Human request and command-run capability are separate. A node can have one, both, or neither.

## Workflows

Workflows describe the evidence path for a purpose.

Use workflows for:

- the root, parent, and worker node tree
- node descriptions and node-local guidance
- required consumed artifacts or criteria
- required produced artifacts
- hard criteria that can block closure

A workflow is not a runtime log. It does not own checkpoints, dispatch state, operator decisions, or live task currentness.

## Task-compose

Task-compose names one concrete task, selects a workflow, gives task-specific instruction, and binds roots such as `workspace` and `context`.

Task-compose is intentionally separate from reusable definitions. It is the thing you start.

## Related pages

- [Task-compose model](task-compose-model.md)
- [Design workflows and instructions](../guides/design-workflows-and-instructions.md)
- [Create a definition set](../guides/create-a-definition-set.md)
- [Definitions reference](../reference/definitions/README.md)
