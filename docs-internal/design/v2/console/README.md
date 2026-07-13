# Console target

Status: Reference

This directory is the V2 implementation-facing console contract for runtime state, task chronology, provider control, recovery, and external waits.

The primary product owner is [Console runtime surfaces](../interfaces/console-runtime-surfaces.md). The pages here translate that product contract into frontend data boundaries, page states, and component semantics without redefining backend truth.

## Pages

- [API and view-model boundary](api-and-view-model-boundary.md) owns source-row, event, mapping, error, and cursor-reset boundaries.
- [Page state contracts](page-state-contracts.md) owns the required runtime page states and lawful transitions.
- [Component system](component-system.md) owns shared visual, interaction, responsive, and accessibility semantics.

This README is the only console subtree router. The four files in this directory are the complete live V2 console target set.

## Authority order

Console implementation follows this order:

1. Control API source-row contracts for current state and mutation legality
2. task event contracts for chronology and live updates
3. human-request and command-run source owners for complete external-wait detail
4. console runtime surface rules for product composition
5. console page and component contracts for presentation

Generated OpenAPI types remain the TypeScript wire source. Explicit mappers may shape render-ready views, but they must preserve controller names and states.

## Scope

This subtree covers:

- current attempt plan and plan revision history
- `last_progress_at`
- requested and resolved provider provenance
- provider-control operation, retry, countdown, error, and reason presentation
- watchdog restart count and exhausted-recovery pause
- ordinary continue after provider repair
- human-request and command-run waits
- source-row refresh, task-event chronology, and cursor reset

It does not own definition authoring, provider onboarding, backend routes or schemas, runtime behavior, task-file projections, or implementation evidence programs.

## Non-negotiable exclusions

The console does not invent backend fields, lifecycle states, counts, progress percentages, ETA, provider health, or action legality. Ordinary product views never expose raw provider events, credentials, `provider_session_hint`, raw provider output, or raw provider logs.

## Related contracts

- [Console runtime surfaces](../interfaces/console-runtime-surfaces.md)
- [Control API](../interfaces/control-api.md)
- [Task event stream](../interfaces/task-event-stream.md)
- [Runtime lifecycle and watchdog](../architecture/runtime-lifecycle-and-watchdog.md)
