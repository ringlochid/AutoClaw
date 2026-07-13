# Console page state contracts

Status: Target

This page owns the user-visible runtime states the V2 console must render. It consumes finalized Control API and task-event names without adding frontend lifecycle states.

## Shared page states

Every data-backed runtime surface supports:

- initial loading
- ready content
- empty content where the source permits it
- normalized authorization, validation, network, and controller errors
- stale mutation followed by targeted source refresh
- narrow viewport without hiding current status or lawful actions

Event-backed surfaces also support disconnected, reconnecting, and `cursor_reset_required`. Those are transport presentation states, not task or provider states.

## Task selection

The task entry surface routes to task detail and displays only fields supplied by the existing task-list contract. This page does not add list counts, aggregate metrics, provider health, or runtime fields absent from that route.

Task status labels preserve controller values. External-wait, recovery, and provider-control detail belongs to the selected task's Control API read.

## Task detail

Task detail bootstraps from the current task read and snapshot, then attaches event chronology. Its required regions are:

- compact task and current-node identity
- current attempt plan and semantic progress
- requested and resolved provider provenance
- current dispatch and provider-control readback
- watchdog restart and pause/recovery state
- current external wait when present
- ordered task chronology
- selected graph, trace, checkpoint, boundary, request, or run context
- lawful task controls

Source state remains readable when SSE is disconnected.

### Plan states

| Source state | Presentation |
| --- | --- |
| `current_plan = null` with an active worker attempt | awaiting the worker's first plan; do not fabricate steps |
| current plan with one `in_progress` step | render ordered steps and highlight only that active step |
| every step `completed` | render the plan as complete without implying the task boundary committed |
| new semantic attempt with no plan | start a separate plan-history group for the new attempt |
| `plan_updated` history | expose revisions in event order with explanation and update provenance |

Plan completion never renders the task as succeeded by itself. Boundary and task source state remain authoritative.

### Progress states

`last_progress_at` appears as an exact timestamp with an optional derived relative-time label. Null means no semantic progress has committed for that dispatch; it does not prove whether adapter start occurred. It does not mean disconnected, failed, or zero percent complete.

The console does not show an activity clock from reads, provider output, MCP transport, or task-event arrival.

### Provider resolution states

| Requested versus resolved | Presentation |
| --- | --- |
| equal | show the resolved provider once with requested/resolved detail available |
| different | show requested and resolved values and label the resolution as fallback |

No state implies that the provider is connected, generating, finished, or healthy.

### Provider-control states

| `state` | Required presentation |
| --- | --- |
| `queued` | operation queued; show attempt budget when present |
| `attempting` | operation and `attempt / max_attempts` |
| `retry_scheduled` | operation, attempt budget, `next_retry_at` countdown, and bounded error summary when present |
| `succeeded` | completed AutoClaw control operation, not provider task completion |
| `failed` | bounded failure summary and controller state that follows |
| `null` | no current provider-control operation |

The matching control-event chronology shows exact `reason`: `initial_dispatch`, `watchdog_recovery`, `operator_cancel`, or `shutdown`. `initial_dispatch` means a non-watchdog provider start; the matching `dispatch_opened.reason` preserves the more specific external-wait, operator-continue, or semantic-retry cause. The UI does not add reason values.

### Watchdog recovery states

| Source state | Presentation and action |
| --- | --- |
| restart count zero and no recovery control | ordinary runtime; no recovery alert |
| restart count above zero with active control | show count and current stop/start control readback |
| replacement dispatch opened | preserve same-attempt plan while chronology shows the replacement |
| task paused with `runtime_recovery_exhausted` | show exhausted-recovery notice, latest bounded control error, and repair guidance |
| repaired exhausted recovery | ordinary operator continue action; render the returned same-attempt dispatch |

The console never runs continue automatically when a countdown ends or provider readiness changes.

### Task controls

Pause, continue, and cancel use current controller guards and distinct confirmations.

- Pause holds task progression and may stop a live dispatch through the controller.
- Continue resumes an operator-paused task or repaired `runtime_recovery_exhausted` task.
- Cancel is terminal controller intent.

Continue is not offered as a way to answer a human request or finish a command run.

## Human requests

The task-local human-request surface supports:

- no request history
- current open `direction`, `approval`, `input`, or `review` request
- typed item navigation and response controls
- validation error without losing entered answers
- successful answer and source refresh
- terminal `resolved`, `timed_out`, or `cancelled` history
- stale or no-longer-current resolve rejection

Only the current open request offers resolve controls. Request summary, item prompt, options or structured input, item-scoped notes, and final submission stay distinct.

The page never becomes a generic chat or provider approval surface.

## Command runs

The task-local command-run surface supports:

- empty history
- `pending_start`
- `running`
- `cancellation_requested`
- terminal `succeeded`, `failed`, `timed_out`, or `cancelled`
- bounded progress summary when supplied
- detail expansion
- explicit log loading, missing log, and log error
- cancel accepted, denied, stale, and terminally unavailable

`cancellation_requested` stays visibly non-terminal and keeps the task waiting. The cancel action does not claim success before the source row becomes `cancelled`.

Ordinary rows show normalized summary and provenance. Raw command output appears only in the explicit authorized log view and never replaces source state.

## Task chronology

The chronology supports:

- REST backfill before live tail
- ascending event sequence
- reconnect and deduplication
- plan revision expansion
- provider-control reason and retry detail
- checkpoint, boundary, external-wait, task-control, and structural events
- empty history
- cursor reset

Provider events and per-MCP-invocation events never appear.

On cursor reset, the page discards event-derived current display assumptions, rereads task and snapshot source state, refreshes selected source detail, and reconnects from the new stream head.

## Data exclusion states

No page adds a disclosure, debug tab, or fallback rendering for:

- credentials
- `provider_session_hint`
- provider-native event or output payloads
- raw provider logs
- provider run ids
- unsupported progress, ETA, throughput, or health

Authorized command-run logs remain a separate controller route and are not provider logs.

## Owner boundary

This page owns required render states only. It does not define API fields, event payloads, backend legality, runtime transitions, provider behavior, authoring pages, or visual tokens.

## Related contracts

- [Console target](README.md)
- [API and view-model boundary](api-and-view-model-boundary.md)
- [Component system](component-system.md)
- [Console runtime surfaces](../interfaces/console-runtime-surfaces.md)
- [Control API](../interfaces/control-api.md)
- [Task event stream](../interfaces/task-event-stream.md)
