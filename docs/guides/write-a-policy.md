# Write a policy

Status: Reference

Write a policy when you need reusable guardrails, budgets, and capabilities for a node. A policy should constrain how work proceeds; it should not replace the role.

Use policies to make authority explicit. Human requests and command runs are separate capabilities, so grant only the one the node actually needs.

## Decide what the policy controls

Before writing YAML, answer:

- can this node ask a human for direction, approval, input, or review?
- can this node start controller-managed long command runs?
- how should retry or child assignment be bounded?
- what evidence must appear before closure?
- what actions should be explicitly out of scope?

Keep identity out of the policy. "Reviewer", "engineer", or "researcher" behavior belongs in a role. The policy should say what is allowed and how tightly the node must behave.

## Write capability rules separately

Human requests are for human judgment. Command runs are for long-running command work. A node can have one, both, or neither.

```yaml
kind: policy
id: scope-review-policy
description: Guardrails for scoped review without implementation or command execution.
capabilities:
  human_request:
    mode: allow
    allowed_kinds:
      - direction
      - review
  command_run: deny
instruction: >
  Review only the current assignment, criteria, surfaced refs, and produced
  artifacts. Ask for direction only when the next judgment cannot be made from
  current evidence. Do not implement, run long commands, publish externally, or
  expand the accepted scope.
```

## Use command-run capability carefully

Grant command-run capability only when command work is expected to outlive a normal dispatch. Ordinary commands should finish inline and comfortably under about two minutes.

If a workflow frequently needs long commands, decide whether the command belongs in a dedicated worker with a command-run-enabled policy.

## Good policy checklist

- capability grants are explicit and minimal
- human request kinds match real workflow gates
- command-run permission is not granted by default
- retry or assignment posture is clear when relevant
- evidence and checkpoint expectations are stated
- forbidden actions are concrete
- the policy does not duplicate role identity

## Related pages

- [Write a role](write-a-role.md)
- [Write a workflow](write-a-workflow.md)
- [Capability model](../concepts/capability-model.md)
- [Policy reference examples](../reference/definitions/policies/README.md)
