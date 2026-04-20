# Flow 02 — Default Runtime Lifecycle

Last verified: 2026-04-20

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

## Advancement note

Current baseline:

- `continue_flow()` / `advance_flow_until_boundary()` are the advancement entry points
- current implementation advances until the next real runtime boundary inside one controller call
- the important current boundaries are:
  - a running delegated attempt
  - a projected manifest waiting for acknowledgement
  - pending approval / watchdog / operator wait state
  - terminal flow completion
- `continue_flow()` also attempts detached OpenClaw dispatch after the controller reaches a dispatchable boundary

Next-stage target:

- keep the boundary table explicit and runtime-owned rather than scattering the policy across routes and presenters
- see `07-controller-driven-implementation-loop.md`
