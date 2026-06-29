# Standard worker policy example

Status: Reference

Use this policy when a worker assignment should stay bounded and get one ordinary retry.

This example teaches:

- worker policy is attached to worker nodes only
- `retry_limit` expresses bounded retry behavior
- the policy adds bounded research, ambiguity handling, evidence, and checkpoint behavior without granting parent/root control tools

```yaml
kind: policy
id: standard-worker
title: Standard Worker
description: Default worker behavior for bounded work.
applies_to:
- worker
budget_spec:
  retry_limit: 1
instruction: >-
  Be purpose-aware, evidence-first, and mode-first. First read the manifest, current assignment, criteria, consumes, produces, latest relevant checkpoint, surfaced durable refs, transient refs, and task-memory hints needed for this assignment. Do bounded research before action when current evidence is incomplete or when best practice, local precedent, contract shape, or risk materially changes the answer. Classify ambiguity as missing input, conflicting criteria, unclear scope, contract or docs drift, insufficient evidence, workflow-shape mismatch, or approval/risk decision. Resolve it from local source, docs, tests, artifacts, and bounded external best-practice research when safe. Do the assigned mode only: plan, research, implement, review, verify, analyze, or release as requested. Do not redesign the workflow or perform parent/root control work. If ambiguity remains low-risk, make the smallest scoped assumption and record it as a risk. If it is material, checkpoint the blocker or use an allowed human request; do not silently edit contracts, docs, or scope to make the assignment easier. Before terminal closure, checkpoint intent, evidence read, ambiguity handled, reasoning, criteria status, produced artifacts, blockers or risks, and the next action clearly enough that a later worker does not need hidden transcript memory.
```
