# Authoring, Compiler, and Runtime

## Source layer

- role definitions and versions
- policy definitions and versions
- workflow definitions and versions
- skill references

Skill scope rule:

- role/workflow skill declarations are allowed as authoring/default layers
- compiled/runtime execution truth must be node-local effective skill bindings

## Compiler layer

The compiler:

- validates source definitions
- resolves pinned versions
- computes an explicit effective-node artifact from role / workflow / node / replan inputs
- validates merged effective-node semantics, not only raw graph structure
- normalizes graph structure
- emits immutable `compiled_plans`, `compiled_plan_nodes`, and `compiled_plan_edges`

Each compiled node carries version provenance and effective execution meaning:

- `role_version_id`
- `policy_version_id`
- `skill_bindings[*].skill_version_id`
- effective mode / metadata / skill state after merge

Graph/workflow-scope skill declarations should therefore compile into node-local effective skill bindings rather than remaining graph-scoped at runtime.

## Skill reference contract (recommended target)

AutoClaw should treat skills as **pinned OpenClaw artifacts plus extracted manifest summary**, not as a second skill-logic format.

Definition/registry storage should keep enough information to pin, inspect, search, and materialize a skill safely:

- `provider`
- `key`
- `version_label`
- `skill_version_id`
- `runtime_name` (the exact `name` from `SKILL.md`)
- `source_uri` / `source_ref`
- `artifact_ref` (for example `.skill` blob or unpacked skill directory reference)
- `artifact_sha256`
- `manifest_summary` parsed from `SKILL.md` frontmatter
  - `name`
  - `description`
  - `user-invocable`
  - `disable-model-invocation`
  - selected `metadata.openclaw.*` fields such as `primaryEnv`, `requires`, and `install`

The compiler should collapse role/workflow/node/replan skill declarations into a **node-local effective binding set**.
Each resolved binding should be strong enough to drive runtime dispatch without re-reading authoring defaults.

Illustrative binding shape:

```json
{
  "provider": "openclaw",
  "key": "contract-checker",
  "runtime_name": "contract-checker",
  "version_label": "2026-04-17",
  "skill_version_id": "8c3b4c2d-...",
  "source_ref": "clawhub://openclaw/contract-checker@2026-04-17",
  "artifact_ref": "s3://autoclaw-skills/contract-checker/2026-04-17.skill",
  "artifact_sha256": "abc123...",
  "manifest": {
    "name": "contract-checker",
    "description": "Check frontend/backend contract drift",
    "user_invocable": false,
    "disable_model_invocation": false,
    "metadata": {
      "openclaw": {
        "primaryEnv": "OPENAI_API_KEY",
        "requires": {
          "bins": ["node"],
          "env": ["OPENAI_API_KEY"]
        }
      }
    }
  },
  "state": "required",
  "provenance": {
    "effective_layer": "workflow"
  }
}
```

## Runtime layer (target)

The runtime should:

1. create a `flow` for a task
2. create an initial `flow_revision` from a `compiled_plan`
3. materialize `flow_nodes` and `flow_edges`
4. pick runnable nodes
5. create `node_attempts` for actual execution slices
6. project a policy-filtered context slice for the node attempt
7. persist a `context_manifest` for that projected slice
8. resolve the node-local effective skill binding set for dispatch
9. materialize or verify the pinned OpenClaw skill packages for the delegated session
10. dispatch bootstrap instructions to OpenClaw for read + acknowledge
11. only after successful context acknowledgement, and only with required skills available, dispatch delegated node work to OpenClaw with a session-level skill filter that reflects the node-local bindings
12. persist `node_checkpoints`
13. advance node/flow state only from checkpoint or operator events

## Context bootstrap boundary

AutoClaw should not rely on "please read this first" prompt wording alone.

Before delegated execution:

- the controller projects a node-scoped context slice from shared/private workspace items
- the slice is filtered by role, skill bindings, and policy visibility
- the controller persists a `context_manifest` containing required and optional items plus hashes
- the controller includes the node-local skill contract in the manifest or sibling dispatch payload, including required/allowed/blocked runtime skill names plus pinned binding summaries
- required skills are materialized in the delegated session before execute-phase work starts
- the delegated session enters a bootstrap/read phase first

Execution should begin only after the delegated node acknowledges the manifest.

That acknowledgement may be recorded in manifest metadata directly or linked to a checkpoint, but it is a controller-enforced gate rather than a soft convention.

## Skill availability rule

If a node declares a skill as `required` and AutoClaw cannot materialize or verify that skill for the delegated session, the node should block before execute rather than relying on prompt luck.

## Hard boundary

- Runtime never executes raw source definitions directly.
- Runtime never mutates graph shape in place during a node call.
- Structural changes go through proposal -> validate -> compile -> adopt.
- Shared workspace publication should happen at checkpoint boundaries or explicit operator action, not as uncontrolled transcript residue.

## Legacy note

The old `run -> attempt -> flow` shape is historical only.
The live runtime contract is `task -> flow -> flow_revision -> flow_node -> node_attempt`.
