# Flow 04 — Approval and Watchdog

## Approval gate behavior

- node can emit `needs_approval`
- flow enters `waiting_approval`
- operator resolves via approval row
- controller resumes based on approval state

## Watchdog behavior

- re-check stalled nodes
- recover from missing child heartbeat
- support soft-stop for human intervention

## Safety note

No state transition without a checkpoint or explicit operator action.
