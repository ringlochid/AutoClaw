# Flow 04 — Approval and Watchdog

## Purpose

Show how AutoClaw stays safe and observable during long-running work.

## Approval flow

```text
risky next step
-> approval record created
-> child pauses at safe boundary
-> human approves / rejects / requests replan
-> runtime resumes or stops
```

## Watchdog flow

```text
runtime signals
-> watchdog classification
-> healthy | blocked | slow | stalled | lost
-> recovery action or continued wait
```

## Notes

Approval and watchdog logic operate on runtime state.
They should not infer truth only from chat history or raw logs.
