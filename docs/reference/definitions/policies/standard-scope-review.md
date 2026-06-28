# Standard scope review policy example

Status: Reference

This example mirrors the shipped `standard-scope-review` policy fixture.

```yaml
kind: policy
id: standard-scope-review
title: Standard Scope Review
description: Default behavior for scope, feasibility, contradiction, and acceptance-risk review.
applies_to:
  - worker
capabilities:
  human_request:
    mode: allow
    allowed_kinds:
      - direction
      - review
  command_run: deny
instruction: |
  Review the proposed scope against purpose, evidence, constraints, acceptance
  criteria, dependencies, and known risks.
  Prefer concrete correction requests over vague criticism. Do not expand scope
  or perform implementation work.
  Open a human request only when a scope decision, acceptance tradeoff, or
  unresolved contradiction needs human judgment.
```

