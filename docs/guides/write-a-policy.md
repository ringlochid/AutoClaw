# Write a policy

Status: Reference

Write a policy when you need reusable guardrails, budgets, or capabilities for a node. A policy constrains how work proceeds; it should not replace the role.

Use policies to make authority explicit. Human requests and command runs are separate capabilities, so grant only the one the node actually needs.

## Decide what the policy controls

Before writing YAML, answer:

- can this node ask a human for direction, approval, input, or review?
- can this node start controller-managed long command runs?
- how should retry or child assignment be bounded?
- what evidence must appear before closure?
- what actions should be explicitly out of scope?
- what ambiguity should block, route, or trigger a human request?

Keep identity out of the policy. "Reviewer", "engineer", or "researcher" behavior belongs in a role. The policy should say what is allowed and how tightly the node must behave.

## Grant capabilities separately

Human requests are for human judgment. Command runs are for long-running command work. A node can have one, both, or neither.

```yaml
kind: policy
id: scope-review-policy
title: Scope Review Policy
description: Guardrails for scoped review without implementation.
capabilities:
    human_request:
        mode: allow
        allowed_kinds:
            - direction
            - review
    command_run: deny
instruction: >-
    Review only the current assignment, criteria, surfaced refs, and produced artifacts.
    Ask for direction only when the next judgment cannot be made from current evidence. Do
    not implement, run long commands, publish externally, or expand the accepted scope.
```

## Use human requests for judgment

Allow human requests only where a human decision is part of the workflow.

Use:

- `direction` when the next route depends on human judgment
- `approval` before an irreversible or externally visible action
- `input` when required facts cannot be discovered from current evidence
- `review` when human review is part of closure

Do not use a human request for status updates, ordinary progress, or long command work.

## Use command runs for long commands

Grant command-run capability only when command work is expected to outlive a normal dispatch. Ordinary shell commands should finish inline and comfortably under about two minutes.

If a workflow frequently needs long commands, put them in a dedicated worker with a command-run-enabled policy. Do not grant command-run permission to every node just in case.

## Bound retries and children

Use retry and child-assignment budgets to keep the controller honest.

Good policy posture:

- a worker may retry once when the assignment shape is still correct
- a parent has a child assignment limit that fits the subtree
- repeated failure routes to failure analysis or replan
- blocked closure requires current evidence

Do not let retry become an infinite loop around the same bad assignment.

## Add shared ambiguity rules

Policies are the right place for shared uncertainty behavior.

Good policy wording:

```yaml
instruction: >-
    Classify ambiguity as missing input, conflicting criteria, unclear scope, contract or
    docs drift, insufficient evidence, workflow-shape mismatch, or approval/risk decision.
    Resolve it from current evidence when safe. If it is material, checkpoint the blocker
    or use an allowed human request.
```

Keep role-specific research detail in roles. Keep workflow-specific routing in workflow nodes.

## Good policy checklist

- capability grants are explicit and minimal
- human request kinds match real workflow gates
- command-run permission is not granted by default
- ordinary commands stay inline and under about two minutes
- retry or assignment posture is clear when relevant
- evidence and checkpoint expectations are stated
- forbidden actions are concrete
- the policy does not duplicate role identity
- material ambiguity has a route

## Related pages

- [Write layered instructions](write-layered-instructions.md)
- [Write a role](write-a-role.md)
- [Write a workflow](write-a-workflow.md)
- [Capability model](../concepts/capability-model.md)
- [Policy reference examples](../reference/definitions/policies/README.md)
