# Design workflows and instructions

Status: Reference

Use this guide before writing role, policy, workflow, or task-compose YAML.

An AutoClaw workflow is not a role list. It is a purpose-specific evidence path: what the run is trying to prove, how evidence should move, and what makes green, retry, blocked, or release honest.

The shipped definitions are examples, not a menu. Use them to learn valid shapes, then write definitions for the automation you actually want AutoClaw to run.

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

## Use layered contracts

Use each authored object for one kind of truth.

| Object       | Owns                                                                 | Should not own                                     |
| ------------ | -------------------------------------------------------------------- | -------------------------------------------------- |
| Role         | reusable specialist lens and mode posture                            | one task's scope, paths, secrets, or launch detail |
| Policy       | authority, budgets, capabilities, retry and closure guardrails       | role identity or node tree                         |
| Workflow     | node tree, evidence path, criteria, node missions, stable artifacts  | hidden runtime state or live registry truth        |
| Task-compose | one concrete task launch, selected workflow, roots, task instruction | reusable doctrine                                  |

The simple memory model is:

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

## Choose the smallest useful shape

Use the lowest-complexity shape that can still prove the work is done.

| Shape                | Use when                                                 | Avoid when                                                |
| -------------------- | -------------------------------------------------------- | --------------------------------------------------------- |
| Single worker        | one bounded output and one proof loop are enough         | the work needs review, dependencies, or separate evidence |
| Fixed sequence       | each step depends on the previous artifact               | the route may change after evidence appears               |
| Purpose routing      | similar inputs need different paths                      | the distinction is only cosmetic                          |
| Parent orchestration | a parent must inspect evidence and choose the next child | the sequence is known and small                           |
| Parallel specialists | independent perspectives improve confidence              | outputs must be synchronized at every step                |
| Review loop          | clear criteria allow useful critique and correction      | there is no hard standard to review against               |
| Human checkpoint     | judgment, approval, input, or review needs a human       | the node can proceed from current evidence                |

Complexity is useful only when it improves evidence quality, recovery, or safety. A giant workflow that tries to handle every purpose is usually worse than several smaller workflows with clear contracts.

## Fixed and dynamic workflows

Use a fixed workflow when the path is known.

Good fixed-workflow fits:

- one bounded implementation
- bug fix with reproduce, fix, verify, review
- release checklist
- document generation with clear review
- support classification
- predictable command sequence

Fixed workflows should use `consumes`, `produces`, and `criteria` heavily, because the evidence chain is known.

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

Dynamic workflows should use `consumes`, `produces`, and `criteria` sparsely. Use them as stable anchors and phase gates, not as a pretend full future chain.

Good dynamic anchors:

- root criteria that define final success
- parent criteria that define phase readiness
- broad artifacts such as `research_brief`, `risk_log`, `current_plan`, `evidence_bundle`, or `closure_report`
- consumes that point to known upstream anchors only

Bad dynamic design:

```text
predeclare every possible future child artifact
```

Better dynamic design:

```text
root preserves purpose
setup parent proves readiness
implementation parent assigns children dynamically
review and fixer nodes consume surfaced current evidence
root closes from current evidence bundle and root criteria
```

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

## Design roles

Write roles as durable specialists.

Good roles:

- name one capability profile, such as `scope_reviewer` or `invoice_reconciliation_reviewer`
- keep `allowed_node_kinds` narrow
- say what evidence the role reads first
- say what output the parent/root can expect
- say what the role must not do
- surface uncertainty instead of hiding it

Avoid generic roles such as `assistant`, `helper`, or `worker`. Generic names hide responsibility and make workflow review harder.

## Design policies

Policies are behavioral guardrails, not alternate roles.

Use policy instruction for:

- retry or child-assignment limits
- human request capability
- command-run capability
- evidence and checkpoint expectations
- release, blocked, or replan guardrails
- concrete prohibitions such as "do not publish externally"

Human requests and command runs are separate capabilities. A node can have one, both, or neither.

Use human requests for human judgment: direction, approval, missing input, or review. Use command runs only for controller-managed long-running command work. Ordinary commands should stay inline and comfortably under about two minutes.

## Design parent and root nodes

Use a parent node when local orchestration has a reason to exist:

- the next child depends on current evidence
- child outputs need inspection before release
- the subtree may need retry, failure analysis, or replan
- the parent must coordinate several bounded specialists

Use a root node to preserve the whole task purpose and final closure standard. Root should not become a one-shot solo worker. It should route, inspect, challenge weak evidence, ask for human judgment when allowed, replan when the shape is wrong, and close only from current evidence.

## Design for gaps

Every non-trivial workflow needs a gap posture.

Workers should:

- read current task truth first
- resolve low-risk ambiguity from current evidence when safe
- record assumptions and residual risk
- report material ambiguity instead of widening scope

Parents and roots should:

- classify the gap
- route to research, planning, review, verification, failure analysis, human request, replan, or blocked closure
- treat child green as evidence, not automatic closure
- treat child blocked as routing input, not automatic whole-flow failure

For detailed rules, use [handle ambiguity and incidents](handle-ambiguity-and-incidents.md).

## Common workflow families

| Family                 | Purpose                                                | Typical evidence                                              |
| ---------------------- | ------------------------------------------------------ | ------------------------------------------------------------- |
| Idea discovery         | compare directions before committing                   | option brief, evidence notes, tradeoffs, recommendation       |
| Planning only          | create an execution plan without building              | scope brief, work breakdown, risk log, plan review            |
| MVP build              | prove core user value with a thin slice                | MVP scope, patch, demo verification, product review           |
| Core-only build        | build a foundation layer without launch polish         | contract plan, patch, verification, architecture review       |
| Feature implementation | add one feature to an existing product                 | context report, integration plan, patch, verification, review |
| Bug fix                | reproduce, fix, verify, review, and release one defect | triage, fix plan, patch, regression proof, review             |
| Marketing campaign     | plan campaign work without external publishing         | audience research, campaign brief, approval risks             |
| Project management     | coordinate delivery without implementation             | objectives, packages, owners, dependency map, status          |
| Incident response      | contain, triage, recover, and learn                    | timeline, impact, mitigation, fix evidence, lesson            |

The same roles can appear in several families, but the workflow should differ when the purpose and evidence differ.

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
- [Handle ambiguity and incidents](handle-ambiguity-and-incidents.md)
