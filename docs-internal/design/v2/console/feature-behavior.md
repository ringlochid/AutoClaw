# Console Feature Behavior Contract

Date: 2026-06-30

This document defines the user-visible behavior required for each console page. Backend/OpenAPI truth wins for route shape, state names, action legality, auth, and currentness. Served design references win for visual hierarchy, interaction layout, density, active states, and responsive behavior.

## Shared Behavior

- The console is task-first. Runtime work begins from Tasks; Task Detail, Human Requests, and Command Runs are task-scoped siblings.
- Definitions, Task Start, and Definition Editor are authoring surfaces.
- No page may display fake metrics, fake counts, ETAs, progress percentages, unsupported support-file truth, unsupported routes, or labels not backed by source and backend contract.
- Loading, empty, no-results, auth/error, validation, and narrow viewport states are required review states for every page that can reach them.
- Implementation reviews must inspect actual app config/source before judging active-state behavior.

## Tasks

Design anchors: `tasks.html`, `tasks.png`, `shared-ui.css`, `shared-shell.js`, and the Tasks page charter.

Backend anchor: `GET /runtime/tasks`.

Required states: loading, populated list, empty list, no search results, search, status filter, sort, pagination/load more, row open/focus, API/auth error, and narrow stacked controls.

Behavior contract:

- Show runtime task list data only from the backend route or fixtures that faithfully model it.
- Status filters and sort controls must match backend-supported values.
- Rows open task detail without inventing task metadata.
- The Tasks nav item remains active for task detail, human-request, and command-run task-scoped routes.

## Task Detail

Design anchors: `task-detail.html`, `task-detail-modal-open.png`, shared CSS/JS, and the Task Detail page charter. `task-detail.png` is caveated by the design docs and must not be the sole visual authority.

Backend anchors: runtime task detail, control snapshot, trace, event list, event stream, pause, continue, and cancel routes.

Required states: REST bootstrap, snapshot graph, trace/event lane, live stream, cursor reset, stream error, selected graph/event detail, detail modal tabs, pause/continue/cancel legal/disabled/stale, empty event lane, and task-scoped sibling links.

Behavior contract:

- Display task graph, event, checkpoint, assignment, boundary, artifact, and trace details only from backend/control data.
- Pause, continue, and cancel must use current backend action legality and currentness requirements, including fresh `expected_active_flow_revision_id` when required.
- Cursor reset is a first-class recovery state, not a silent failure.

## Human Requests

Design anchors: `human-request.html`, `human-request.png`, shared CSS/JS, and the Human Requests page charter.

Backend anchors: task-scoped human-request list and resolve routes.

Required states: empty queue, pending queue, `direction`, `approval`, `input`, and `review` requests, option selection, freeform input, structured input, notes, resolve success, validation error, terminal readback, stale request, and auth/error.

Behavior contract:

- Resolve controls must be typed to the request kind.
- The page must not become a generic chat, continue-task, or approval tunnel.
- Terminal requests remain readable without offering illegal resolution actions.

## Command Runs

Design anchors: `command-runs.html`, `command-runs.png`, shared CSS/JS, and the Command Runs page charter.

Backend anchors: task-scoped command-run list, detail, log, and cancel routes.

Required states: empty list, `pending_start`, `running`, `cancellation_requested`, `succeeded`, `failed`, `timed_out`, `cancelled`, expanded detail, hidden log, visible log, missing log, cancel allowed, cancel denied, and auth/error.

Behavior contract:

- Log content, command, timing, state, and provenance come from command-run routes only.
- Do not show progress, ETA, or invented health labels.
- Cancel affordance must follow backend legality.

## Definitions

Design anchors: `definitions.html`, `definitions.png`, shared CSS/JS, and the Definitions page charter.

Backend anchors: definition list/detail/history routes for `role`, `policy`, and `workflow`.

Required states: kind switch, search, filter, sort, populated list, empty/no-results, selected detail, version history, stale selected entity, auth/error, Definition Editor handoff, and Task Start handoff.

Behavior contract:

- Do not assume a mixed-definition endpoint.
- Filters must be kind-appropriate and backend-supported.
- Handoffs to editor and task start must preserve the distinction between stored definitions, flat definition drafts, and task-startable workflow definitions.

## Task Start

Design anchors: `task-start.html`, `task-start.png`, shared CSS/JS, and the Task Start page charter.

Backend anchors: workflow definition list/detail/history routes and `POST /tasks/start`.

Required states: workflow search/select, workflow detail/history, required fields, root selection modes, optional params, preview modal/disclosure, validation errors, successful start, occupied root, unknown workflow, and auth/error.

Behavior contract:

- Preview is a user-facing review of the request payload, not a fake backend simulation.
- Do not launch drafts or expose raw manifest paths unless backend and product contract explicitly support it.
- Root ownership and validation errors must follow backend shape.

## Definition Editor

Design anchors: `definition-editor.html`, `definition-editor.png`, `definition-editor-replace-modal.png`, shared CSS/JS, and the Definition Editor page charter.

Backend anchors: flat authoring draft routes.

Required states: draft list, empty draft list, create draft client template, load existing draft, clean editor, dirty editor, save, validate, preview, apply, reset, rematerialize/replace modal, stale draft, validation warnings/errors, auth/error, and focus recovery.

Behavior contract:

- Stored definition truth, flat draft truth, and task-start truth stay separate.
- Reset and rematerialize/replace are distinct operations and need distinct confirmation behavior.
- Apply, validate, preview, and save feedback must match authoring route responses.
