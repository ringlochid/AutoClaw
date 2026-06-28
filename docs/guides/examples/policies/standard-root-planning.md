# Standard root planning policy example

Status: Reference

Use this policy when the root node owns final closure and may stage a limited number of child assignments.

This example teaches:

- root planning policy belongs on the root node
- `child_assignment_limit` constrains how much delegated work the root can open
- root closure still depends on surfaced evidence, criteria, and explicit release preconditions, not on provider success alone

```yaml
kind: policy
id: standard-root-planning
title: Standard Root Planning
description: Default root planning and closure behavior.
applies_to:
  - root
budget_spec:
  child_assignment_limit: 3
instruction: |
  Root is purpose-first for the whole task and owns final closure.
  Read the manifest, root assignment, latest relevant checkpoints, surfaced refs,
  criteria, transient refs, and task-memory hints before release or blocked
  closure.
  Lead through focused child work rather than one-shot solo completion. Ask
  planners, architects, reviewers, verifiers, or failure analysts for interface
  maps, test scenes, docs navigation, or evidence when those judgments are weak.
  Challenge weak evidence, request review or verification when criteria are too
  broad, and replan when the current workflow shape prevents clean progress.
  Commit release_green only when current whole-flow evidence is sufficient.
  Commit release_blocked only when whole-flow terminal blocked state is explicit
  and current.
```
