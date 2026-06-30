# Console Component System

Status: Locked target for implementation planning.

This page defines the frontend component and design-system boundaries for the
V2 console. It translates the design handoff into implementation rules without
copying static prototype HTML, page-local CSS selectors, or prototype scripts.

## Source Anchors

Use these design references for visual behavior:

- `references/frontend_design/design/navigation.md`
- `references/frontend_design/design/DESIGN.md`
- `references/frontend_design/design/product-brief.md`
- `references/frontend_design/design/work-package-map.md`
- `references/frontend_design/design/reference-anchors.md`
- `references/frontend_design/feature-charters/pages/*.md`
- `references/frontend_design/feature-charters/packages/*.md`
- `references/frontend_design/pages/*.html`
- `references/frontend_design/pages/*.png`
- `/home/ubuntu/leo/design/autoclaw-v2-ui/**` when checking upstream design
  parity

The copied `references/frontend_design/**` paths currently match the external
design workspace except for workspace-only files such as `.git`, `.agents`,
`AGENTS.md`, `README.md`, and `STYLE.md`. Prefer copied refs for implementation
tasks and use the external workspace only for parity checks or design-owner
inspection.

## Design Language

The console uses the warm light, task-first control-room direction:

- light paper-like surfaces
- compact operational metadata
- restrained blue/indigo active state
- quiet borders and selection states
- progressive disclosure over always-open detail
- one shared shell across runtime and authoring
- minimal components for full feature coverage

The implementation token owner is `apps/console/src/styles/tokens.css` with the
`--ac-*` namespace. Do not carry prototype-only `--oc-*` tokens, copied static
page selectors, or inline prototype scripts into `apps/console`.

## Shared Shell

The shared shell owns:

- left rail primary navigation
- top breadcrumb/status row
- page content inset
- runtime versus authoring grouping
- responsive mobile primary navigation

Required primary nav entries:

- `Tasks`
- `Definitions`
- `Task Start`

Required breadcrumb families:

- `Tasks`
- `Tasks / {task title or task id}`
- `Tasks / {task title or task id} / Human Requests`
- `Tasks / {task title or task id} / Command Runs`
- `Definitions`
- `Definitions / Editor`
- `Task Start`

Do not show `Task Control Suite`, `/runtime`, `/control`, `/operator`,
`Overview` as a page, or raw task ids as the preferred breadcrumb label when a
task title is available.

## Primitive Ownership

Shared primitives should exist only when they remove real repetition or enforce
a contract:

- buttons and icon buttons
- chips for status, kind, and selected state
- segmented controls for kind/mode switches
- tabs for selected detail modes
- dialogs and drawers
- disclosure rows
- table/list rows
- empty, loading, error, auth failure, and stale-action panels
- form fields, selects, textareas, and schema-backed inputs
- property grids
- log viewer
- timestamp and id/ref renderers

Use `lucide-react` icons in icon buttons when a matching icon exists.
Icon-only controls must have accessible labels and tooltips when meaning is not
obvious from nearby text.

## Page Composition Patterns

### Scan-First List

Use for `Tasks` and `Definitions`.

Contract:

- controls above the list
- rows front-load identity, status or kind, and updated time
- secondary metadata stays compact
- load-more follows cursor truth
- no KPI/dashboard cards competing with the list

### Control Room

Use for `Task Detail`.

Contract:

- graph is read-only and dominant on wide screens
- event lane stays chronological and compact
- selected detail opens through focused modal, drawer, or equivalent disclosure
- sibling page previews stay compact
- large logs, manifests, and prompt bodies stay behind refs or sibling pages

### Queue And Focused Work

Use for `Human Requests`.

Contract:

- queue stays compact
- selected request summary is separate from item response
- one focused item at a time
- notes are item-scoped
- resolve actions stay grouped with the selected request

### Disclosure-First List

Use for `Command Runs`.

Contract:

- one large list surface
- row summary first, detail on deliberate expansion
- logs hidden by default
- cancel stays contextual and legal-state-bound

### Authoring Workbench

Use for `Definitions`, `Definition Editor`, and `Task Start`.

Contract:

- stored truth, draft truth, preview truth, diff truth, apply truth, and launch
  truth are visually labeled and separated
- draft selector is a compact list, not nested decorative cards
- editor mode switches own `Edit`, `Validation`, and `Preview`
- task start is a flat form with preview/result disclosures

## Responsive Rules

- Preserve hierarchy before squeezing columns.
- On medium widths, switch secondary surfaces into tabs, drawers, or mode
  switches before compressing them into unreadable rails.
- On narrow widths, stack source/list/summary before focused detail and actions.
- Avoid horizontal overflow except for intentionally scrollable log/code blocks.
- Preserve primary action reachability without oversized sticky toolbars.
- Text must not overlap or overflow parent controls.

Page-specific order on narrow screens:

- Tasks: controls, list, load more.
- Task Detail: header, graph, events, open-detail actions, sibling handoffs.
- Human Requests: queue, selected summary, instruction, item navigation,
  response controls, notes, resolve actions.
- Command Runs: list rows, expanded detail, log disclosure.
- Definitions: kind switch, controls, list, selected detail, versions.
- Task Start: workflow search, selected workflow summary, task fields, roots,
  preview/start actions, result.
- Definition Editor: draft selector, editor, validation/preview output, apply.

## Accessibility Rules

Implementation slices must cover:

- semantic headings and landmarks
- labelled form controls
- keyboard access to nav, filters, rows, disclosures, tabs, dialogs, graph
  selection, and actions
- visible focus states
- modal/drawer focus return and close behavior
- color-with-text status treatment
- disabled versus hidden action semantics that match legality
- no keyboard traps in log/code/editor regions

Action failure and stale-currentness states must be announced near the action
that failed and must preserve operator context.

## Visual Reference Caveat

`task-detail.png` is not a trusted final visual parity target.

Task Detail implementation should use:

- `references/frontend_design/pages/task-detail.html`
- `references/frontend_design/pages/task-detail-modal-open.png`
- semantic design docs and page charter
- a fresh promoted Task Detail capture before release readiness

The referenced `task-detail-last-known-good.jpeg` is absent in both copied and
external design page folders. Release review must require a fresh capture or an
explicit replacement visual-review note.

## Component Extraction Rules

Extract shared components when:

- two or more pages use the same behavior and state grammar
- a primitive enforces accessibility or action legality consistently
- a mapper/state pattern becomes a true shared API boundary
- repeated Tailwind utility clusters would otherwise drift from tokens

Do not extract:

- page-specific orchestration before a second real use exists
- components that hide controller state or action legality
- generic helper names without domain responsibility
- prototype wrappers that preserve stale HTML structure

## Forbidden Component Drift

- no card inside card nesting for ordinary page sections
- no decorative dashboard tiles for unsupported metrics
- no one-off color palettes outside `--ac-*` tokens
- no dynamic Tailwind class construction such as `bg-${status}`
- no page-local copies of auth/config/error/pagination behavior
- no static prototype JavaScript in React components
- no invented count badges unless the controller exposes real count fields
