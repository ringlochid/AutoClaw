# Console Validation And Evidence Contract

Date: 2026-06-30

This document defines the evidence required for implementation scopes and final
release review.

## Scope Evidence Directory

Use the fresh evidence root:

`/home/ubuntu/leo/projects/autoclaw/tmp/autoclaw-frontend/full-delivery-design-parity`

Per-scope directories:

- `00-foundation/`
- `01-tasks/`
- `02-task-detail/`
- `03-human-requests/`
- `04-command-runs/`
- `05-definitions/`
- `06-task-start/`
- `07-definition-editor/`

Each scope must save:

- served-design browser screenshots for desktop and narrow viewports;
- app browser screenshots for matching states;
- browser comparison notes;
- command output or command summary;
- accessibility/focus notes;
- review report;
- commit hash after review passes.

## Served Design Requirement

Design pages are served through `python3 -m http.server` for browser
inspection:

```sh
cd /home/ubuntu/leo/projects/autoclaw/references/frontend_design/pages
python3 -m http.server 18773 --bind 127.0.0.1
```

Review must record the exact served URL, viewport, state, and screenshot path.
If browser or image inspection is unavailable, the scope must publish an
explicit degraded-evidence note or blocker. Shell reads of HTML/CSS/PNG are not
visual acceptance.

## Command Gates

Always run:

- `git diff --check`

For shared console or page code, run the applicable subset:

- `make console-format-check`
- `make console-lint`
- `make console-typecheck`
- `make console-openapi-check`
- `make console-test`
- `make console-test-integration`
- `make console-build`
- `make console-e2e`

Run `make console-openapi-check` when API types, route helpers, generated
clients, SSE, fixtures, or backend-shape assumptions change.

If a command is skipped, record why, the risk, and the compensating evidence.

## Existing Test Surface

Current source has API foundation integration tests, page integration tests for
required pages, MSW fixtures, and Playwright e2e specs for required pages. The
visual test directory is still an empty lane, so saved screenshots and browser
review notes remain required for design parity.

Older docs that say integration tests or mocks are empty are stale.

## Review Gate

Strict review must check:

- source precedence and backend/design conflict handling;
- current app config/source before active-state judgment;
- all states required by `feature-behavior.md`;
- browser parity against served HTML and PNG references;
- desktop and narrow viewport behavior;
- keyboard focus, modal focus trap/restore, labels, errors, and hit targets;
- no fake metrics, counts, ETAs, progress, support-file truth, routes, or
  labels;
- fixture and test coverage for changed behavior;
- no unrelated worktree churn.

## Commit Gate

After review passes, commit that scope before starting the next scope. Do not
batch multiple functional pages into one commit unless the current review scope
explicitly allows it.

If unrelated user or prior changes are present, leave them alone and document
the dirty-worktree boundary in the review evidence.

## Final Release Gate

Final validation must serve the design pages, compare every released page
against served design HTML plus PNG references in browser, check desktop and
narrow viewports, verify accessibility/focus behavior, verify scope commits,
run applicable console validation commands, and block release on visual
mismatch or hidden debt.
