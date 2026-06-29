# Standard failure analysis policy example

Status: Reference

This example mirrors the shipped `standard-failure-analysis` policy fixture.

```yaml
kind: policy
id: standard-failure-analysis
title: Standard Failure Analysis
description: Default behavior for failed, blocked, or repeated attempt analysis.
applies_to:
    - worker
instruction: >-
  Analyze why the previous attempt failed before proposing more work. Read the terminal
  checkpoint, current assignment, criteria, surfaced refs, and task-memory hints.
  Separate root cause, symptom, missing evidence, and prompt ambiguity. Also identify
  contract or docs drift, workflow-shape mismatch, and unresolved approval/risk
  decisions when they explain the failure. Use bounded research to test the likely cause
  against local facts and current best practice before recommending the next route.
  Publish a recommendation for retry, specialist assignment, structural replan, or
  blocked closure. Do not fix the implementation unless explicitly assigned.
```
