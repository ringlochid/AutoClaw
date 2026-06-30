# Console Feature Behavior

Status: Locked target for implementation planning.

This page defines what users can see and do in the AutoClaw console. Backend
and API contracts still own data truth, action legality, event chronology, and
currentness.

## Global Rules

- Runtime begins at `Tasks`; do not create another runtime home.
- Runtime task pages use `Tasks > {task title or task id}` breadcrumbs.
- Authoring pages use authoring breadcrumbs and never appear under a selected
  task.
- Loading, empty, no-results, error, permission, stale-action, and conflict
  states render inside the surface that owns the failed read or action.
- Actions are visible or enabled only when controller truth and currentness
  allow them. Missing buttons are not a legality model by themselves.
- User-facing copy uses product nouns: `Tasks`, `Task Detail`,
  `Human Requests`, `Command Runs`, `Definitions`, `Definition Editor`, and
  `Task Start`.
- Implementation route prefixes such as `/runtime`, `/control`, `/operator`,
  `/observability`, `/callback`, and `/node/mcp` are not primary UI labels.
- Do not invent controller-backed fields, lifecycle states, aggregate counts,
  progress, ETA, or launch readiness to make placeholders feel complete.

## Tasks

Purpose: let an operator scan task rows, narrow the list, and open one task.

Required behavior:

- Query through `q`, filter by shipped status values, sort by shipped sort
  values, and load more through `cursor` and `next_cursor`.
- Rows prioritize task title, summary, status, updated time, and open target.
- Secondary metadata may show workflow key, current node key, active attempt id,
  or task id when the layout stays scan-first.
- Opening a row routes to `Task Detail`.

Required states:

- loading or refresh
- mixed dense task list
- no tasks
- no results for current query/filter
- read error
- auth or permission failure
- focus and hover on row/open controls
- cursor-backed load more

Forbidden states:

- row-level waiting cause, request count, run count, child count, artifact
  count, or dashboard metrics unless a later task-list route exposes bounded
  fields
- pause, continue, cancel, human-request resolution, or command-run cancel on
  the list page
- numbered page totals, fake totals, or page-count UI

## Task Detail

Purpose: let an operator inspect one task, read current task shape, follow
persisted chronology, inspect selected detail, and take legal task-level
controls.

Required behavior:

- Bootstrap from REST: task read, snapshot, trace, and event backfill when
  `stream_head_event_id` exists.
- Use the shared fetch-based SSE transport for live updates.
- Render a read-only execution graph, chronological task-event lane, and
  selected detail.
- Support selected detail views named `Overview`, `Checkpoint`, `Assignment`,
  `Boundary`, `Artifacts`, and `Trace`.
- Render every current `TaskEventType` family by its controller event name.
- Pause, continue, and cancel submit the current
  `expected_active_flow_revision_id` and surface stale or illegal-state
  errors.
- Link to `Human Requests` and `Command Runs` as sibling pages. Compact
  previews may appear only from controller-backed reads.

Required states:

- running task with graph, events, and legal controls
- selected node, selected event, and focused detail
- trace view for every event family
- checkpoint, assignment, boundary, artifact/ref detail
- human-request and command-run previews
- paused, stale-action, cancelled, no-history, long-event-list, and read-error
  states
- deep or wide graph with readable default zoom and reset
- SSE reconnect/reset after `cursor_reset_required`

Forbidden states:

- chat framing
- graph editing
- synthesized event families or chronology from trace, snapshot, support files,
  provider traces, or local UI state
- raw logs, prompt packages, manifests, or large payload bodies in event rows
- command-run cancel or human-request resolve as generic task controls

Task Detail visual release cannot close from the current `task-detail.png`
alone. It needs fresh promoted capture or an explicit replacement visual-review
anchor.

## Human Requests

Purpose: let an operator resolve typed pending human requests for one task.

Required behavior:

- Use the task-scoped human-request list and resolve control routes.
- Show a request queue and one focused selected request item.
- Preserve request-level summary separately from item-level response controls.
- Support request kinds `direction`, `approval`, `input`, and `review`.
- For option-based items, submit exactly one selected option or one freeform
  answer, plus optional item-scoped notes.
- For `input` items, validate and submit a schema-backed `response_payload`
  when the controller provides a schema.
- Show suggested human instruction, due time, recommendation, timeout/default
  behavior, and terminal readback when available.

Required states:

- open direction/review/approval/input requests
- multi-item navigation with per-item response memory
- mixed queue with one selected request
- empty queue
- resolved, timed out, and cancelled terminal readback
- stale or resolved-elsewhere conflict
- auth, legality, and validation errors

Forbidden states:

- generic chat, transcript recovery, or `continue` tunneling
- treating an approval rejection option as request status `cancelled`
- always-open giant multi-item form
- invented risk, expected-effect, progress, or default-response metadata

## Command Runs

Purpose: let an operator inspect task-scoped controller-managed command runs.

Required behavior:

- Use command-run list, detail, log, and cancel routes.
- Render states `pending_start`, `running`, `cancellation_requested`,
  `succeeded`, `failed`, `timed_out`, and `cancelled`.
- Keep rows compact: description, command, bounded summary, state, and legal
  action.
- Open full detail through disclosure grouped by command, result, timing,
  provenance, and log access.
- Logs are hidden by default and load only when `log_ref` exists.
- Cancel only when controller-backed state and action contract allow it.

Required states:

- every command-run state
- expanded row with full record
- log hidden, log visible, and missing-log variants
- legal cancel, stale/denied cancel, empty list, read error, and auth failure

Forbidden states:

- cross-task command dashboard
- always-visible raw logs
- progress percentage, ETA, throughput, elapsed-time widgets, or progress rings
- terminal-state inference from logs or local UI heuristics

## Definitions

Purpose: let an author browse current stored roles, policies, and workflows.

Required behavior:

- Use separate list reads for roles, policies, and workflows.
- Keep a visible kind switch; do not fake a mixed registry endpoint.
- Search, sort, filter, and cursor-load within the selected kind only.
- Roles may filter by `allowed_node_kind`; policies may filter by `applies_to`;
  workflows do not inherit those filters.
- Selected detail comes from `GET /definitions/{kind}/{key}`.
- Version history comes from `GET /definitions/{kind}/{key}/versions` and stays
  behind compact `Versions` disclosure.
- Adjacent pivots to `Definition Editor` and workflow-only `Task Start` are
  handoffs, not inline editor or launch flows.

Required states:

- role, policy, and workflow list views
- kind switching without stale filters or stale detail leakage
- selected current detail
- single and multi-revision history
- empty, no-results, detail-missing, read-error, and auth states

Forbidden states:

- repo YAML or seed files as live registry truth
- invented author identity, validation status, launch readiness, mixed
  stored/draft badges, or workflow compatibility badges
- prompt preview, diff, draft editing, or task launch inside the browse surface

## Definition Editor

Purpose: let an author edit backend-owned draft sets and apply them to stored
definition truth without confusing draft, preview, and launch truth.

Required behavior:

- Use `/authoring/definition-draft-sets/*` routes for draft-set lifecycle,
  materialization, save, reset, rematerialize-current, validate, preview, and
  apply.
- Keep stored truth, draft-set truth, preview truth, diff truth, and task-start
  launch truth visibly separate.
- Draft selector rows stay compact: key, kind, and status.
- `Reset draft` restores the captured draft baseline or local starter baseline.
- `Replace with current stored revision` is a separate explicit
  rematerialize-current action that discards local edits only after explicit
  intent.
- Validation distinguishes schema, cross-reference, stale, preview, warning,
  no-op, and new-revision outcomes.
- Preview labels provenance as stored truth or draft truth.
- Task start remains a separate page and launches only from current stored
  controller truth.

Required states:

- default workbench with draft rail and editor
- new draft modal and added draft state
- dirty and clean draft states
- reset confirmation and rematerialize-current confirmation
- validation pending, valid, warning, invalid, and stale
- preview unavailable, stored truth preview, draft truth preview
- apply no-op and new revision outcomes
- auth and permission failure

Forbidden states:

- unsaved draft as current, applied, or launchable
- autosave, collaboration presence, approval, or compile states not owned by
  the controller
- reset that silently fetches newest stored registry truth
- browser-only draft state as saved backend truth

## Task Start

Purpose: let an author launch a task from current stored workflow truth.

Required behavior:

- Discover workflows through stored definition reads.
- Launch through `POST /tasks/start` only.
- Collect task key, title, summary, optional instruction, workflow key, and
  optional workspace/context root bindings.
- Root modes are `ensure_task_default`, `ensure_host_path`, and
  `use_existing_host`.
- `host_path` is forbidden for `ensure_task_default` and required for the two
  host-path modes.
- Preview is local semantic readback over selected stored workflow and current
  form fields. It is not controller truth and not a server-side preflight.
- Success renders compact handoff readiness without default raw ids, compiled
  plan ids, flow revision ids, or raw manifest filesystem paths.

Required states:

- ready-to-launch with selected workflow
- workflow search/loading/empty
- required-field errors
- all root binding mode combinations
- preview modal/disclosure
- success result with `flow_status`
- unknown workflow, invalid host path, occupied workspace, auth error, and
  validation error

Forbidden states:

- launch from unsaved drafts, repo files, preview output, or diff output
- server-side dry-run or preflight claims before a backend route exists
- runtime graph, event thread, human-request handling, or command-run detail
  inside Task Start
- raw request JSON or raw host-path echoes as default visible result copy
