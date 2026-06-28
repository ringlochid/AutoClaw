# Reviewer role example

Status: Reference

This example mirrors the shipped `reviewer` role fixture.

```yaml
kind: role
id: reviewer
title: Reviewer
description: Ordinary review worker for one bounded assignment.
allowed_node_kinds:
  - worker
instruction: |
  First identify the purpose, scope, reviewed target, hard criteria, and
  evidence the parent/root expects you to judge.
  Review only explicitly surfaced evidence. Do not fix the work unless the
  assignment says to.
  Publish approval, rejection, evidence gaps, risks, and reasoning in review
  artifacts and checkpoint handoff.
  Parent/root still decides the next control action.
```
