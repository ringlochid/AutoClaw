# Docs structure standard

Status: Reference

Use this guide when adding, moving, splitting, versioning, or redesigning docs
pages.

## Core model

AutoClaw docs should separate **audience**, **task**, **page type**, and
**version**.

Do not treat the docs tree as a direct mirror of the code tree, the phase plan,
or the implementation timeline.

Use three layers:

1. **Public product and operator docs**
   - for onboarding, workflows, concepts, operations, troubleshooting, and
     user-visible behavior
2. **Public reference and internals docs**
   - for exact CLI, schema, API, contract, maintainer, and stable
     implementation reference
3. **Internal canon docs**
   - for design truth, shipped-behavior contrast, execution routing, evidence,
     reviews, migration notes, ADRs, and archive material

## Public versus internal versioning

Version public docs only when AutoClaw intentionally supports multiple public
product versions in parallel.

Default rule for public docs:

- keep public docs versionless by default
- do not add `v1`, `v2`, or `vnext` folders under public docs just because the
  internal design changed
- only add public version selectors or versioned public folders when multiple
  supported public releases must coexist for readers

Default rule for internal canon:

- version internal docs explicitly by directory
- prefer `v1/`, `v2/`, and `vnext/`
- use directory-level versioning, not filename suffixes such as
  `runtime-v2-final.md`
- freeze one internal version when it becomes historical and move active future
  design into `vnext/`

## Current transition rule

Today, the repo still uses these legacy internal-canon buckets:

- `docs/redesign/**`
- `docs/current/**`
- `docs/execution/**`
- `docs/archive/**`

Treat those as the **current transitional layout**, not as the final public
information architecture and not as the final internal naming scheme.

Until the docs migration lands:

- keep target design truth in `docs/redesign/**`
- keep shipped-behavior contrast in `docs/current/**`
- keep plans, evidence, reviews, and gates in `docs/execution/**`
- keep historical material in `docs/archive/**`

Target internal homes:

- `docs/redesign/**` -> `docs-internal/design/vnext/**`
- `docs/current/**` -> `docs-internal/current/<owning-version>/**`
- `docs/execution/**` -> `docs-internal/execution/<owning-version>/**`
- `docs/archive/**` -> `docs-internal/archive/**`

If the repo later introduces explicit published internal ADRs, place them under:

- `docs-internal/adr/**`

## Target public docs methodology

The long-term public docs structure should follow reader intent first.
Recommended top-level public lanes are:

- `docs/start/**`
- `docs/concepts/**`
- `docs/operator/**`
- `docs/runtime/**`
- `docs/openclaw/**`
- `docs/authoring/**`
- `docs/reference/**`
- `docs/help/**`

Stable implementation-heavy public material should live under dedicated
reference lanes such as:

- `docs/reference/internals/**`
- `docs/reference/maintainers/**`

The exact folder names can change during the redesign, but the three-layer model
must stay intact.

## Target internal canon methodology

Internal canon should be explicit about version era.

Recommended internal top-level structure:

- `docs-internal/design/v1/**`
- `docs-internal/design/v2/**`
- `docs-internal/design/vnext/**`
- `docs-internal/current/v1/**`
- `docs-internal/current/v2/**`
- `docs-internal/current/vnext/**` only when current shipped contrast genuinely
  exists for a next-era branch or long-lived prerelease line
- `docs-internal/execution/v1/**`
- `docs-internal/execution/v2/**`
- `docs-internal/execution/vnext/**`
- `docs-internal/archive/**`
- `docs-internal/adr/**`

Rules:

- `design/` replaces `redesign/` as the steady-state name
- `current/` remains contrast, not target truth
- `execution/` remains implementation-control and record-keeping, not product
  truth
- `archive/` is historical only
- `adr/` is for durable accepted decisions, not speculative plans or raw design
  notes

## Placement rules

### Put a page in public product or operator docs when:

- a reader needs it to install, onboard, author, operate, troubleshoot, or use
  AutoClaw safely
- the page teaches a workflow, concept, responsibility boundary, or
  operational behavior
- the behavior is part of the supported product surface

Examples:

- install and first-run flows
- onboarding and local setup
- workflow and task-compose authoring
- operator workflows and observability entry points
- runtime mental models and user-facing lifecycle explanations
- troubleshooting and migrations readers must perform

### Put a page in public reference or internals when:

- the page is stable lookup material
- the audience is contributor, integrator, operator, or maintainer
- the material is implementation-aware but still useful as durable reference
- the detail is too mechanical or exhaustive for a guide or topic page

Examples:

- exact CLI flag and output contracts
- schema and payload reference
- operator surface reference
- runtime record or dispatch contract reference
- stable load pipeline or adapter internals
- maintainer templates and release/reference material

### Put a page in internal canon docs when:

- the page exists to drive implementation, migration, design landing, or
  execution control
- the page compares current and target behavior
- the page records a phase plan, evidence artifact, review, or file-lock rule
- the page is temporary or version-era-specific implementation-control truth
  rather than stable product/reference truth

Examples:

- design architecture truth
- current-behavior contrast pages
- execution plans, evidence, reviews, gates, and maps
- migration-only decision records
- version-era specific implementation specs
- archive and historical provenance

## Implementation-detail rule

Implementation details are allowed in docs, but they must be placed by
**stability** and **audience**.

- if the detail explains a stable public boundary, put it in a public
  architecture or topic page
- if the detail is deep but stable contributor reference, put it in
  `reference/internals` or an equivalent public internals lane
- if the detail is design-only, migration-only, version-era-only, or
  execution-only, keep it in internal canon docs

Do not dump active implementation-program material into public onboarding,
concept, or troubleshooting pages.

## Page-type rules

Separate page types clearly.

- **Overview / topic page**: what the surface is, what it owns, how to use it
  safely
- **Guide**: one workflow from prerequisites to verification
- **Reference**: exhaustive fields, flags, schemas, enums, contracts, outputs
- **Internals**: stable implementation mechanics for contributors and
  maintainers
- **Troubleshooting**: symptom -> checks -> cause -> fix
- **Plan / review / evidence**: internal canon only
- **ADR**: durable accepted decision, context, alternatives, and consequences

Do not let one page try to be all of these at once.

## Architecture plus internals pattern

For important technical surfaces, prefer the OpenClaw-style pairing:

- `surface.md` -> boundary, purpose, ownership, supported behavior
- `surface-internals.md` -> pipeline, state model, mechanical details, tables,
  and deeper contributor reference

Use this pattern only when both pages have a clear audience and durable value.
Do not create an `-internals` page just to park temporary notes.

## Navigation rules

- public docs navigation should be curated by reader intent, not derived
  mechanically from folders
- internal canon pages should not become the default public browsing surface
- maintainer-heavy public pages should live under reference or maintainer lanes,
  not under onboarding
- internal canon should not be mixed into the public nav by default
- if a page is private, scratch, or mirror-only, keep it out of public nav and
  publish paths

If an unpublished scratch area is needed later, prefer:

- `docs-internal/scratch/**`

Do not let scratch pages compete with design, current, execution, archive, or
public reference owners.

## Duplication rules

- keep one canonical owner for each truth surface
- do not duplicate the same contract across public guide, public reference, and
  internal canon pages unless one page is intentionally a short routing summary
- if a public page depends on deep implementation detail, summarize the
  implication and link to the owning reference or internals page
- if an internal design or current page exists only to preserve temporary
  contrast, keep it out of stable public reference lanes
- if a version split exists internally, avoid repeating the same stable content
  across `v1/`, `v2/`, and `vnext/` unless the contract truly changed

## Migration rules

When redesigning the docs tree:

1. classify the page as public product/operator, public reference/internals, or
   internal canon
2. decide the page type before moving or rewriting it
3. decide whether the content belongs to a specific internal version era
4. preserve canonical transitional truth until a replacement owner is explicit
5. move stable reader-facing material into the public `docs/**` lanes
6. move internal versioned material into `docs-internal/**`
7. add redirects or routing notes when a moved page had meaningful prior entry
   points
8. when renaming `redesign` to `design`, update routing language together with
   the path move so truth does not fork

Do not flatten `docs/redesign`, `docs/current`, and `docs/execution` directly
into one public tree without reclassifying the audience, page type, and version
ownership first.

## Cross-checks

- if the page claims target truth, verify it matches the active design canon
  path for this repo stage
- if the page claims shipped truth, verify it matches current behavior or
  explicit migration notes
- if the page claims public reference, verify the contract is stable enough to
  expose as durable reference
- if the page claims internals, verify the audience is contributor or
  maintainer and the mechanics are not just temporary execution notes
- if the page claims execution authority, verify it points to the correct phase
  page and file-lock map
- if the page is guidance only, verify it does not silently compete with root
  canon
- if the page sits under internal canon, verify its version-era home is
  explicit or intentionally versionless for archive/ADR reasons
