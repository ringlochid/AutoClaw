# Runtime model

The runtime model is the controller-owned record of one launched task. It explains what is current, what happened, what evidence exists, and what the controller can do next.

Authored definitions explain reusable intent. Runtime records explain one execution.

## Lifecycle

A task usually moves through this loop:

1. Task start compiles the selected workflow and pins current role and policy revisions.
2. Launch persists the task, compiled plan, flow, nodes, root assignment, attempt, dispatch, and root bindings.
3. The current dispatch sends the node its rendered prompt, generated files, and allowed tools.
4. The node works through the harness loop.
5. The node records checkpoints, publishes artifacts, opens a wait, stages a child assignment, or returns a boundary.
6. The controller advances, retries, replans, waits, releases, blocks, or opens the next dispatch.

The controller updates runtime truth first, then materializes generated projections such as workflow manifests, assignments, checkpoint files, artifact indexes, and support refs.

## Core runtime nouns

| Noun | Meaning |
| --- | --- |
| Task | one launched unit of work |
| Compiled plan | launch-time snapshot of workflow, role revisions, policy revisions, and dependency graph |
| Flow | active runtime graph for the task |
| Flow node | one root, parent, or worker node inside the flow |
| Assignment | current bounded mission for one node |
| Attempt | one try at an assignment |
| Dispatch | one delegated harness turn for the current attempt |
| Manifest | generated whole-flow projection for humans and agents |
| Checkpoint | durable progress or terminal handoff written during an attempt |
| Artifact | durable output published into a declared produced slot |
| Boundary | node control return: `yield`, `green`, `retry`, or `blocked` |
| Wait state | controller pause caused by a human request or command run |
| Structural revision | adopted replan of the active flow shape |

## Assignment before checkpoint

Assignment is the mission. Checkpoint is the evidence written against that mission.

A good assignment is bounded enough that another node or operator can tell whether the work stayed in scope. A good checkpoint says what happened, what evidence exists, what criteria are satisfied or not, and what risk remains.

## Boundaries and progress

A checkpoint records what the node learned or produced. A boundary tells the controller what should happen next.

- `yield`: parent/root has staged child work or needs the controller to continue later.
- `green`: the node believes its current assignment is complete with evidence.
- `retry`: worker assignment failed in a recoverable way and should get another attempt.
- `blocked`: the node cannot honestly continue from current evidence.

Parent/root terminal closure requires release preconditions before final `green` or whole-flow `blocked`. That keeps closure evidence-driven instead of letting a model simply declare success.

## Human requests

Human requests are typed waits for human judgment:

- `direction`: the next route depends on human choice
- `approval`: work should not continue without permission
- `input`: required facts are missing
- `review`: human review is part of closure

Human request capability is granted by policy. A node that lacks that capability should not treat ordinary chat continuation as a hidden workflow boundary.

## Command runs

Command runs are controller-managed long-running command work. They create a `waiting_for_command_run` state, emit command-run events, preserve logs, and allow the operator to inspect or cancel the run without cancelling the whole task.

Use command runs when command work is expected to exceed a normal dispatch or needs durable logs, terminal state, cancellation, or continuation. Ordinary commands should stay inline and finish comfortably under about two minutes.

## Replan

Replan changes the active flow shape when the current structure cannot honestly complete the task.

Use replan for:

- missing work lanes
- invalid dependency shape
- repeated failures that show the assignment shape is wrong
- mismatch between user intent and current node tree
- review evidence proving the workflow is judging the wrong thing

Use retry for another attempt at the same assignment shape. Use replan when the shape itself is wrong.

## Materialization

Materialization is the act of projecting controller-owned runtime truth into durable files or read models.

Materialized surfaces are not casual logs. They are the shared workbench for agents, operator agents, human operators, and debugging tools:

- `_runtime/workflow-manifest.md` summarizes the current workflow and refs
- `_runtime/attempts/<attempt_id>/assignment.md` shows the active assignment
- `_runtime/attempts/<attempt_id>/latest-checkpoint.md` shows durable progress or handoff
- `outputs/artifacts/` stores published artifacts
- operator snapshot and trace views summarize current state and history
- support refs expose dispatch files for debugging transport and recovery

The direction matters:

```text
controller truth -> materialized files/readbacks -> agent and operator inspection
```

Do not reverse it. A task-root file can help a node or operator understand the run, but it does not legalize a state transition by itself. If a generated projection and controller readback disagree, prefer controller/runtime truth.

## MCP node tools

AutoClaw exposes runtime transitions through node tools. The important families are:

- lookup: `search_definitions`, `get_definition`
- progress: `record_checkpoint`
- boundary: `return_boundary`
- external waits: `open_human_request`, `start_command_run`
- parent/root control: `assign_child`, structural edit tools, `release_green`, `release_blocked`

Every mutating call is validated against current task, session key, dispatch, assignment, attempt, node authority, and flow revision.

## Related pages

- [Orchestration model](orchestration-model.md)
- [Core concepts](core-concepts.md)
- [Inspect a task](../start/inspect-a-task.md)
- [Inspect and control a task](../guides/inspect-and-control-a-task.md)
- [Recover or replan a task](../guides/recover-or-replan-a-task.md)
