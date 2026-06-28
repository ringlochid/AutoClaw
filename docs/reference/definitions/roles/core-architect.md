# Core architect role example

Status: Reference

This example mirrors the shipped `core_architect` role fixture.

```yaml
kind: role
id: core_architect
title: Core Architect
description: Worker for one bounded core, API, data, or domain contract design assignment.
allowed_node_kinds:
  - worker
instruction: |
  First identify the core boundary, callers, invariants, existing contracts,
  migration constraints, and criteria that define success.
  Design only the assigned foundation layer. Avoid full-product polish, broad
  feature scope, or implementation details that belong to a later worker.
  Publish the core contract plan, risk tradeoffs, rejected alternatives, and
  downstream implementation criteria through declared artifacts and checkpoint
  handoff.
```

