# Console Environment And Runtime Config Contract

Date: 2026-06-30

This document locks the environment and runtime config assumptions for the
frontend rebuild.

## Current Runtime Config

Current console config lives in frontend source. The app normalizes:

- API base URL, defaulting to `http://127.0.0.1:18125`.
- Blank API key values to `null`.
- API-key headers through the shared client for protected routes.

No current API route map or OpenAPI evidence supports a backend
`/console/config` endpoint. Do not implement or depend on that route unless a
backend contract is added.

## Local Development

Expected local surfaces:

- Console package: `apps/console`.
- Package scripts: `dev`, `build`, `typecheck`, `lint`, `format:check`,
  `test`, `test:integration`, `test:e2e`, and `openapi:generate`.
- Root Make targets include `console-format-check`, `console-lint`,
  `console-typecheck`, `console-openapi-check`, `console-test`,
  `console-test-integration`, `console-e2e`, `console-build`, and
  `check-console`.
- MSW handlers and fixtures support local contract tests and page review.

Design pages must be served separately for visual review:

```sh
cd /home/ubuntu/leo/projects/autoclaw/references/frontend_design/pages
python3 -m http.server 18773 --bind 127.0.0.1
```

Record the served source, port, viewport, page URL, and screenshot paths in the
scope evidence directory.

## Fixture And Mock Boundaries

Fixtures are allowed for local and test coverage only when they model backend
schema. Backend schema wins over visual mock data when they conflict.

Fixture data must not add product truth for:

- task counts not exposed by backend;
- progress or ETA;
- support-file content not returned by a route;
- action legality not provided by backend;
- route families not in the current route map;
- user-facing labels invented from prototype copy.

## Deployment And Auth Assumptions

- Protected requests use `X-AutoClaw-API-Key`.
- Missing or blank API key must produce a clear frontend state and must not
  silently bypass protected route errors.
- Network, abort, HTTP, validation, and backend operation errors must render
  through normalized error views.
- Currentness-sensitive actions must use fresh backend tokens or revision ids
  where required.

## Blockers

Block implementation or release if:

- release requires backend-served console config but no route is documented;
- generated OpenAPI and route docs disagree on a required shape;
- an environment variable or deployment assumption is not documented in source;
- local fixtures are the only evidence for a user-facing backend field.
