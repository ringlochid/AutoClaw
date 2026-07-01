# AutoClaw Console Contract

Date: 2026-06-30

This directory is the locked frontend contract for the AutoClaw console design
parity rebuild. It is scoped to planning and implementation review for the
React console under `apps/console`.

## Contract Docs

- `frontend_contract_docs.md`: inventory and non-negotiable planning rules.
- `feature-behavior.md`: required page behavior and state matrices.
- `api-view-model-contract.md`: backend/API, SSE, error, fixture, and
  view-model boundaries.
- `component-system.md`: shell, tokens, components, icons, active states, and
  responsive behavior.
- `environment-and-runtime-config.md`: local runtime config and deployment
  assumptions.
- `validation-and-evidence.md`: validation commands, browser comparison,
  accessibility/focus, review, and commit gates.
- `ambiguity-and-debt-log.md`: open decisions, blockers, risks, and next
  actions.

## Source Precedence

Backend/OpenAPI truth wins for schemas, route names, action legality, auth,
currentness, and state names. Design references win for layout, spacing, color,
shadow, typography, component shape, active states, icon usage, visual density,
and responsive hierarchy.

Backend schema wins over visual mock data when they conflict. Do not invent
icons, fake metrics, task counts, ETAs, progress, unsupported states,
support-file truth, backend routes, or user-facing labels.

## Required Browser Source

Design pages must be served through `python3 -m http.server` for browser
inspection:

```sh
cd /home/ubuntu/leo/projects/autoclaw/references/frontend_design/pages
python3 -m http.server 18773 --bind 127.0.0.1
```

The mirror directory `/home/ubuntu/leo/design/autoclaw-v2-ui/pages` may be used
the same way if the repo copy is unavailable. Record the source, port, viewport,
URL, screenshot path, and observed state in each scope evidence directory.

## Current Implementation Status

The current console is not placeholder-only. It already has app routes, shell
navigation, API config, route helpers, a JSON client, fetch-based SSE,
view-model mappers, feature pages, MSW handlers, fixtures, integration tests,
and e2e tests for required pages.

That does not make the implementation accepted. Each scope must inspect current
source/config, compare against served design pages and PNG references in
browser, run applicable commands, pass strict review, and be committed before
the next scope starts.

Implementation reviews must inspect actual app config/source before judging
active-state behavior, including router, nav, token/style files, component
variants, fixtures, state mappers, and active-route config.

## Required Page Targets

- Tasks.
- Task Detail.
- Human Requests.
- Command Runs.
- Definitions.
- Task Start.
- Definition Editor.

Implementation scope order and gates are defined in
`references/frontend/frontend_delivery_plan.md`.
