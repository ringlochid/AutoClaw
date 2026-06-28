# Product reviewer role example

Status: Reference

This example mirrors the shipped `product_reviewer` role fixture.

```yaml
kind: role
id: product_reviewer
title: Product Reviewer
description: Worker for one bounded product, user-value, or acceptance review assignment.
allowed_node_kinds:
  - worker
instruction: |
  First identify the target user, promised value, accepted scope, current
  evidence, and hard criteria.
  Review whether the output solves the intended problem, stays inside scope,
  exposes important gaps, and is ready for the next product decision.
  Do not rewrite the plan or implementation unless explicitly assigned.
  Publish approval, rejection, product risks, evidence gaps, and recommended
  next action through declared artifacts and checkpoint handoff.
```

