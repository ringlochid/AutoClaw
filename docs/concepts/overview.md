# Overview

Status: Reference

AutoClaw is an orchestration layer for structured AI-assisted work. It turns reusable workflow definitions and one concrete launch request into controller-owned runtime state that can be inspected, resumed, replanned, or closed with evidence.

Use AutoClaw when a task needs more structure than a chat transcript can provide: multiple roles, bounded assignments, durable checkpoints, artifacts, human-in-the-loop decisions, long command runs, or operator recovery.

## The short model

An AutoClaw run moves through a small set of surfaces:

1. Author reusable role, policy, and workflow definitions.
2. Seed or upload those definitions into the registry.
3. Start a concrete task from a task-compose launch body.
4. Compile the current registry revisions into a runtime flow.
5. Dispatch the current root, parent, or worker node.
6. Record checkpoints, artifacts, boundaries, waits, and replans as controller-owned runtime state.
7. Inspect or control the task through operator read and recovery surfaces.

The important rule is that authored files describe reusable intent. Runtime records describe what happened in one launched task.

## What AutoClaw owns

- authored definitions for roles, policies, and workflows
- task-compose launch input for one concrete task
- registry revisions used by compile and launch
- runtime flow, node, assignment, attempt, and dispatch records
- durable evidence through criteria, checkpoints, and artifacts
- human request and command-run wait states
- operator read, control, and recovery surfaces

## What AutoClaw is not

AutoClaw is not just a prompt library. Prompt text is one projection of controller-owned task state, not the source of truth.

AutoClaw is not hidden chat memory. A run should be understandable from its workflow manifest, assignment surfaces, checkpoints, artifacts, and operator readbacks.

AutoClaw is not a generic shell runner. Ordinary commands should finish inline and comfortably under about two minutes. Controller-managed command runs are for long-running command work that must outlive a single dispatch.

## Built-in orchestration features

- **Parent and root orchestration:** parent nodes can assign child work, inspect child evidence, release completed subtrees, or block honestly.
- **Replan:** the runtime can adopt revised structure when the current flow shape no longer fits the work.
- **Human-in-the-loop:** policies can allow specific human request kinds such as direction, approval, input, or review.
- **Long command runs:** policies can allow controller-managed command runs without granting unrelated human request capabilities.
- **Operator recovery:** a trusted OpenClaw operator agent can inspect task state, trace events, resolve human requests, read or cancel command runs, and recover from runtime issues; humans should do equivalent steering through UI surfaces.

## Where to go next

- [Core concepts](core-concepts.md) for the main nouns and truth boundaries
- [Runtime model](runtime-model.md) for task, flow, assignment, attempt, dispatch, checkpoint, artifact, boundary, and wait-state concepts
- [Authoring model](authoring-model.md) for reusable authored inputs
- [Task-compose model](task-compose-model.md) for concrete launch input
- [Write a workflow](../guides/write-a-workflow.md) for purpose-specific automation design
- [Workspace model](workspace-model.md) for task roots and host path binding
- [Operator model](operator-model.md) and [Capability model](capability-model.md) for control, human requests, command runs, and replan
- [API reference](../reference/api/README.md) and [CLI reference](../reference/cli/README.md) for exact contracts
