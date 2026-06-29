# Console Validation And Evidence

Status: Target

This page locks proof requirements for console implementation slices and final
release review.

## Command Matrix

Base commands for frontend implementation slices:

- `make console-format-check`
- `make console-lint`
- `make console-typecheck`
- `make console-test`
- `make console-test-integration`
- `make console-build`

Add `make console-openapi-check` when a slice touches API clients, generated
types, route usage, view models, fixtures derived from OpenAPI, action handling,
or API contracts.

Add `make console-e2e` when a slice changes navigation, page-level flows,
browser-only behavior, visual parity, accessibility-critical interactions, or
the final release suite and browser dependencies are available.

`make check-console` is the non-browser aggregate gate and must pass before
release readiness once integration coverage is non-empty.

## Current Coverage Caveat

`make console-test-integration` currently passes with no tests because
`passWithNoTests` is enabled. This is not meaningful workflow proof.

The API/config foundation slice must add real MSW-backed integration coverage
before page slices can claim API-backed workflow readiness.

## Fixture Ownership

The foundation slice owns:

- MSW setup
- handler conventions
- fixture directory naming
- shared success/loading/empty/auth/error/stale/network scenarios
- OpenAPI-shaped payload factories
- stream fixture helpers
- normalized error fixture helpers

Required fixture families:

- task list
- task detail current read, snapshot, trace, events backfill, and SSE stream
- human requests and typed resolutions
- command-run list, detail, log, and cancel
- definition role/policy/workflow lists, detail, and versions
- draft-set authoring lifecycle
- task start workflow selection, root bindings, success, and failures
- OperationFailure, FastAPI validation, auth, stale currentness, missing
  resource, network, and `cursor_reset_required`

Page slices may extend fixtures for their route family, but they must not fork
shared API helpers or create page-local mock transport layers.

## Per-Slice Evidence

Every implementation slice must write evidence under its
`tmp/autoclaw-frontend/<slice>` path with:

- exact commands run and outcomes
- skipped commands with exact environment or scope reason
- API routes exercised
- fixtures/scenarios covered
- browser/manual checks performed
- screenshots or screenshot paths when visual parity is in scope
- accessibility and keyboard checks
- known residual risks and routed debt

## Browser And Manual Evidence

Use browser evidence for any page-level flow, navigation, visual, responsive, or
accessibility claim.

Minimum page browser states:

- Tasks: default list, dense list, filters/search/sort, no-results, empty,
  load-more, error/auth, row focus/open navigation.
- Task Detail: REST bootstrap, graph, event lane, selected node/event, trace
  detail, stale task action, reconnect/reset path, sibling navigation.
- Human Requests: each request kind, multi-item navigation, notes, structured
  input, stale resolution, terminal readback, empty queue.
- Command Runs: every state, expanded row, log hidden/visible, missing log,
  cancel allowed/denied, empty list.
- Definitions: kind switching, filters/search/sort, selected detail, versions,
  empty/no-results/error, pivots.
- Task Start: workflow search/select, required fields, root modes, preview,
  success, unknown workflow, invalid host path, auth/validation failure.
- Definition Editor: draft load, new draft, edit dirty/clean, reset,
  rematerialize-current confirmation, validation, preview, apply, auth error.

## Visual Evidence

Use copied design references as visual anchors:

- `references/frontend_design/pages/tasks.html` and `tasks.png`
- `task-detail.html` and `task-detail-modal-open.png`
- `human-request.html` and `human-request.png`
- `command-runs.html` and `command-runs.png`
- `definitions.html` and `definitions.png`
- `task-start.html` and `task-start.png`
- `definition-editor.html`, `definition-editor.png`, and
  `definition-editor-replace-modal.png`

Task Detail caveat:

- `task-detail.png` is not trusted as final parity proof.
- `task-detail-last-known-good.jpeg` is absent.
- Task Detail release readiness requires a fresh promoted capture or an
  explicit visual-review note that names the replacement anchor used.

Screenshots must cover desktop and narrow/mobile widths for each released page.
States with modals, disclosures, logs, validation output, preview, or error
content need their own evidence when those states are part of the acceptance
surface.

## Accessibility Evidence

Each page slice must check:

- keyboard path through primary controls
- visible focus states
- labels for inputs and icon buttons
- dialog/drawer focus behavior and close/return
- disclosure and tab keyboard behavior
- color-with-text status treatment
- no horizontal overflow at narrow widths
- no text overlap or clipped button labels

Use automated accessibility checks when available, but do not treat automated
checks as a substitute for keyboard and focus walkthrough evidence.

## Review Gates

Required reviews:

- Foundation contract/integration review before page slices start.
- Focused SSE/API review after Task Detail.
- Authoring contract review before Definition Editor closure.
- Final suite release review after all page slices publish implementation,
  verification, review, and closure evidence.

Reviewers must reject slices that:

- invent unsupported controller fields or states
- hide structured errors
- skip meaningful integration coverage
- claim visual parity from untrusted Task Detail PNG
- omit browser evidence for page-level behavior
- pass raw API payloads deeply through components
- launch from stale compose drafts

## Final Release Evidence Index

The final release review must collect an index under
`tmp/autoclaw-frontend/99-suite-release-review` that links:

- implementation reports for each slice
- review reports
- command summaries
- browser notes
- screenshots
- accessibility notes
- visual parity notes
- known accepted nonblocking debt

Release may accept only explicitly phase-bounded nonblocking debt that does not
violate controller truth, action legality, accessibility, security, or data
integrity.
