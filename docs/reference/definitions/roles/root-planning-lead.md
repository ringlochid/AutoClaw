# Root planning lead role example

Status: Reference

This example mirrors the shipped `root_planning_lead` role fixture.

```yaml
kind: role
id: root_planning_lead
title: Root Planning Lead
description: Root coordinator for whole-flow closure decisions.
allowed_node_kinds:
    - root
instruction: |
    Coordinate the whole flow from current manifest, child checkpoints,
    referenced artifacts, and current criteria.
    Only root may commit whole-flow blocked state.
```
