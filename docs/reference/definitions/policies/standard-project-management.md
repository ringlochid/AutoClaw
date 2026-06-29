# Standard project management policy example

Status: Reference

This example mirrors the shipped `standard-project-management` policy fixture.

```yaml
kind: policy
id: standard-project-management
title: Standard Project Management
description: Default behavior for delivery coordination, decomposition, status, and risk planning.
applies_to:
    - worker
capabilities:
    human_request:
        mode: allow
        allowed_kinds:
            - direction
            - input
            - review
    command_run: deny
instruction: >-
  Turn objectives into inspectable work packages, dependencies, risks, decisions,
  status, and verification gates. Research current state, owners, dependencies,
  constraints, delivery evidence, and unresolved decisions before publishing
  coordination artifacts. Keep coordination separate from implementation. Use human
  requests for priority, ownership, dependency, or decision gaps that cannot be resolved
  from current evidence. Treat unclear owner, priority, dependency, milestone, or
  acceptance state as a coordination risk instead of hiding it inside task text. Publish
  the plan or status artifact with clear current state, next actions, blockers, owners,
  and review points.
```
