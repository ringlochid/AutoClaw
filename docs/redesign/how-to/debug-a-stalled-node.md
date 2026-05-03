# Debug a stalled node

Status: Target

This page describes the intended operator/debug workflow for a stalled node under the redesign.

## Procedure

1. Classify the problem first: dependency wait, degraded continuity, blocked execution, or stalled execution.
2. Read controller-owned runtime truth first through the current manifest, current assignment, latest checkpoint, criteria, and any surfaced durable artifacts relevant to the assignment.
3. Use `_runtime/dispatch/<dispatch_id>/delivery-state.json`, `continuity-state.json`, `watchdog-state.json`, and `provider-events.ndjson` as operator/debug projections only. If they disagree with controller/DB state, controller/DB state wins.
4. If the issue is transport continuity, use provider recovery first.
5. If the assignment is still current but execution stalled, allow at most one bounded `redispatch_same_attempt` only when current controller truth still proves it legal.
6. If the current attempt lineage is no longer trustworthy, prefer `create_new_attempt` only when the controller can prove that path is legal.
7. If the assignment or subtree structure is now wrong, return to parent/root review and structural replan instead of forcing repeated recovery.

## Use these owner pages

- [Runtime monitoring and watchdog automation](../architecture/runtime-monitoring-and-watchdog-automation.md)
- [Watchdog and provider recovery](../architecture/watchdog-and-provider-recovery.md)
- [Worker context contract](../architecture/worker-context-contract.md)
