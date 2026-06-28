# Definitions model

Status: Reference

AutoClaw authoring is split into four concepts.

## Roles

Roles describe what kind of node can do a job and what instruction contract it follows.

## Policies

Policies apply budgeting and retry or child-assignment rules to specific node kinds.

## Workflows

Workflows describe the tree of nodes, their purpose text, optional node-local instruction, criteria, produced artifacts, and dependency structure.

## Task-compose launch input

Task compose is the concrete launch body that picks a workflow, names the task, and binds authored roots to host paths.

## Exact reference

- [Design workflows and instructions](../guides/design-workflows-and-instructions.md)
- [Roles reference examples](../reference/definitions/roles/README.md)
- [Policies reference examples](../reference/definitions/policies/README.md)
- [Workflows reference examples](../reference/definitions/workflows/README.md)
- [Task-compose reference examples](../reference/definitions/task-compose/README.md)
