# 11 — Phase 11: Graph Operator Surfaces and Definition Authoring

## Goal

Turn the console from a compact operator summary into a graph-native product surface for:

- truthful runtime visibility
- richer operator drilldown
- safe workflow / role / policy authoring
- skill reference management

This phase is where AutoClaw should start to feel closer to a polished workflow product.
It is **not** where the semantic contract should be invented.

## Why this phase exists

Current reality:

- the runtime graph model is real
- the console is still mostly a list-and-forms MVP
- workflow/role descriptions exist, but node description is not yet a first-class source/compiled concept
- registry authoring/publish flows are still placeholder-heavy
- AutoClaw stores skill references/pins, while OpenClaw still owns skill internals

That means the product can already execute real flows, but the operator/authoring surface is still much thinner than the runtime underneath it.

This phase exists to close that product gap **after** packaging and semantic safety are ready.

## Preconditions

Do not start this phase seriously until these are true:

- Phase 8 closeout has frozen runtime recovery semantics well enough that the UI is not papering over undefined behavior
- Phase 9 has delivered packaged console/assets/definitions as a real product surface
- Phase 10 has defined explicit effective-node semantics, including authoring precedence and first-class node description handling

If those prerequisites are not true yet, authoring/UI work will outrun the real contract and start lying.

## In scope

### 1. Graph-native runtime/operator view

Add a truthful graph view for a task/flow with:

- nodes
- edges
- per-node state overlays (`ready`, `running`, `waiting`, `paused`, `done`, `failed`)
- current wait reason
- current attempt/session/manifest summary
- approval/watchdog/retry badges
- revision identity and provenance where useful

This should read from relational runtime truth, not transcript reconstruction.

### 2. Richer node detail and provenance surfaces

Surface the information operators and future authors actually need:

- workflow description
- role description
- policy description where relevant
- first-class node description
- effective version provenance
- checkpoint / approval / manifest / session drilldown

A node card should explain both **what the node is for** and **what state it is in**.

### 3. Console definition authoring

Add safe draft/publish/versioned authoring flows for:

- workflows
- roles
- policies

The console should be able to:

- create drafts
- edit drafts
- validate drafts through compiler-backed rules
- publish intentionally
- inspect provenance/version history

Do not make the browser invent or guess unsupported semantics.

### 4. n8n-inspired workflow editing, but on AutoClaw’s contract

It is reasonable to borrow interaction ideas from n8n:

- graph editing
- node cards
- inline side panels
- inspector-style editing
- readable execution overlays

But keep AutoClaw’s actual model:

- edit workflow definitions, not live runtime state
- compile into immutable plans
- keep execution truth in `flow` / `flow_revision` / `flow_node` / `node_attempt`
- do not let the UI become a second scheduler

### 5. Skill reference UX

Improve the skill experience around the architecture already chosen:

- search/pick skill references
- inspect current pinned version/manifest
- update pins deliberately
- show provider/source information
- validate required/blocked skill combinations once Phase 10 semantics exist

Default product stance:

- AutoClaw owns skill **references/bindings/pins**
- OpenClaw owns skill **packages/internals/tools/behavior**

### 6. Packaged console product quality

Make the richer console a real shipped product surface, not a repo-only dev toy:

- packaged assets
- runtime config coming from the server, not baked secrets
- local-first operator experience
- clean flow from install → bootstrap → open console → author/run/inspect

## Explicit non-goals

This phase should **not**:

- replace the flow-first runtime model with browser-owned state
- make transcript text the control truth
- treat drag-and-drop polish as more important than semantic correctness
- host raw skill source/code upload by default
- move OpenClaw skill-package ownership into AutoClaw without an explicit architecture change
- hide watchdog/recovery ambiguity behind cosmetic UI buttons

## Guardrails

- the console must remain a projection of runtime/compiler truth, not a competing source of truth
- authoring forms must validate against compiler/runtime rules, not looser browser-only guesses
- node description must be first-class and inspectable, not just hidden inside opaque `metadata`
- graph editing must target workflow definitions and compiled output, not mutate live runtime topology in place
- skill UX should improve reference management first, not raw code hosting

## Suggested implementation order

### 1. Truthful graph read models

Before major UI work, make sure the API can return one clean graph-ready payload with:

- nodes
- edges
- live state overlays
- wait reasons
- attempt/session/manifest summaries
- effective provenance where needed

### 2. Description/provenance surfaces

Expose:

- workflow description
- role description
- policy description
- node description
- effective skill/provenance summaries

### 3. Graph operator view

Build the visual runtime graph first.
This should make the existing operator/debug loop materially better even before editing ships.

### 4. Draft/publish definition flows

Add explicit versioned authoring for workflow/role/policy definitions.
Start form-first if needed.

### 5. Graph editor on top of the real authoring contract

Only once draft/publish + compiler validation are solid should the graph editor become the primary authoring surface.

### 6. Skill reference management UX

Add search/pin/update/provenance flows once the editor and effective-node semantics can represent them honestly.

## Success criteria

This phase is complete when all of these are true:

- operators can inspect a flow as a real graph with truthful state overlays
- node purpose/context is clear through workflow/role/policy/node descriptions
- the console can create and publish definitions without bypassing compiler/runtime safety
- graph editing modifies authoring definitions, not live runtime truth
- skill references can be managed cleanly without making AutoClaw the default host of skill internals
- the richer console ships as part of the packaged local-first product
