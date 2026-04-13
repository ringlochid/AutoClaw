# Flow 05 — MVP Builder Workflow Pack

## Purpose

Show a concrete advanced workflow-pack example for idea-to-demo / MVP shipping.

## High-level phases

1. discovery
2. architecture
3. build
4. validation
5. launch / report

## Example shape

```text
root orchestrator
-> discovery subtree
-> architecture subtree
-> build subtree
-> validation subtree
-> launch/report subtree
```

## Main rule

This pack should be staged and gated.
It should not explode every loop fully in parallel from minute one.

## Why this matters

This is a strong fit for AutoClaw because:
- it is too adaptive for a plain static DAG
- it has many natural checkpoints and replan points
- supervision and staged expansion help prevent thrash
