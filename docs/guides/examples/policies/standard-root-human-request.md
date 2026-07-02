# Standard root human-request policy example

Use this policy when the root may need a typed human wait before honest whole-task closure.

This example shows:

- human-request capability is separate from command-run capability
- root human requests are for final direction, approval, missing input, or review
- root should try to settle the question from task evidence and child work first

```yaml
kind: policy
id: standard-root-human-request
title: Standard Root Human Request
description: Guardrails for root orchestration that may wait for human judgment.
applies_to:
    - root
budget_spec:
    child_assignment_limit: 15
capabilities:
    human_request:
        mode: allow
        allowed_kinds:
            - direction
            - approval
            - input
            - review
    command_run: deny
instruction: >-
  Open a human request only when final direction, approval, missing input, or review is material to honest closure, try to solve it in current subtree first, if the worker can't provide best practices plus sufficient evidence, then use human request.
```
