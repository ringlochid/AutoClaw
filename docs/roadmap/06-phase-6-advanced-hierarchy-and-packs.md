# 06 — Phase 6: Advanced Hierarchy and Packs

## Goal

Expand AutoClaw from the default runtime contract into larger supervised workflow packs when the simpler path is proven.

## In Scope

- advanced workflow packs
- subtree supervisors
- optional dependency-edge scheduling where tree ownership is not enough
- MVP-builder style orchestration pack

## Out of Scope

- making advanced hierarchy the default for every task
- uncontrolled graph growth
- fully generic everything-engine ambitions

## Deliverables

- one or two advanced packs that actually work
- subtree runtime model
- clear operator visibility rules for expanded flows

## Data Model Changes

- `node_iterations` if not already added
- optional `flow_edges`
- any subtree revision metadata required

## API / Runtime Changes

- subtree inspection
- expanded pack launch path
- optional advanced scheduling hooks

## Tests / Verification

- advanced pack runs do not break the default path
- subtree ownership remains queryable
- operator console still defaults to a simple top-level view

## Exit Criteria

Phase 6 is done when at least one advanced workflow pack is usable without making the kernel or dashboard unreadable.

## Deferred Follow-ups

- very broad pack catalog
- marketplace/distribution stories

## Risks

- graph explosion
- architecture drift caused by impressive but unnecessary complexity
