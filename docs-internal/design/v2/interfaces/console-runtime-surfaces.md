# Console runtime surfaces

Status: Target

This page owns the V2 console's runtime-facing product model: current task state, semantic progress, provider-control readback, watchdog recovery, external waits, task chronology, and operator controls.

It does not own backend schemas, event payloads, provider behavior, definition authoring, or literal visual styling. Those remain with their named owners.

## Core rule

The console renders controller truth; it does not reconstruct an agent runtime from provider behavior.

Current state comes from Control API source-row reads. Ordered history and live chronology come from persisted task events. Source-specific detail comes from the human-request and command-run routes.

The console never treats provider output, provider events, provider logs, support files, or opaque provider continuity as product truth.

## Authority split

| Surface | Authority role | Console use |
| --- | --- | --- |
| Control API task and snapshot reads | current source-row state | bootstrap and refresh the current task view |
| Control API human-request and command-run reads | complete external-wait source records | render request forms, run detail, and legal actions |
| Task event list and SSE | append-only chronology | render revision history, control attempts, waits, checkpoints, and boundaries in order |
| Trace | historical controller read model | inspect dispatch, checkpoint, boundary, and graph history |
| Provider-native output | none | never rendered as runtime truth |

Task events do not replace current source rows. A newer-looking event cannot overrule `RuntimeFlowRead`, the current external-wait record, or controller action legality.

## Primary runtime experience

The runtime console centers on four coordinated surfaces:

1. task selection and compact task status
2. task detail with the current execution tree and runtime summary
3. ordered task chronology
4. selected context for plans, dispatches, human requests, command runs, checkpoints, and boundaries

These surfaces may share one responsive page, but their authority roles remain distinct. The task tree answers what work exists, the runtime summary answers what is current, the chronology answers what happened, and the selected context exposes detail and lawful actions.

## Current plan and semantic progress

For the active worker attempt, the console renders the complete current `AttemptPlan` from `RuntimeFlowRead.current_plan`:

- attempt identity
- plan revision
- optional explanation
- ordered steps using only `pending`, `in_progress`, and `completed`
- dispatch and timestamp provenance supplied by the plan read

Plan revision history comes from ordered `plan_updated` task events. Each event is a bounded complete plan snapshot for one attempt and revision. The console groups history by `attempt_id` and orders it by event sequence; it never manufactures revisions from local edits or provider messages.

The console renders `current_dispatch.last_progress_at` as the last semantic controller progress time. It may present an accessible relative-time label derived from that timestamp while preserving the exact timestamp in detail. It does not turn plans into percentages, infer ETA, or treat read-only MCP traffic as progress.

When `current_plan` is null, the console distinguishes the controller-defined cases: no active worker attempt, or the worker has not yet committed its first plan. It does not synthesize a placeholder plan.

## Provider resolution provenance

The console renders the finalized provider-resolution provenance exactly as:

- `requested_provider`
- `resolved_provider`

When the values differ, the console may label the resolved provider as a fallback. It does not invent a fallback chain, model name, provider run id, or provider health state.

Provider selection is dispatch provenance, not watchdog truth. A provider badge never implies that the provider is currently generating, connected, or complete.

## Provider-control readback

For the current dispatch, the console renders the persisted provider-control fields:

- `operation`
- `state`
- `attempt`
- `max_attempts`
- `next_retry_at`
- `last_error_summary`

The matching `dispatch_control_updated` event supplies the bounded control `reason` for chronology. For starts, `initial_dispatch` covers every non-watchdog dispatch start; the more specific continuation or retry cause comes from `dispatch_opened.reason`. The console may show those values beside the corresponding rows, but it does not fold either event into a replacement current-state record.

The retry countdown is derived from `next_retry_at` and the client clock. It is presentation only; reaching zero never schedules a retry or mutates controller state. The console refreshes current source rows after a control event rather than assuming the event payload is the latest state.

Control `state` remains AutoClaw's start/stop operation state:

- `queued`
- `attempting`
- `retry_scheduled`
- `succeeded`
- `failed`

It is never relabeled as an agent lifecycle, provider completion, or provider health state.

## Watchdog recovery

The console renders the active attempt's `watchdog_restart_count` and the ordinary runtime state around it.

During recovery, dispatch and provider-control source reads show the current stop or start work. Task events explain the ordered recovery attempts. The console does not create a separate recovery state machine.

When recovery exhausts, the canonical presentation is:

- task status `paused`
- `pause_reason = runtime_recovery_exhausted`
- the latest bounded provider-control failure readback
- ordinary operator `continue` as the recovery action after the provider is repaired

The console must not present continue as a provider reconnect, automatic retry, human-request answer, or command-run completion. It invokes the ordinary controller continue route and renders the returned source truth.

## Human-request waits

An open human request is a controller-owned external wait. The console renders:

- current waiting cause from `RuntimeFlowRead`
- compact current request summary in task context
- the complete request and resolution history from the dedicated source-row route
- typed item controls for `direction`, `approval`, `input`, or `review`
- terminal request history without illegal resolve actions

The console resolves only the current open request through its dedicated route. It never uses task continue as an answer path and never exposes provider-native question or approval UI.

## Command-run waits

A current command run is another controller-owned external wait. The console renders:

- exact source state from `pending_start`, `running`, `cancellation_requested`, `succeeded`, `failed`, `timed_out`, or `cancelled`
- command, description, workdir, timing, timeout, and bounded summary fields supplied by the source read
- terminal result and cancellation provenance when present
- cancel only while the Control API allows it

`cancellation_requested` remains non-terminal. The task continues waiting until the command-run source becomes terminal.

Ordinary views use bounded summaries and log references. An authorized explicit log inspection may call the dedicated command-run log route. Command output never replaces the normalized source state.

## Task chronology and cursor reset

The execution chronology renders persisted task events in ascending `event_seq` order. Event type remains the primary label; provider or adapter is never an event source.

The client keeps cursor, high-water mark, ordering, and deduplication explicit. On `cursor_reset_required`, it performs the canonical reset:

1. discard event-derived current-state assumptions
2. reread `GET /control/tasks/{task_id}`
3. reread `GET /control/tasks/{task_id}/snapshot`
4. reread source-specific detail when the selected view requires it
5. reconnect after `stream_head_event_id`

Cursor reset returns to a fresh source-row snapshot. The console never rebuilds current state by folding retained events.

## Operator controls

Pause, continue, cancel, human-request resolution, and command-run cancellation use their dedicated Control API routes and current controller guards.

Rules:

- disabled buttons are presentation; backend legality remains authoritative
- current structural revision guards come from fresh source reads
- stale or illegal mutations render the shared structured failure and trigger a targeted refresh
- pause does not resolve an external wait
- continue does not resolve an external wait
- task cancel is distinct from command-run cancel

## Data exclusions

Ordinary console product views never render or persist:

- raw provider events or provider-native tool events
- provider credentials or authentication material
- `provider_session_hint`
- provider run identifiers or adapter-private handles
- raw provider output or logs
- `NodeMcpInvocation` rows
- support-file projections as currentness
- fabricated percent complete, ETA, throughput, or provider health

## Owner boundary

This page owns runtime console behavior and presentation semantics. It does not define:

- Control API fields or routes
- task event payloads or retention
- runtime lifecycle transitions or retry defaults
- provider setup, authentication, or readiness
- human-request or command-run source state machines
- definition registry or authoring workflows
- final colors, spacing, typography, or implementation framework

The console subtree owns API mapping, page states, and component semantics for this interface.

## Related contracts

- [Console target](../console/README.md)
- [Control API](control-api.md)
- [Task event stream](task-event-stream.md)
- [Runtime lifecycle and watchdog](../architecture/runtime-lifecycle-and-watchdog.md)
- [Runtime records and control state](../architecture/runtime-records-and-control-state.md)
- [Attempt plan and checkpoint contract](../architecture/attempt-plan-and-checkpoint-contract.md)
- [Human request and approval contract](human-request-and-approval-contract.md)
- [Command run and external wait](../architecture/command-run-and-external-wait.md)
- [Provider selection and runtime config](provider-selection-and-runtime-config.md)
