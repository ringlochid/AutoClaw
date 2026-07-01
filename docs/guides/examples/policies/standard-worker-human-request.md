# Standard worker human-request policy example

Use this policy when a worker may need a typed human wait for judgment, input, approval, or review.

This example teaches:

- human-request capability is separate from command-run capability
- `allowed_kinds` must be non-empty when human requests are allowed
- human requests are not status updates or a replacement for local evidence gathering

```yaml
kind: policy
id: standard-worker-human-request
title: Standard Worker Human Request
description: Guardrails for worker assignments that may need human direction, input, approval, or review.
applies_to:
    - worker
budget_spec:
    retry_limit: 1
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
  Open a human request only for material direction, approval, missing input, or review that cannot be settled from current task evidence.
```
