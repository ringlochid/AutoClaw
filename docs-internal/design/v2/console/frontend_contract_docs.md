# Console Frontend Contract Docs

Date: 2026-06-30

This inventory locks the console planning contract for the design parity
rebuild. It points to the contract docs that implementation and review must
use before product code changes.

## Locked Docs

- `README.md`: contract index, source precedence, current implementation status,
  and review rules.
- `feature-behavior.md`: page behavior contracts, state matrices, and
  backend/design anchors for each required page.
- `api-view-model-contract.md`: API, route, SSE, error, fixture, and
  view-model boundaries.
- `component-system.md`: shell, token, component, icon, active-state, and
  responsive rules.
- `environment-and-runtime-config.md`: runtime config, API base, API key,
  local dev, fixtures, and deployment assumptions.
- `validation-and-evidence.md`: command, browser, accessibility, review,
  evidence, and commit gates.
- `ambiguity-and-debt-log.md`: blocked or risky decisions with owner, block
  status, and next action.

## Non-Negotiable Rules

- Design pages are served through `python3 -m http.server` for browser
  inspection. Filesystem reads of HTML/CSS/PNG are support evidence only.
- Implementation reviews inspect actual app config/source before judging
  active-state behavior. Required source includes router, nav, token/style
  files, component variants, fixtures, state mappers, and active-state config.
- Backend schema wins over visual mock data when they conflict.
- Backend/OpenAPI truth wins for schemas, routes, action legality, auth,
  currentness, and state names.
- Served design HTML, PNG references, page charters, navigation contract,
  design direction, and shared design CSS/JS win for layout, spacing, color,
  shadows, typography, component shape, active states, icon usage, visual
  density, and responsive hierarchy.
- Current console source is a candidate implementation, not acceptance proof.
  Existing pages still require served-design browser comparison, validation,
  review, and commit gates.

## Planning Evidence

Planning audit:
`/home/ubuntu/leo/projects/autoclaw/tmp/autoclaw-frontend/full-delivery-design-parity/frontend_source_audit.md`

Delivery plan:
`/home/ubuntu/leo/projects/autoclaw/references/frontend/frontend_delivery_plan.md`

Design reference directory:
`/home/ubuntu/leo/projects/autoclaw/references/frontend_design/pages`

Mirror design directory:
`/home/ubuntu/leo/design/autoclaw-v2-ui/pages`

Required implementation scopes:

1. Foundation/API config.
2. Tasks.
3. Task Detail.
4. Human Requests.
5. Command Runs.
6. Definitions.
7. Task Start.
8. Definition Editor.

Each scope must produce saved browser evidence, command evidence, review notes,
and a scope commit before the next scope starts unless it publishes a blocker.
