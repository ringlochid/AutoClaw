# Authoring, Compiler, and Runtime

## Source layer

- role definitions and versions
- policy definitions and versions
- workflow definitions and versions
- skill references

## Compiler layer

- validates definitions
- normalizes plan structure
- emits immutable compiled plan + node/edge skeleton

## Runtime layer

- imports compiled plan into a `flow`
- reads `flow_node` ownership + `flow_edges`
- dispatches leaf tasks to OpenClaw-bound sessions
- reacts only on checkpoint outcomes

## Hard boundary

A child execution result never directly rewrites graph shape.
Shape changes must go through explicit replan revision flow.
