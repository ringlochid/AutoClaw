# AutoClaw docs

AutoClaw is a local-first orchestration tool for delegated AI work. Use these docs to install it, understand the architecture, write small workflows, and inspect running tasks from controller-owned evidence.

## Recommended path

**Run one task before writing your own workflow.**

1. [Prepare OpenClaw first](start/prepare-openclaw.md)
2. [Get started](start/getting-started.md)
3. [Start a task](start/start-a-task.md)
4. [Inspect a task](start/inspect-a-task.md)
5. [Read the orchestration model](concepts/orchestration-model.md)
6. [Design your first workflow](guides/design-workflows-and-instructions.md)

## Model

Read concepts in this order:

| Step | Page | What it teaches |
| --- | --- | --- |
| 1 | [Orchestration model](concepts/orchestration-model.md) | what orchestration means, how AutoClaw differs from OpenClaw, and why the layers exist |
| 2 | [Core concepts](concepts/core-concepts.md) | the minimum nouns: workflow, task-compose, assignment, checkpoint, artifact |
| 3 | [Authoring model](concepts/authoring-model.md) | role, policy, workflow, task-compose, criteria, consumes, produces |
| 4 | [Runtime model](concepts/runtime-model.md) | task, flow, assignment, attempt, dispatch, manifest, checkpoint, boundary, wait, replan |
| 5 | [Capability model](concepts/capability-model.md) | human requests, command runs, budgets, retry, and replan |

Optional concept pages:

- [Policy model](concepts/policy-model.md)
- [Task-compose model](concepts/task-compose-model.md)
- [Workspace model](concepts/workspace-model.md)
- [Operator model](concepts/operator-model.md)

## Build and operate

Use these guides when writing real definitions:

- [Design workflows and instructions](guides/design-workflows-and-instructions.md)
- [Write layered instructions](guides/write-layered-instructions.md)
- [Write a role](guides/write-a-role.md)
- [Write a policy](guides/write-a-policy.md)
- [Write a workflow](guides/write-a-workflow.md)
- [Write a task-compose file](guides/write-a-task-compose.md)
- [Use guide examples](guides/examples/README.md)

Use these guides when a task is already running:

- [Inspect and control a task](guides/inspect-and-control-a-task.md)
- [Recover or replan a task](guides/recover-or-replan-a-task.md)
- [Use human requests](guides/use-human-requests.md)
- [Use long command runs](guides/use-long-command-runs.md)
- [Handle ambiguity and incidents](guides/handle-ambiguity-and-incidents.md)

## Exact reference

Reference pages are for exact commands, routes, schemas, and shipped definition examples:

- [CLI reference](reference/cli/README.md)
- [API reference](reference/api/README.md)
- [Operator reference](reference/operator/README.md)
- [Definitions reference](reference/definitions/README.md)

## Help

- [Troubleshooting](help/troubleshooting.md)
- [Task start failures](help/task-start-failures.md)
- [Task stuck or waiting](help/task-stuck-or-waiting.md)
- [OpenClaw integration](help/openclaw-integration.md)
- [Install and onboard](help/install-and-onboard.md)
- [Diagnostic bundle](help/diagnostic-bundle.md)
- [FAQ](help/faq.md)

## Maintainers

- [Maintain docs](maintainers/maintain-docs.md)
- [Choose a verification lane](maintainers/choose-a-verification-lane.md)
- [Maintain packaging](maintainers/maintain-packaging.md)
- [Maintain database support](maintainers/maintain-database-support.md)
- [Prepare a release](maintainers/prepare-a-release.md)
- [Recover a broken release](maintainers/recover-a-broken-release.md)

## Public and internal docs

`docs/**` is the public product, guide, help, and reference surface.

`docs-internal/**` is implementation canon: target design, shipped-behavior contrast, ADRs, and internal architecture records.
