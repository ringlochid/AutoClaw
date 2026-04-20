# Roadmap Backlog

Last verified: 2026-04-20

Only put **deferred** work here.
If an item is required for the core runtime migration, it belongs in a phase file instead.

## Deferred until after core migration

### Performance / optimization

- denormalized provenance caches only if profiling proves they are needed
- scheduler tuning and performance-specific indexes after real query shapes are measured
- storage compaction/retention policy for large context artifacts and logs

### UX / productization

- richer operator diff views for revision and subtree comparison
- rich progress/event streaming beyond the minimum typed runtime events needed for controller correctness and console auditability
- pack authoring UX and registry/product surfaces
- polished lineage/audit reporting exports

### Migration support / cleanup helpers

- tooling to inspect or export legacy `run` / `attempt` history after cutover
- one-off backfill/report scripts for historical data where needed
- cleanup automation for removing dead legacy routes, tables, and compatibility shims
