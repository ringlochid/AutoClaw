# Core concepts

Status: Reference

AutoClaw separates reusable design, concrete launch input, runtime truth, and operator readbacks. Most confusion comes from mixing those surfaces.

## Four planes

### Authoring plane

The authoring plane contains reusable definitions:

- roles describe a stable capability profile and instruction contract
- policies describe budgets, retries, guardrails, and allowed capabilities
- workflows describe the node tree, durable criteria, consumed inputs, and produced artifacts

These files are importable definition inputs. After seed or upload, current registry revisions become the source used by compile and launch.

### Launch plane

The launch plane is task-compose. It names one concrete task, selects a workflow, carries the task instruction, and binds roots such as `workspace` and `context` to host paths.

Task-compose is not a reusable workflow definition. It is the launch body for one task.

### Runtime plane

The runtime plane is the controller-owned record of one launched task. It includes the task, compiled plan, flow, nodes, assignments, attempts, dispatches, checkpoints, artifacts, boundaries, wait states, and structural revisions.

Runtime state is the authority for what is current. Generated task-root files and operator read models are projections over that state.

### Operator plane

The operator plane exposes views and controls for trusted runtime steering. Operators inspect snapshots and traces, resolve human requests, read or cancel command runs, pause or continue tasks, and recover from failures.

Operator readbacks are useful views. They do not replace controller-owned runtime truth.

## People

- definition author: writes reusable roles, policies, and workflows
- task launcher: creates a task-compose body and starts concrete work
- operator: inspects runtime state, reviews evidence, and uses control or recovery surfaces

## Node kinds

Node kind comes from workflow structure:

- `root`: the top node that owns whole-task closure
- `parent`: a non-root node with children; it orchestrates a subtree
- `worker`: a leaf node with no children; it performs one bounded assignment

Review, verification, research, implementation, planning, failure analysis, and release work are modes of work. They are not separate node kinds.

## Proof model

AutoClaw treats evidence as part of the workflow contract:

- `criteria` are hard acceptance or guardrail requirements
- `consumes` declare durable artifacts or criteria a node needs before work can proceed
- `produces` declare durable artifacts a node must publish before successful completion
- checkpoints record progress, reasoning, criteria status, and handoff context during execution
- artifacts carry durable output that later nodes and operators can inspect

A child returning green is evidence, not proof by itself. Parent and root nodes should inspect current evidence before release.

## Capability boundaries

Policies can allow human requests and command runs independently.

Human request capability is for typed human judgment: direction, approval, input, or review.

Command-run capability is for controller-managed long-running command work. It should not be used for ordinary commands that can finish inline inside a dispatch.

## Small example

A minimal implementation workflow may have one root and one worker. The root reads the task instruction, assigns the worker, then waits for the worker checkpoint and produced artifacts. The worker completes the scoped change, publishes verification evidence, records a checkpoint, and returns a terminal boundary. The root then decides whether the evidence satisfies the criteria, needs retry, needs replan, or should close.

## Related pages

- [Definitions model](definitions-model.md)
- [Runtime model](runtime-model.md)
- [Workflow lanes](workflow-lanes.md)
- [Workspace model](workspace-model.md)
- [Inspect and control a task](../guides/inspect-and-control-a-task.md)
