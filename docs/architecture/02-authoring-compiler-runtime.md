# Authoring, Compiler, and Runtime

## Source layer

- role definitions and versions
- policy definitions and versions
- workflow definitions and versions
- skill references

## Compiler layer

The compiler:

- validates source definitions
- resolves pinned versions
- normalizes graph structure
- emits immutable `compiled_plans`, `compiled_plan_nodes`, and `compiled_plan_edges`

Each compiled node carries version provenance:

- `role_version_id`
- `policy_version_id`
- `skill_bindings[*].skill_version_id`

## Runtime layer (target)

The runtime should:

1. create a `flow` for a task
2. create an initial `flow_revision` from a `compiled_plan`
3. materialize `flow_nodes` and `flow_edges`
4. pick runnable nodes
5. create `node_attempts` for actual execution slices
6. project a policy-filtered context slice for the node attempt
7. persist a `context_manifest` for that projected slice
8. dispatch bootstrap instructions to OpenClaw for read + acknowledge
9. only after successful context acknowledgement, dispatch delegated node work to OpenClaw
10. persist `node_checkpoints`
11. advance node/flow state only from checkpoint or operator events

## Context bootstrap boundary

AutoClaw should not rely on "please read this first" prompt wording alone.

Before delegated execution:

- the controller projects a node-scoped context slice from shared/private workspace items
- the slice is filtered by role, skill bindings, and policy visibility
- the controller persists a `context_manifest` containing required and optional items plus hashes
- the delegated session enters a bootstrap/read phase first

Execution should begin only after the delegated node acknowledges the manifest.

That acknowledgement may be recorded in manifest metadata directly or linked to a checkpoint, but it is a controller-enforced gate rather than a soft convention.

## Hard boundary

- Runtime never executes raw source definitions directly.
- Runtime never mutates graph shape in place during a node call.
- Structural changes go through proposal -> validate -> compile -> adopt.
- Shared workspace publication should happen at checkpoint boundaries or explicit operator action, not as uncontrolled transcript residue.

## Legacy note

Current code still instantiates `run -> attempt -> flow`.
The roadmap migrates that shape to `task -> flow -> flow_revision -> flow_node -> node_attempt`.
