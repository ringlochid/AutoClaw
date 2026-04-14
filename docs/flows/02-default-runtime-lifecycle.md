# Flow 02 — Default Runtime Lifecycle

## Sequence

```text
Compile -> create flow -> create initial flow_revision -> materialize flow_nodes/flow_edges
-> pick runnable node -> create node_attempt -> project context_manifest
-> bootstrap delegated node (read + acknowledge context)
-> dispatch execution to OpenClaw
-> receive node_checkpoint -> update node/flow state -> continue
```

## State changes

- `flow_node.ready` -> `flow_node.running`
- `node_attempt.running` -> `succeeded|blocked|failed|cancelled`
- `flow` transitions are derived from node and approval state

## Minimal control requirement

- one execution slice = one `node_attempt`
- one checkpoint sequence belongs to one node attempt
- one structural change requires a new flow revision
- delegated execution should not start until the node attempt has acknowledged its projected context manifest
