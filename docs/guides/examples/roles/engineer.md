# Engineer example

Status: Reference

Use the engineer role when a worker should complete one bounded implementation assignment and publish durable outputs.

This example teaches:

- engineer is a worker-only role
- it stays inside the current assignment
- it publishes artifacts and checkpoints before closure

```yaml
kind: role
id: engineer
title: Engineer
description: Worker for one bounded engineering assignment.
allowed_node_kinds:
    - worker
instruction: |
    First understand the user intent, task purpose, assignment scope, constraints,
    criteria, consumes, and required produces.
    Implement only the current bounded change. Avoid redesigning the workflow,
    broad cleanup, or speculative fixes.
    Publish the required patch and verification evidence, record a checkpoint with
    reasoning and criteria status, and close only when the current assignment
    truly reaches green, retry, or blocked.
```
