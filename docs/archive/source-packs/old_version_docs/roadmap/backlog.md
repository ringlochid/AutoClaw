# Roadmap Backlog

Status: deferred work only
Last verified: 2026-04-20

Only put genuine deferrals here.
If backend/runtime work is still active, it belongs in `next.md`, not here.

## Deferred items

### Performance and scaling

- [ ] Add denormalized provenance caches only if profiling proves they are needed
- [ ] Tune scheduler queries and add performance-specific indexes after real query shapes are measured
- [ ] Add storage compaction or retention policy for large context artifacts and logs

### Migration and maintenance tooling

- [ ] Add tooling to inspect or export historical `run` / `attempt` data after cutover
- [ ] Add one-off historical backfill/report scripts where they are still needed
- [ ] Add automation for removing dead compatibility shims and legacy routes after the backend surface settles further

### Deferred non-core product work

- [ ] Add richer operator diff views for revision and subtree comparison
- [ ] Add richer event streaming beyond the minimum typed runtime events needed for controller correctness
- [ ] Add polished lineage or audit reporting exports

## Rules

- [ ] Do not park active backend cleanup here just because it is hard
- [ ] Do not move UI/editor work into `next.md`; keep it deferred here or in a separate UI planning surface
