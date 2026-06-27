# Planner role example

Status: Reference

This example mirrors the shipped `planner` role fixture.

```yaml
kind: role
id: planner
title: Planner
description: Worker for one bounded planning assignment.
allowed_node_kinds:
    - worker
instruction: |
    Publish the current delivery plan for the owned assignment only.
    Keep plan updates specific to surfaced findings, current criteria, and the
    declared workflow outputs.
```
