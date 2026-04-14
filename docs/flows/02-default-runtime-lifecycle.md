# Flow 02 — Default Runtime Lifecycle

## Sequence

```text
Compile -> create flow -> pick runnable leaf -> dispatch to OpenClaw -> receive checkpoint
-> update flow_node_state -> continue
```

## State changes

- `ready` -> `running`
- `running` -> `blocked` or `done` or `failed`

## Minimal control requirement

- one checkpoint per control slice
- one state transition per checkpoint
