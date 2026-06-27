# Standard root planning policy example

Status: Reference

This example mirrors the shipped `standard-root-planning` policy fixture.

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
  Root owns final closure.
  Commit release_green only when current whole-flow evidence is sufficient.
  Commit release_blocked only when whole-flow terminal blocked state is
  explicit and current.
```
