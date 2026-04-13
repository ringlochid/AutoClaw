# Flow 02 — Default Runtime Lifecycle

## Purpose

Show the normal small-kernel runtime path.

## Default path

```text
parent supervisor
-> main execution loop child
-> optional review
-> sync / report
```

## Walk-through

1. runtime starts a run from a compiled plan
2. parent supervisor inspects current state and dispatches the child
3. child performs local work (`implement -> test -> triage -> retry`)
4. child emits a typed checkpoint
5. parent decides whether to continue, review, approve, block, or finish
6. sync/report runs only after the work is ready to publish outward

## Notes

This is the default AutoClaw path.
Bigger trees are extensions.
