# User and operator journeys

Status: Reference

This page summarizes the main product journeys at a narrative level.

## Launch work

1. Choose or author a workflow.
2. Start a concrete task from a lean task-compose surface.
3. Let the controller compile, launch, and supervise runtime work.

## Supervise work

1. Inspect current flow health, parent verification state, and operator-visible summaries.
2. Pause, continue, retry, or cancel through the operator surface.
3. Use watchdog and audit surfaces when work stalls or continuity degrades.

## Close work

1. Gather artifacts, reports, findings, and evidence.
2. Let each parent verify its own subtree and release `green`, `blocked`, or replan escalation.
3. Let root decide final closure readiness and dispatch the final sync leaf only when ready.
