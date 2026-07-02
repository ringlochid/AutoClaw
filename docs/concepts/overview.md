# Overview

AutoClaw turns reusable workflow definitions and one concrete launch request into a controller-owned workflow run. Use it when the work needs bounded delegation, durable evidence, retry, replan, human waits, long command runs, or operator recovery.

## The short model

AutoClaw docs separate three layers:

1. **General orchestration:** why long delegated work needs more than chat memory.
2. **Definition authoring:** how roles, policies, workflows, and task-compose describe reusable intent and one launch.
3. **Runtime operation:** how manifest, assignment, attempt, dispatch, checkpoint, artifact, boundary, wait, and replan describe one running task.

Read [orchestration model](orchestration-model.md) before memorizing runtime nouns.

## Launch sequence

| Concept | Definition | Why it matters |
| --- | --- | --- |
| Workflow | reusable node tree, routing, criteria, and evidence contract | gives the task shape and closure requirements |
| Task-compose | one launch request | binds the workflow to the task instruction and optional roots |
| Assignment | controller-owned scope, instructions, and evidence requirements for the active node | keeps delegation explicit |
| Checkpoint | controller-recorded progress or handoff for one assignment attempt | lets another node or operator inspect current evidence |
| Artifact | durable output published into a declared slot | gives later nodes and operators a stable output to consume |

A checkpoint is read after the assignment because it records progress against that assigned scope.

## What AutoClaw owns

- definition registry revisions used by compile and launch
- compiled task flow, nodes, assignments, attempts, and dispatches
- checkpoint and artifact publication
- boundary handling for `yield`, `green`, `retry`, and `blocked`
- human request and command-run wait states
- structural replan and flow revision adoption
- operator readbacks, trace, and recovery controls

## What AutoClaw is not

AutoClaw is not a prompt library. Prompts are dispatch-specific projections over controller truth.

AutoClaw is not hidden chat memory. A run can be reconstructed from the workflow manifest, assignment, checkpoints, artifacts, and operator readbacks.

AutoClaw is not a generic shell runner. Ordinary commands should stay inline. Controller-managed command runs are for long-running command work that needs logs, terminal state, cancellation, or continuation.

## Where to go next

- [Orchestration model](orchestration-model.md)
- [Core concepts](core-concepts.md)
- [Authoring model](authoring-model.md)
- [Runtime model](runtime-model.md)
- [Design workflows and instructions](../guides/design-workflows-and-instructions.md)
