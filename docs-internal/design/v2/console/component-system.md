# Console component system

Status: Target

This page owns reusable V2 console component semantics for runtime truth. It does not freeze a particular framework, final visual values, backend fields, or task transitions.

## Core rule

Components make controller state easy to scan without turning provider or transport detail into product truth.

The console uses one compact operational language for plans, progress, provider control, recovery, external waits, chronology, and lawful actions.

## Shell and composition

The task runtime shell keeps these regions distinct:

- task navigation
- current runtime summary
- execution tree or trace context
- event chronology
- selected detail or action context

At wide widths, the regions may sit beside one another. At narrow widths, they stack in the same semantic order. Current state and required actions must not disappear behind hover-only or desktop-only affordances.

Task detail, human requests, and command runs remain task-scoped siblings. Definition authoring navigation may exist elsewhere in the app shell, but it is not owned by this runtime component contract.

## Tokens and variants

Shared console tokens use the `--ac-*` namespace and cover:

- background and surface hierarchy
- text and muted text
- borders and focus rings
- spacing and density
- radius and shadow
- semantic information, success, warning, failure, paused, waiting, and neutral treatments

State color always appears with text or an icon label. Components use explicit variants keyed to finalized controller states; they do not construct arbitrary style names from backend strings.

## Runtime components

### Plan panel

The plan panel renders revision, optional explanation, ordered steps, update provenance, and revision-history access.

Step variants are exactly:

- `pending`
- `in_progress`
- `completed`

Only one active step receives primary emphasis. Completed steps remain readable. The panel does not add percentages, progress bars, or ETA.

### Semantic progress time

The progress component renders `last_progress_at` with an exact timestamp available to assistive technology and detail views. A relative label is presentation only and updates without mutating task state.

Null progress uses neutral copy. It must not appear as provider failure or zero progress.

### Provider provenance

The provider component renders requested and resolved values. Equal values remain compact; differing values expose the fallback relationship without inventing a fallback chain or provider health.

### Provider-control status

The control component renders:

- operation and controller-owned state
- `attempt / max_attempts`
- retry countdown from `next_retry_at`
- bounded `last_error_summary`
- documented event reason when shown in chronology

Countdown changes must not resize surrounding rows. The component never labels control success as assignment completion.

### Recovery notice

The recovery component renders watchdog restart count and, when applicable, the `runtime_recovery_exhausted` pause.

The exhausted variant includes:

- precise pause reason
- latest bounded provider-control failure
- instruction to repair provider availability or configuration
- ordinary continue action after repair

It does not offer a provider-native reconnect action.

### External-wait card

Human-request and command-run cards share compact task-wait structure while preserving distinct source states and actions.

Human-request cards show typed request kind, title, summary, source status, and resolve affordance only for the current open source.

Command-run cards show exact state, command summary, bounded update, terminal result when present, and cancel only when legal. `cancellation_requested` uses a waiting treatment, not a terminal cancelled treatment.

### Event row

Event rows preserve event type, sequence, occurrence time, and controller context. Plan, control, checkpoint, boundary, wait, and task-control details use bounded disclosures.

Provider and adapter are not event-source variants. Rows do not render raw payload dumps by default.

### Task tree and selected context

The task tree stays read-only and compact. It emphasizes the current path and uses the selected context for rich assignment, checkpoint, artifact, dispatch, request, or run detail.

Provider resolution detail, full plan history, and action forms belong in summary or selected detail, not repeated on every node card.

## Controls and feedback

Buttons, icon buttons, segmented controls, tabs, inputs, selects, textareas, disclosure rows, status chips, empty states, error states, dialogs, and drawers share:

- visible keyboard focus
- stable size across hover, focus, countdown, and status changes
- disabled explanation where legality is not obvious
- pending mutation feedback tied to the exact controller action
- normalized failure summary and suggested next step

Destructive task cancel remains visually distinct from command-run cancel and nonterminal pause.

Dialogs trap focus, provide an accessible name, associate validation errors with fields, and restore focus to the triggering control on close.

## Responsive and accessibility rules

- preserve task status, current wait, recovery notice, and lawful primary action at narrow widths
- keep timestamp, retry count, and state available as text, not color alone
- announce materially changed control and wait states without announcing every countdown tick
- make plan revision and event disclosures keyboard operable
- preserve readable source order when panes stack
- avoid nested scroll regions that hide current actions or error summaries
- keep action hit targets usable without inflating the overall operational density

## Data exclusions

No component variant exists for raw provider events, credentials, `provider_session_hint`, provider run ids, raw provider logs, fabricated provider health, progress percentage, ETA, or throughput.

The explicit command-run log viewer is a controller-backed source-specific component and remains separate from ordinary runtime summaries.

## Owner boundary

This page owns reusable component meaning and accessibility. [Page state contracts](page-state-contracts.md) owns when states appear, [API and view-model boundary](api-and-view-model-boundary.md) owns their data, and [Console runtime surfaces](../interfaces/console-runtime-surfaces.md) owns the product composition.

## Related contracts

- [Console target](README.md)
- [API and view-model boundary](api-and-view-model-boundary.md)
- [Page state contracts](page-state-contracts.md)
- [Console runtime surfaces](../interfaces/console-runtime-surfaces.md)
