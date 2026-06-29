# Console Environment And Runtime Config

Status: Target

This page locks the environment and runtime-configuration contract for the
console frontend.

## Current Decision

Initial console implementation uses build-time Vite environment variables and a
centralized frontend config module. It must not call `/console/config` until a
backend route exists and is documented in API/OpenAPI truth.

`/console/config` remains the target same-origin serving preference from
`control-ui-runtime-and-authoring-surfaces.md`, but it is not a shipped current
route in the router, route map, or generated OpenAPI inspected for this contract
lock.

## Current Variables

`apps/console/.env.example` exposes:

```text
VITE_AUTOCLAW_API_BASE_URL=http://127.0.0.1:18125
VITE_AUTOCLAW_API_KEY=replace-me-with-your-operator-api-key
```

The current `apps/console/src/app/config.ts` behavior is the contract baseline:

- default API base URL is `http://127.0.0.1:18125`
- configured base URL is trimmed
- trailing slashes are removed
- blank API key becomes `null`

The foundation slice may refactor config internals, but it must preserve one
central config owner.

## API Base URL Rules

- All API paths are resolved through the shared API client against one
  normalized base URL.
- Feature pages must not construct absolute API URLs directly.
- Test fixtures may configure a test base URL, but component code must consume
  the same config shape.
- Subpath hosting must be handled deliberately through app/base-path config
  before release; do not assume it from Vite defaults.

## API Key Rules

- The API key is an operator secret.
- The key is sent only through `X-AutoClaw-API-Key`.
- Do not render it in UI.
- Do not include it in query params, screenshots, test names, fixture files,
  logs, markdown evidence, or browser storage.
- Do not copy it into MSW fixtures except as an obvious placeholder when a test
  must assert header presence.
- If the key is absent, API reads and writes should surface access/auth errors
  from the backend rather than pretending data is empty.

## Actor Ref

Some shipped write routes expose optional `X-AutoClaw-Actor-Ref`. The console
must not invent actor identity. Add actor-ref support only when a product
contract names how the current operator identity is obtained.

Until then, action routes may omit actor ref and rely on backend auth context.

## `/console/config` Route Status

Decision: do not implement a frontend dependency on `/console/config` in the
initial slices.

Route status:

- target preference: same-origin runtime config at `/console/config`
- current shipped route: absent
- current OpenAPI: absent
- current implementation blocker: backend/API prerequisite if production
  deployment requires runtime config after build

Affected slices:

- The API/config foundation slice owns centralizing env-based config now.
- A future backend/runtime-config prerequisite owns adding `/console/config`
  and updating OpenAPI if same-origin deploy requires it.
- Page slices must consume the shared config and must not each add fallback
  config behavior.

## Same-Origin Serving Assumptions

Preferred future same-origin shape:

- SPA shell at `/`
- assets at `/assets/*`
- runtime config at `/console/config`
- API and MCP lanes stay on explicit prefixed routes

Initial implementation may run with Vite dev server and an explicit API base
URL. Same-origin production serving is a deployment/runtime slice, not a reason
for page implementations to call missing routes.

## Local Development

Developers should use:

- `make console-install`
- `make console-dev`
- `.env` values copied from `.env.example` with a local operator API key

Do not commit local `.env` secrets.

## Test And Fixture Config

Tests should avoid real API secrets:

- unit/component tests use explicit config objects or MSW.
- integration tests assert that the configured API key is forwarded as a
  placeholder header.
- e2e tests may use a controlled test key only when the test environment starts
  or points at a real API intentionally.

## Release Gate

Before final suite release review, decide whether the target deployment still
uses build-time env config or requires `/console/config`.

If `/console/config` is required, release is blocked until a backend/API slice
adds the route, updates generated OpenAPI or documented config truth, and the
console client consumes it through the shared config owner.
