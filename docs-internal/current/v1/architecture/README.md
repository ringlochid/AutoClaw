# Current architecture

Status: Current

Last verified: 2026-05-05

This surface routes to the current architecture pages for shipped runtime, manifest, task-root, and read-model behavior. It is current-behavior contrast only, not design canon.

## Search-first routing

If you are asking:

- "How does the current control plane work?" -> [Runtime control plane](runtime-control-plane.md)
- "What runtime/operator read surfaces exist today?" -> [Current runtime read models and operator surfaces](runtime-read-models-and-operator-surfaces.md)
- "How does the current manifest projection work?" -> [Current workflow-manifest projection](manifest-projection-and-acknowledgement.md)
- "How are current task directories laid out?" -> [Task directories and materialized paths](task-roots-and-materialized-paths.md)

## Start here

- [Runtime control plane](runtime-control-plane.md)
- [Current runtime read models and operator surfaces](runtime-read-models-and-operator-surfaces.md)
- [Current workflow-manifest projection](manifest-projection-and-acknowledgement.md)
- [Task directories and materialized paths](task-roots-and-materialized-paths.md)

## Background contrast

These shipped-behavior notes remain reachable for migration and implementation contrast. They are not additional target-design owners.

- [Current architecture at a glance](current-architecture.md)
- [Current system baseline](system-baseline.md)
- [Current OpenClaw and bridge-plugin baseline](openclaw-and-bridge-plugin.md)
- [Current OpenClaw dispatch and session contract](openclaw-dispatch-and-session-contract.md)
- [Current parent, retry, and operator control](parent-retry-and-operator-control.md)
- [Current watchdog and OpenClaw bridge](watchdog-and-openclaw-bridge.md)
- [Current watchdog and runtime monitoring](watchdog-and-runtime-monitoring.md)

## Keywords

- runtime control plane
- operator snapshot
- operator trace
- observability refs
- workflow manifest
- task-root layout

## Surface rule

Use this surface for shipped runtime, manifest, task-root, and read-model behavior only.

When current and design differ about target behavior, design wins and this surface remains contrast-only. Pages not linked above remain background architecture notes, not the maintained current-truth entry points for this surface.
