# Design workflows and instructions

Use this guide before writing role, policy, workflow, or task-compose YAML.

An AutoClaw workflow is not a role list. It is a purpose-specific evidence path: what the run is trying to prove, how evidence should move, and what makes green, retry, blocked, replan, or release honest.

## Recommended design flow

**Start small, prove the workflow, then scale it.**

1. Define the job in one sentence.
2. Choose the smallest workflow shape that can prove the job is done.
3. List required tools and verify they work in the selected harness.
4. Write one root, one worker, and one reviewer when possible.
5. Run a pilot task and inspect manifest, assignment, checkpoint, artifacts, and trace.
6. Only then expand the workflow or reuse it as a subtree.

## Start with the job

Write one sentence that defines the job:

- "Investigate a reported defect, fix it, and prove the regression is covered."
- "Research campaign positioning and produce an approval-ready brief."
- "Reconcile invoices against source records and flag mismatches for review."
- "Build a thin MVP slice that proves the target user's core job."

Then answer:

- what user or operator purpose does this serve?
- what evidence must exist before closure?
- what should be explicitly out of scope?
- what risk would make green dishonest?
- what decisions need human judgment?
- what work should happen only if evidence requires it?

If the purpose changes, write a different workflow. Similar-looking work can need different evidence.

## Choose a workflow shape

Use the lowest-complexity shape that can still prove the work is done.

| Shape | Use when | Avoid when |
| --- | --- | --- |
| Single worker | one bounded output and one proof loop are enough | the work needs independent review, routing, or human judgment |
| Root + worker + reviewer | one implementer/researcher should be checked before closure | review has no hard criteria |
| Fixed sequence | each step depends on the previous artifact | the route may change after evidence appears |
| Parent orchestration | a parent must inspect evidence and choose the next child | the sequence is known and small |
| Parallel specialists | independent perspectives improve confidence | outputs must be synchronized constantly |
| Review/fix loop | clear criteria allow useful critique and correction | feedback is vague preference |
| Human checkpoint | direction, approval, input, or review needs a human | current evidence is enough for the node to continue |
| Command-run worker | long/log-heavy/cancelable command work matters | ordinary commands finish quickly inline |
| Delivery batch parent | many similar scopes should run one at a time | every scope needs a bespoke workflow |

Split by evidence handoff and authority boundary, not by job title.

## Preflight tools before launch

A workflow is only as good as the tools available to the assigned nodes. List required tools before writing YAML.

Common tool families:

- file read, patch, and write tools
- shell or CLI tools
- browser automation tools
- visual screenshot or image tools
- PDF or document tools
- external service tools
- package manager or build tools
- provider skills or local reusable instructions

Check:

- the selected harness exposes the required tools
- sandbox policy allows the needed file and command access
- browser tools can reach local pages when the workflow needs localhost UI review
- credentials or external services are intentionally available when needed
- long commands have a command-run-enabled worker when inline execution is the wrong surface
- unsupported tools have a fallback path or the workflow blocks honestly

Do not assume a role instruction can compensate for an unavailable tool. If a browser, PDF, visual, CLI, or service tool is missing, the workflow should either use a different assignment, ask for human input when allowed, or block with the exact gap.

## Use layered contracts

Use each authored object for one kind of truth.

| Object | Owns | Should not own |
| --- | --- | --- |
| Role | reusable specialist lens and mode posture | one task's scope, paths, secrets, or launch detail |
| Policy | authority, budgets, capabilities, retry and closure guardrails | role identity or node tree |
| Workflow | node tree, evidence path, criteria, node missions, stable artifacts | hidden runtime state or live registry truth |
| Task-compose | one concrete task launch, selected workflow, optional roots, task instruction | reusable doctrine |

The simple memory model:

```text
Role = lens
Policy = rules
Node = mission
Criteria = done gate
Produces = leaves behind
Consumes = must read
Workflow = evidence path
Task-compose = this launch
```

For detailed wording rules, use [write layered instructions](write-layered-instructions.md).

## Merge work when one agent can own the evidence

Do not split tasks just because you can name more roles.

Usually merge when:

- one worker can read docs, patch code, and run focused tests
- one reviewer can inspect implementation, root cause, and regression risk
- one researcher can gather sources and synthesize findings in a bounded domain
- one verifier can run tests and report evidence without changing code

Usually split when:

- implementation and review must be independent
- long command work needs controller-managed logs and cancellation
- human judgment is a real gate
- a parent must route repeated scopes or ambiguous evidence
- specialist tools or permissions differ

Over-agenting creates more handoff surface without improving proof.

## Control repeated scope with a parent

For work like "implement 10 frontend pages from design", do not create 10 separate workers or subtrees by default.

Use one parent that assigns one page or slice at a time to the same worker or subtree pattern. The parent should inspect evidence after each slice before assigning the next one.

Parent/root instructions should say:

- how large one child assignment should be
- what evidence must exist before assigning the next child
- what must not be parallelized
- when to ask for direction
- when to stop and replan
- how to report skipped or deferred scope

Good parent instruction:

```yaml
instruction: >-
  Assign one frontend page at a time. Each child assignment must name the page, design reference, expected states, required screenshots, and validation commands. Inspect the child's checkpoint, artifacts, desktop screenshot, mobile screenshot, and test output before assigning the next page. Do not open parallel page work unless the pages have no shared components or fixture conflicts.
```

Bad parent instruction:

```yaml
instruction: >-
  Implement all pages and make sure they look good.
```

## Pilot before scaling

Start with one root, one worker, and one reviewer.

Pilot goals:

- the worker receives enough context
- criteria are concrete enough to block weak output
- `consumes` and `produces` create useful handoffs
- checkpoints contain real progress and risk
- artifacts are published where expected
- the reviewer can decide from evidence without rereading the whole transcript
- operator readbacks and task-root files explain the run

Only embed the pattern in a larger workflow after the pilot is understandable.

## Design fixed and dynamic workflows

Use a fixed workflow when the path is known.

Good fixed-workflow fits:

- one bounded implementation
- bug fix with reproduce, fix, verify, review
- release checklist
- document generation with clear review
- predictable command sequence

Fixed workflows should use `consumes`, `produces`, and `criteria` heavily because the evidence chain is known.

```text
triage_report -> fix_plan -> patch -> verification_report -> review_report
```

Use a dynamic workflow when the route is not knowable up front.

Good dynamic-workflow fits:

- large feature touching unknown areas
- incident response
- ambiguous user intent
- MVP build where value or scope may change
- product or marketing strategy
- research where sources may redirect the work
- multi-stage delivery with optional failure analysis or replan

Dynamic workflows should use `consumes`, `produces`, and `criteria` as stable anchors and phase gates, not as a pretend full future chain.

Dynamic does not mean unbounded. It means the parent/root owns routing while the workflow still defines purpose, authority, evidence gates, and closure.

## Design the evidence path

Before writing YAML, identify the durable evidence that later nodes or humans must inspect.

Use `criteria` when:

- pass/fail matters
- release could be disputed
- a reviewer needs hard grounds to reject
- a parent/root must know when to retry, replan, block, or release

Use `produces` when:

- another node needs a named artifact
- a human will review an output
- closure depends on a durable report, patch, plan, or bundle
- hidden transcript memory would be too fragile

Use `consumes` when:

- a node must depend on a specific prior artifact or criterion
- review must inspect the exact patch or report
- release must use only surfaced evidence

For fixed workflows, make the evidence pipeline explicit. For dynamic workflows, keep the required artifacts broad and stable.

## Design roles and skills

Write roles as durable specialists. Good roles:

- name one capability profile
- keep `allowed_node_kinds` narrow
- say what evidence the role reads first
- say what output the parent/root can expect
- say what the role must not do
- surface uncertainty instead of hiding it

Add provider skills when the harness supports them and the task needs specialized instructions. Examples: security review, PDF reading, browser triage, frontend visual verification, release safety, or database query review.

Skills are not workflow truth. They enrich the agent loop; the workflow still owns criteria, assignment boundaries, and required artifacts.

## Design policies

Policies are authority guardrails, not alternate roles.

Use policies for:

- node-kind compatibility through `applies_to`
- retry or child-assignment limits
- human request capability
- command-run capability
- evidence and checkpoint expectations
- release, blocked, or replan guardrails
- concrete prohibitions such as "do not publish externally"

Human requests and command runs are separate capabilities. Use human requests for human judgment. Use command runs only for controller-managed long command work.

Budget fields are node-kind-specific:

- `retry_limit` only on worker policies
- `child_assignment_limit` only on root or parent policies
- omitted `budget_spec` means no controller budget counter for that family

Start from the standard policy family and write a custom policy only when reusable authority changes.

## Validate the workflow after launch

During or after a run, inspect:

- real tool usage in the provider or harness surface, such as OpenClaw console events
- `_runtime/workflow-manifest.md`
- `_runtime/attempts/<attempt_id>/assignment.md`
- `_runtime/attempts/<attempt_id>/latest-checkpoint.md`
- `outputs/artifacts/`
- operator snapshot and trace
- human request or command-run readbacks when the task is waiting

Ask:

- did each node do the work its assignment asked for?
- did tool usage match the workflow's assumptions?
- did produced artifacts match the declared slots?
- did checkpoints explain progress, criteria status, and residual risk?
- did the boundary match the checkpoint?
- did parent/root release only after inspecting current evidence?

For the operational walkthrough, use [inspect and control a task](inspect-and-control-a-task.md).

## Common workflow families

| Family | Purpose | Typical evidence |
| --- | --- | --- |
| Idea discovery | compare directions before committing | option brief, evidence notes, tradeoffs, recommendation |
| Planning only | create an execution plan without building | scope brief, dependency map, risk log, plan review |
| MVP build | prove core user value with a thin slice | MVP scope, patch, demo verification, product review |
| Core-only build | build a foundation layer without launch polish | contract plan, patch, verification, architecture review |
| Feature implementation | add one feature to an existing product | context report, integration plan, patch, verification, review |
| Bug fix | reproduce, fix, verify, review, and release one defect | triage, fix plan, patch, regression proof, review |
| Marketing campaign | plan campaign work without external publishing | audience research, campaign brief, approval risks |
| Project management | coordinate delivery without implementation | objectives, task slices, owners, dependency map, status |
| Incident response | contain, triage, recover, and learn | timeline, impact, mitigation, fix evidence, lesson |

## Before saving

Check the definition set:

- the root knows what final closure means
- every parent has a real routing job
- every worker has one bounded mode
- review and verification nodes have criteria to judge
- implementation nodes know what not to touch
- planning nodes explicitly avoid implementation
- human request policies state when and why to ask
- command-run policies isolate long command work
- dynamic workflows use broad phase gates instead of speculative artifacts
- produced artifacts let later nodes work without hidden transcript memory

## Related pages

- [Write layered instructions](write-layered-instructions.md)
- [Write a role](write-a-role.md)
- [Write a policy](write-a-policy.md)
- [Write a workflow](write-a-workflow.md)
- [Use guide examples](examples/README.md)
- [Inspect and control a task](inspect-and-control-a-task.md)
