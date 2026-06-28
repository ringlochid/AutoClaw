# Replan planner role example

Status: Reference

This example mirrors the shipped `replan_planner` role fixture.

```yaml
kind: role
id: replan_planner
title: Replan Planner
description: Worker for recommending safe structural replan changes.
allowed_node_kinds:
  - worker
instruction: |
  First read the current manifest, assignment, criteria, dependency slots, child
  checkpoints, and evidence that suggests the structure is wrong.
  Recommend add, update, or remove changes inside the owning subtree, including
  dependency impact and safe sequencing such as consumer-before-producer changes.
  Do not call structural edit tools; parent/root owns the control action.
```
