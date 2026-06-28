# AutoClaw docs

Status: Reference

AutoClaw is a local-first workflow control plane for compiling, launching, supervising, and closing structured work.

Use this front door for the public docs story: first success, core concepts, practical guides, exact reference, and maintainer follow-through. Internal engineering canon lives under [`docs-internal/`](../docs-internal/README.md).

## Start here

- [Getting started](start/getting-started.md)
- [Run your first task](start/first-task.md)
- [Inspect your first run](start/inspect-your-first-run.md)

## Learn the model

- [Overview](concepts/overview.md)
- [Core concepts](concepts/core-concepts.md)
- [Workflow lanes](concepts/workflow-lanes.md)
- [Workspace model](concepts/workspace-model.md)
- [Definitions model](concepts/definitions-model.md)

## Build and operate

- [Create your first definition set](guides/create-your-first-definition-set.md)
- [Design workflows and instructions](guides/design-workflows-and-instructions.md)
- [Choose a workflow lane](guides/choose-a-workflow-lane.md)
- [Bind a real workspace](guides/bind-a-real-workspace.md)
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
