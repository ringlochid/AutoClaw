# Runtime model

Status: Reference

The runtime model is the controller-owned record of one launched task. It explains what is current, what happened, what evidence exists, and what the controller can do next.

Authored definitions explain reusable intent. Runtime records explain one execution.

## Lifecycle

A task usually moves through this loop:

1. Task start compiles the selected workflow and pins current role and policy revisions.
2. Launch persists the task, task-compose body, compiled plan, flow, nodes, edges, root assignment, attempt, dispatch, and root bindings.
3. The current dispatch sends the node its rendered prompt and mounted tools.
4. The node records checkpoints and artifacts as it works.
5. The node reaches a boundary, opens a human request, starts a command run, or is recovered by operator/runtime control.
6. The controller advances, retries, replans, waits, releases, blocks, or opens the next dispatch.

The controller updates runtime truth first, then writes generated projections such as workflow manifests, assignments, checkpoint files, artifact indexes, and observability refs.

## Core runtime nouns

- **task:** one launched unit of work with a selected workflow and task root
- **compiled plan:** the launch-time snapshot of the workflow, role revisions, policy revisions, and dependency graph
- **flow:** the active runtime graph for the task
- **flow node:** one root, parent, or worker node inside the flow
- **assignment:** the current mission prose and criteria context for one node
- **attempt:** one execution attempt for an assignment
- **dispatch:** one delegated turn opened for the current node attempt
- **checkpoint:** durable progress or terminal handoff written during an attempt
- **artifact:** durable output published into a declared produced slot
- **boundary:** the node's control-flow return, such as `yield`, `green`, `retry`, or `blocked`
- **wait state:** a controller-owned pause caused by a human request or command run
- **structural revision:** an adopted replan of the active flow shape

## Boundaries and progress

A checkpoint records what the node learned or produced. A boundary tells the controller what should happen next.

For ordinary child handoff, a parent/root assigns child work and returns `yield`. For completion, a node returns `green` only after publishing required evidence. For recoverable failure, it returns `retry` with terminal retry evidence. For honest dead end, it returns `blocked` with a terminal blocked checkpoint.

Parent/root release is evidence-driven. A parent should inspect child checkpoints, artifacts, criteria, and surfaced refs before releasing a subtree or whole task.

## Human requests

Human requests are typed waits for human judgment. They are useful when the node cannot safely continue from current evidence.

Common request kinds are:

- `direction`: the next path depends on human judgment
- `approval`: work should not continue without explicit permission
- `input`: required facts are missing
- `review`: a human review gate is part of the workflow

Human request capability is granted by policy. A node that lacks that capability should not treat ordinary chat continuation as a hidden workflow boundary.

## Command runs

Command runs are controller-managed long-running command work. They create a `waiting_for_command_run` state, emit command-run events, preserve logs, and allow the operator to inspect or cancel the run without cancelling the whole task.

Use command runs only when command work is expected to exceed a normal dispatch. Ordinary commands should stay inline and comfortably under about two minutes.

Command-run capability is separate from human request capability. A policy may grant one, both, or neither.

## Replan

Replan changes the active flow shape when the current structure cannot honestly complete the task. It is for structural mismatch, missing work lanes, invalid dependency shape, or a repeated failure pattern that needs a different subtree.

Replan is not a substitute for retry. Retry is for another attempt at the same assignment shape. Replan is for changing the shape.

## Readbacks and projections

Runtime truth lives in controller-owned records. Public files and read models help humans and workers inspect that truth:

- `_runtime/workflow-manifest.md` summarizes the current workflow and relevant refs
- `_runtime/attempts/<attempt_id>/assignment.md` shows the active assignment surface
- `_runtime/attempts/<attempt_id>/latest-checkpoint.md` shows the latest durable handoff
- `outputs/artifacts/` stores published artifacts
- operator snapshot and trace views summarize current state and history
- observability refs expose dispatch support files for debugging transport and recovery

If a generated projection and controller readback disagree, prefer controller/runtime truth.

## Related pages

- [Core concepts](core-concepts.md)
- [Inspect your first run](../start/inspect-your-first-run.md)
- [Inspect and control a task](../guides/inspect-and-control-a-task.md)
- [Operator reference](../reference/operator/README.md)
