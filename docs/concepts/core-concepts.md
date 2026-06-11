# Core concepts

Status: Reference

AutoClaw separates authored inputs from runtime truth and operator readbacks.

## Main personas

- workflow author: defines reusable roles, policies, workflows, and the task-compose launch body
- task launcher: starts concrete work from a task-compose body
- operator: inspects runtime state, reviews evidence, and uses control or recovery surfaces

## Main surfaces

- authoring surface: reusable definitions plus a separate task-compose launch input
- runtime surface: tasks, flows, assignments, attempts, checkpoints, and artifacts
- operator surface: inspect, control, audit, and recovery readbacks
- worker surface: delegated execution under the workflow and runtime contracts

## Main rule

Role, policy, and workflow files are importable definition inputs. Task-compose is a separate launch body. After upload and launch, controller-owned runtime state and registry truth take over.

## Related pages

- [Definitions model](definitions-model.md)
- [Workspace model](workspace-model.md)
- [Inspect and control a task](../guides/inspect-and-control-a-task.md)
