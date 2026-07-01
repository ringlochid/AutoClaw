# Core concepts

AutoClaw separates reusable design, one launch request, runtime truth, and operator readbacks. Most confusion comes from mixing those surfaces.

## Four planes

| Plane | Owns | Example nouns |
| --- | --- | --- |
| Authoring | reusable definitions | role, policy, workflow, node, criteria, consumes, produces |
| Launch | one concrete task request | task-compose, task instruction, workspace root, context root |
| Runtime | controller-owned execution state | task, flow, assignment, attempt, dispatch, checkpoint, artifact, boundary, wait, replan |
| Operator | trusted inspection and control | snapshot, trace, human request resolution, command-run inspection, pause, continue, cancel |

Authored files describe intent. Runtime records describe what happened in one launched task. Operator readbacks help humans and trusted operators inspect that runtime truth.

## The minimum vocabulary

Learn these first:

- **Workflow:** reusable evidence path for a kind of work.
- **Task-compose:** one concrete launch request.
- **Assignment:** bounded mission currently given to a root, parent, or worker node.
- **Checkpoint:** durable progress or handoff record for an assignment attempt.
- **Artifact:** durable output published into a declared slot.

Assignment is the delegation boundary. Checkpoints and artifacts are evidence for that assigned mission.

## Definition concepts

Definitions are reusable:

- **Role:** specialist lens and behavior contract.
- **Policy:** authority, budgets, capabilities, and guardrails.
- **Workflow:** node tree plus evidence path.
- **Node:** one mission inside a workflow.
- **Criteria:** hard requirements that can block closure.
- **Consumes:** evidence a node must read.
- **Produces:** artifacts a node must publish.

Role says who the node is good at being. Policy says what the node may do. Workflow says how evidence moves.

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

Generated task-root files such as manifest, assignment, checkpoint, and artifacts are projections over controller-owned runtime records.

## Node kinds

Node kind comes from workflow structure:

- `root`: owns whole-task purpose and final closure.
- `parent`: owns routing and release for a subtree.
- `worker`: performs one bounded assignment.

Review, research, implementation, verification, planning, and release are modes of work. They are not separate node kinds.

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

A child returning green is evidence, not proof by itself. Parent and root nodes should inspect current evidence before release.

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
