# Control UI runtime and authoring surfaces

Status: Target

This page defines the Vnext control UI surface model for runtime tracking, human-request handling, command-run inspection, and definition authoring.

## Core rule

The UI must be built over controller-owned task truth, `task_event` history, pending human-request records, command-run records, and definition-registry truth.

It must not imply features or fields that the controller contract does not own.

The UI is not:

- a chat-first surface
- a workflow-editor canvas
- a support-file reader
- a fabricated progress or metrics dashboard for data the runtime does not persist

## Primary runtime surfaces

The runtime control experience should center on three coordinated surfaces:

1. a read-only task tree
2. an execution thread over `task_event`
3. a selected inspector surface

Rules:

- the task tree answers "what is the current shape of the work"
- the execution thread answers "what happened and in what order"
- the inspector answers "what is selected right now and what can I do with it"
- these surfaces may share one page, but they must stay conceptually distinct

## Task tree rules

The task graph is a read-only execution tree, not a free-form editor.

Rules:

- root node appears at the top
- parent and worker descendants appear beneath their committed parent
- staged relationships may appear as dashed or otherwise visually secondary edges
- the active lineage should be visually emphasized
- done or quiet subtrees may collapse, but the current active path must remain obvious
- node cards should stay compact and should not duplicate rich inspector detail

Minimum node-card content:

- title
- role or kind
- current status
- one short checkpoint or assignment summary
- one compact hint such as waiting cause, artifact count, or child count when useful

When provider preference matters, the graph may show one compact provider badge, but requested versus resolved provider detail belongs in the inspector.

The graph must not become the place where full checkpoint prose, request forms, or artifact inventories live.

## Execution thread rules

The execution thread is a chronological rendering of `task_event`.

Rules:

- thread rows are event-driven, not support-file-driven
- event type is primary
- secondary chips or labels stay compact and low-contrast
- detail actions such as `View state` are secondary, not the main visual signal on every row
- the execution thread may open the inspector to a selected event or selected node context, but it is not itself the inspector

The execution thread may live in a center or right pane. It should not be overloaded with unrelated forms.

## Inspector rules

The inspector is for the currently selected task, node, request, job, artifact set, or event context.

Recommended tabs or equivalent views are:

- `Overview`
- `Checkpoint`
- `Assignment`
- `Artifacts`
- `Human Requests`
- `Command Runs`
- `Trace`

Rules:

- tab names should map to real controller-backed surfaces
- do not promise arbitrary `Metrics` or other views unless controller truth later defines them
- logs may appear only where a command run or other contract-backed source actually exposes logs
- current controller-backed human-request or command-run legality may appear in the selected inspector when the relevant node or action surface is selected
- the UI must not infer capability from missing buttons alone; it should read the controller-provided capability view or event payload
- when a selected node or dispatch has provider provenance, the inspector may show requested provider and resolved provider

## Human-request UI rules

Human requests are first-class interactive work items.

They may appear:

- in a global inbox
- in a task-local request list
- in a selected request drawer or side pane

They should not be treated as dense inline clutter inside the execution thread by default.

Rules:

- request-level summary stays separate from item-level response controls
- if a request contains multiple items, the UI should show one focused item at a time
- item navigation should use compact previous and next controls plus an item position indicator
- answers are item-scoped, not one undifferentiated freeform blob for the whole request

Recommended request surface structure:

1. request summary
2. current item header and item prompt
3. item navigator
4. item options or input controls
5. item-scoped notes
6. final resolve actions

## Command-run UI rules

Command runs are inspectable runtime records, not a guaranteed progress dashboard.

Rules:

- the UI may show run state, latest summary, and logs when present
- the UI may show a textual latest progress update when controller-owned progress events exist
- the UI must not assume controller-owned percent complete, ETA, elapsed time, throughput, or progress rings unless a later contract explicitly adds those fields
- the default command-run read should be the normalized latest summary, not a raw result dump
- full logs should open only on explicit inspect actions when present
- log-backed raw output should not replace the displayed controller state or normalized summary
- command-run inspection may live beside execution as its own selectable surface rather than being permanently embedded inside the execution thread

Recommended command-run surface content:

- run id
- command
- description
- state
- workdir when present
- created, started, and ended timestamps
- timeout when declared
- latest progress or update summary when present
- terminal summary plus exit code or signal when present
- logs link or log panel when present
- cancellation action when legal

## Runtime page composition rule

The main task-detail page should feel sparse and inspectable, not crowded.

Recommended composition:

- left or center tree canvas
- sibling execution thread
- sibling inspector or context pane

If the UI uses a compact mode switch for the right-side pane, preferred surface families are:

- `Execution`
- `Human Requests`
- `Command Runs`

Do not mix execution thread, large request form, command-run pseudo-metrics, and unrelated inspector tabs into one dense undifferentiated column.

## Definition authoring mode

Authoring is a separate major surface from live runtime control, even if both live in one app shell.

The authoring workbench should contain:

- registry browser
- draft workspace
- validation panel
- apply or publish actions
- optional task-compose preview and post-apply task-start surface

Rules:

- drafts are not runtime truth
- the UI must show saved draft state separately from stored current truth
- saved draft state comes from backend-owned draft-set storage rather than browser-owned truth
- the exact draft-set, validation, apply, and stale semantics belong to the definition authoring API and draft-set contract rather than this page

## Non-goals

This page does not define:

- literal final spacing, color, or typography choices
- a Figma component library
- numeric command-run progress models that the controller does not own
- workflow-authoring canvas editing in the runtime task graph

## Related contracts

- [Control API and task event stream](control-api-and-task-event-stream.md)
- [Human request and approval contract](human-request-and-approval-contract.md)
- [Command run and long-running boundary](../architecture/command-run-and-long-running-boundary.md)
- [Definition authoring workbench](definition-authoring-workbench.md)
- [Definition authoring API and draft-set contract](definition-authoring-api-and-draft-set-contract.md)
- [Provider preference and runtime config](provider-selection-and-runtime-config.md)
- [Prompt system vnext](../prompt-layer/prompt-system-vnext.md)
