# Core concepts

AutoClaw separates reusable design, one launch request, controller-owned runtime state, and operator readbacks. Each surface has different authority.

## Planes

| Plane     | Owns                             | Example nouns                                                                              |
| --------- | -------------------------------- | ------------------------------------------------------------------------------------------ |
| Authoring | reusable definitions             | role, policy, workflow, node, criteria, consumes, produces                                 |
| Launch    | one concrete task request        | task-compose, task instruction, workspace root, context root                               |
| Runtime   | controller-owned execution state | task, flow, assignment, attempt, dispatch, checkpoint, artifact, boundary, wait, replan    |
| Operator  | trusted inspection and control   | snapshot, trace, human request resolution, command-run inspection, pause, continue, cancel |

## Launch concepts

- **Workflow:** reusable node tree, routing rules, criteria, and evidence contract.
- **Task-compose:** one launch request with task metadata, instruction, workflow key, and optional roots.
- **Assignment:** controller-owned scope, instructions, and evidence requirements for an active node.
- **Checkpoint:** controller-recorded progress or handoff record for one assignment attempt.
- **Artifact:** durable output published into a workflow-declared slot.

## Definition concepts

Definitions are reusable:

- **Role:** reusable instructions for how a node performs a class of work.
- **Policy:** reusable authority limits, budgets, capabilities, and guardrails.
- **Workflow:** reusable node tree, routing rules, criteria, consumed evidence, and produced artifacts.
- **Node:** one planned work unit inside a workflow tree.
- **Criteria:** hard closure requirements.
- **Consumes:** evidence a node is required to read.
- **Produces:** artifact slots a node is required to publish.

## Runtime concepts

Runtime nouns describe one launched task:

- **Task:** one launched unit of work.
- **Compiled plan:** launch-time snapshot of workflow, roles, policies, and dependencies.
- **Flow:** active runtime graph for the task.
- **Flow node:** one root, parent, or worker node in the flow.
- **Attempt:** one try at an assignment.
- **Dispatch:** one opened agent turn for an attempt.
- **Boundary:** node exit such as `yield`, `green`, `retry`, or `blocked`.
- **Wait:** controller pause caused by a human request or command run.
- **Replan:** controller-approved structural change to the active flow.

Generated task-root files such as manifest, assignment, checkpoint, and artifacts are materialized projections over controller-owned runtime records. They make runtime truth readable; they do not replace controller truth.

## Node kinds

- `root`: owns whole-task purpose and final closure.
- `parent`: owns routing and release for a subtree.
- `worker`: performs one bounded assignment.

Runtime node kind is derived from workflow tree position: the top node becomes the root, leaf nodes become workers, and intermediate nodes become parents.

## Budgets and authority

Policies attach by node kind through `applies_to`.

- `retry_limit` belongs on worker policies.
- `child_assignment_limit` belongs on root or parent policies.
- A policy must not mix retry and child-assignment budgets.
- Omitted `budget_spec` means no controller budget counter for that budget family.

Budgets do not grant tools. Human request and command-run capability are separate policy fields.

## Proof model

AutoClaw treats evidence as part of the workflow contract:

- criteria define hard closure requirements
- consumes declare the evidence a node needs
- produces declare durable outputs
- checkpoints record progress and handoff context
- artifacts carry inspectable output

A child `green` boundary is an evidence claim, not final closure. Parent and root nodes should inspect current evidence before release.

## Small example

A small bugfix workflow might have a root, an implementer, and a reviewer.

1. Root assigns a bounded fix mission to the implementer.
2. Implementer patches, tests, publishes a patch summary and verification artifact, records a checkpoint, then returns `green`.
3. Root or parent assigns review.
4. Reviewer consumes the patch and verification artifact, publishes review evidence, records a checkpoint, then returns `green` or `blocked`.
5. Root closes only after current evidence satisfies criteria.

## Related pages

- [Orchestration model](orchestration-model.md)
- [Authoring model](authoring-model.md)
- [Runtime model](runtime-model.md)
- [Policy model](policy-model.md)
- [Design workflows and instructions](../guides/design-workflows-and-instructions.md)
