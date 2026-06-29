# Write a workflow

Status: Reference

Write a workflow when you want AutoClaw to run your own automation. A workflow is a purpose-specific evidence path, not a menu choice from the shipped examples.

Start with the work your automation must prove. Then choose roles, policies, node structure, artifacts, and criteria that make closure honest.

## Start from the purpose

Write one sentence that defines success:

- "Classify inbound support reports and produce a reviewed escalation package."
- "Investigate a regression, fix it, and prove regression behavior is covered."
- "Research campaign positioning and produce an approval-ready campaign brief."
- "Reconcile invoices against source records and flag mismatches for review."

If the purpose changes, write a different workflow. Similar-looking work can need different evidence.

## Decide fixed or dynamic

Use a fixed workflow when the path is known.

Fixed workflows should use explicit `consumes`, `produces`, and `criteria` because the evidence pipeline is known.

```text
triage_report -> fix_plan -> patch -> verification_report -> review_report
```

Use a dynamic workflow when the route is not knowable up front.

Dynamic workflows should use `consumes`, `produces`, and `criteria` as stable anchors and phase gates, not as a full predeclared future chain.

```text
root owns purpose
parent owns routing
children publish current evidence
review consumes surfaced current evidence
root closes from evidence bundle and root criteria
```

Dynamic does not mean loose. It means the parent/root chooses the next child from evidence while the workflow still defines purpose, authority, and closure.

## Define the evidence path

Before writing YAML, answer:

- what evidence must exist before root closure?
- which criteria can block closure?
- which artifacts will later nodes consume?
- where does review or verification happen?
- when should a parent retry, replan, release, or block?
- where is human judgment required?
- where might long command work need command-run capability?

Do this before choosing node count. A smaller workflow is better only when it can still prove the work is done.

Choose policies by authority, not by domain. Use `standard-worker` for ordinary bounded worker steps, `standard-worker-human-request` when that worker may need a typed human wait, and `standard-worker-command-run` when that worker may need controller-managed long commands. Use root and parent policies for orchestration nodes.

## Choose the structure

Use the simplest structure that fits the evidence path:

| Shape                | Use when                                                   |
| -------------------- | ---------------------------------------------------------- |
| Single worker        | one bounded output and one proof loop are enough           |
| Fixed sequence       | each step depends on the previous artifact                 |
| Parent orchestration | a parent must inspect evidence and choose the next child   |
| Parallel specialists | independent perspectives improve confidence                |
| Review loop          | clear criteria allow useful critique and correction        |
| Human in loop        | direction, approval, input, or review needs human judgment |

Every parent should have a real routing job. Every worker should have one bounded mode.

Policy budget should match the shape:

- root and parent nodes use child-assignment budget
- worker nodes use retry budget
- command-run policy belongs on the worker that will own the long command
- human-request policy belongs only where human judgment is a real gate

## Author nodes around contracts

Each node should have:

- `description`: why the node exists
- `instruction`: node-local guidance that does not replace role or policy
- `consumes`: specific artifact or criteria inputs it needs
- `produces`: durable artifacts it must publish
- `criteria`: hard closure or guardrail requirements

Use `criteria` only for requirements that can block closure. Put softer guidance, review rubrics, and behavior posture in role, policy, or node instruction.

## Use criteria carefully

Criteria should be hard enough to make a result fail.

Good criteria:

```yaml
criteria:
    - slot: defect_release_criteria
      description: Hard criteria for defect-fix release.
      criteria:
          - current patch addresses the reported defect
          - verification evidence covers the reproduced behavior
          - unresolved high-risk regression blocks release
```

Weak criteria:

```yaml
criteria:
    - slot: general_quality
      criteria:
          - do a good job
          - be careful
```

If a statement cannot block closure, put it in instruction instead.

## Use produces and consumes by workflow type

For fixed workflows, make handoffs explicit:

```yaml
produces:
    artifacts:
        - slot: triage_report
          file_hint: triage_report.md
          description: Reproduction, likely cause, scope, and uncertainty.
```

```yaml
consumes:
    artifacts:
        - slot: triage_report
```

For dynamic workflows, keep artifacts broad and stable:

- `research_brief`
- `risk_log`
- `current_plan`
- `evidence_bundle`
- `closure_report`

Avoid speculative slots for future branches the parent may never assign.

## Route ambiguity

Add explicit routing posture when a workflow may encounter gaps.

Good dynamic parent instruction:

```yaml
instruction: >-
  Inspect current evidence before assigning the next child. Route unclear scope to a
  scope reviewer, weak verification to a verifier, repeated failure to failure analysis,
  and workflow-shape mismatch to replan. Do not force a worker to widen scope to make
  progress.
```

Workers should surface ambiguity. Parents and roots should route it.

## Keep shipped workflows as examples

The shipped workflows show valid patterns, but they are not the product boundary. Use them to learn shape, then write workflows for your own automation.

Good automation workflows are domain-specific:

- support triage
- accounting reconciliation
- release readiness
- research synthesis
- security review
- product planning
- migration execution

## Good workflow checklist

- the root knows what final closure means
- every parent has a reason to exist
- every worker has one bounded mode
- artifacts let later nodes inspect evidence without transcript memory
- criteria are hard enough to block closure
- fixed workflows have explicit handoffs
- dynamic workflows use sparse stable anchors
- human request points are intentional
- command-run points are isolated to nodes that need them
- the workflow says what is out of scope

## Related pages

- [Design workflows and instructions](design-workflows-and-instructions.md)
- [Write layered instructions](write-layered-instructions.md)
- [Write a role](write-a-role.md)
- [Write a policy](write-a-policy.md)
- [Handle ambiguity and incidents](handle-ambiguity-and-incidents.md)
- [Workflow reference examples](../reference/definitions/workflows/README.md)
