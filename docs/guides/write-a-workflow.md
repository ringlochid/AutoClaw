# Write a workflow

Status: Reference

Write a workflow when you want AutoClaw to run your own automation. A workflow is a purpose-specific evidence path, not a menu choice from the shipped examples.

Start with the work your automation must prove. Then choose roles, policies, node structure, artifacts, and criteria that make closure honest.

## Start from the purpose

Write one sentence that defines success:

- "Classify inbound support reports and produce a reviewed escalation package."
- "Investigate a regression, fix it, and prove the regression behavior is covered."
- "Research campaign positioning and produce an approval-ready campaign brief."
- "Reconcile invoices against source records and flag mismatches for human review."

If the purpose changes, write a different workflow. Similar-looking work can need different evidence.

## Define the evidence path

Before writing YAML, answer:

- what artifacts must exist before root closure?
- which criteria can block closure?
- which nodes need consumed artifacts from earlier nodes?
- where does review or verification happen?
- when should a parent retry, replan, release, or block?
- where is human judgment required?

Do this before choosing node count. A smaller workflow is better only when it can still prove the work is done.

## Choose the structure

Use the simplest structure that fits the evidence path:

| Shape | Use when |
| --- | --- |
| Single worker | one bounded output and one proof loop are enough |
| Sequential chain | each step depends on the previous artifact |
| Parent orchestration | a parent must inspect evidence and choose the next child |
| Parallel specialists | independent perspectives improve confidence |
| Review loop | clear criteria allow useful critique and correction |
| Human checkpoint | direction, approval, input, or review needs human judgment |

## Author nodes around contracts

Each node should have:

- `description`: why the node exists
- `instruction`: node-local guidance that does not replace role or policy
- `consumes`: durable artifact or criteria inputs it needs
- `produces`: durable artifacts it must publish
- `criteria`: hard closure or guardrail requirements

Use `criteria` only for requirements that can block closure. Put softer guidance in role, policy, or node instruction.

## Keep shipped workflows as examples

The shipped workflows show valid patterns, but they are not the product boundary. Use them to learn the shape, then write workflows for your own automation.

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
- human request points are intentional
- command-run points are isolated to nodes that need them
- the workflow says what is out of scope

## Related pages

- [Write a role](write-a-role.md)
- [Write a policy](write-a-policy.md)
- [Design workflows and instructions](design-workflows-and-instructions.md)
- [Workflow reference examples](../reference/definitions/workflows/README.md)
