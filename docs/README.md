# AutoClaw docs

Status: Reference

AutoClaw is a local-first workflow control plane for compiling, launching, supervising, and closing structured work.

Use this front door for the public docs story: first success, core concepts, practical guides, exact reference, and maintainer follow-through. Internal engineering canon lives under [`docs-internal/`](../docs-internal/README.md).

## Start here

- [Getting started](start/getting-started.md)
- [Start a task](start/start-a-task.md)
- [Inspect a task](start/inspect-a-task.md)

## Learn the model

- [Overview](concepts/overview.md)
- [Core concepts](concepts/core-concepts.md)
- [Runtime model](concepts/runtime-model.md)
- [Authoring model](concepts/authoring-model.md)
- [Task-compose model](concepts/task-compose-model.md)
- [Workspace model](concepts/workspace-model.md)
- [Operator model](concepts/operator-model.md)
- [Capability model](concepts/capability-model.md)

## Build and operate

- [Write a task-compose file](guides/write-a-task-compose.md)
- [Create a definition set](guides/create-a-definition-set.md)
- [Choose a workflow lane](guides/choose-a-workflow-lane.md)
- [Design workflows and instructions](guides/design-workflows-and-instructions.md)
- [Use human requests](guides/use-human-requests.md)
- [Use long command runs](guides/use-long-command-runs.md)
- [Recover or replan a task](guides/recover-or-replan-a-task.md)
- [Inspect and control a task](guides/inspect-and-control-a-task.md)

## Exact reference

- [CLI reference](reference/cli/README.md)
- [API reference](reference/api/README.md)
- [Operator reference](reference/operator/README.md)
- [Definitions reference](reference/definitions/README.md)

## Maintainers

- [Packaging guide](maintainers/packaging.md)
- [Release guide](maintainers/release.md)
- [Testing guide](maintainers/testing.md)

## Help

- [Troubleshooting](help/troubleshooting.md)
- [FAQ](help/faq.md)

## Surface rule

Use `docs/**` for public product and reference material only.

Use `docs-internal/**` for engineering design, implementation records, ADRs, and archive material.
