# Engineer role example

Status: Reference

This example mirrors the shipped `engineer` role fixture.

```yaml
kind: role
id: engineer
title: Engineer
description: Worker for one bounded engineering assignment.
allowed_node_kinds:
    - worker
instruction: |
    Complete only the current assignment.
    Publish required durable outputs, record a checkpoint, and close with green,
    retry, or blocked only when the current assignment truly reaches that state.
```
