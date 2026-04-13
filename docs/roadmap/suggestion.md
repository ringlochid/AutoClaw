# Suggested Code Placement, Style, and Verification Flow

This is not a hard policy file. It is the **current suggested working style** for the `apps/api` codebase based on the Phase 1 cleanup pass.

## 1) Preferred logic placement

### Routes: HTTP boundary only

Put these in `app/api/routes/*`:

- request/response wiring
- path/query/body parsing
- HTTP status codes
- `HTTPException` translation
- transaction boundary (`await session.commit()`) for successful writes
- calling presenter helpers for API read models

Try **not** to put these in routes:

- DB query logic
- orchestration logic
- nested response assembly
- domain decisions
- ad-hoc sorting/reshaping of ORM data

Good route shape:

1. accept request
2. call service
3. translate domain errors to HTTP errors
4. commit if needed
5. return presenter/schema output

---

### Services: business logic + persistence orchestration

Put these in `app/services/*`:

- DB reads/writes
- orchestration across models
- compiler/runtime/registry logic
- reusable creation helpers
- relationship loading for downstream presentation

Preferred service return types:

- ORM models
- tuples of ORM models for orchestration paths
- simple domain-oriented values

Avoid returning API response schemas from services when possible.
That keeps services reusable outside HTTP.

Examples from current preferred style:

- `start_run_from_workflow(...)` returns models
- `get_run_with_relations(...)` loads the object graph
- `create_flow_nodes_for_compiled_plan(...)` handles flow-node materialization

---

### Presenters: ORM/domain -> API response shape

Put these in `app/api/presenters/*`:

- ORM model -> Pydantic read model conversion
- nested response shaping
- ordered API view assembly
- any transformation that exists mainly for API output

This layer is the right place for:

- `to_compiled_plan_read(...)`
- `to_run_inspect_response(...)`
- `to_run_start_response(...)`

This keeps routes thin and prevents service code from drifting into HTTP-schema assembly.

---

### Schemas: request/response contracts only

Put these in `app/schemas/*`:

- request models
- response models
- nested read/write DTOs
- validation constraints for API/domain boundaries

Prefer explicit nested read models over raw `dict[str, Any]` in response construction when the shape is known.
That gives better:

- Pylance/Pyright support
- reuse
- editor navigation
- refactor safety

---

### Models: persistence structure only

Put these in `app/db/models/*`:

- table structure
- relationships
- stable relationship ordering where it is intrinsic and broadly useful

If the API always wants a stable order, prefer adding `order_by=...` on the ORM relationship rather than repeatedly calling `sorted(...)` in routes/services.

Examples that fit well here:

- attempts ordered by `number`
- compiled plan nodes/edges ordered by `order_index`
- flow nodes ordered by `iteration_index`

---

### Dependencies: injection only

Put these in `app/api/deps.py` or similar:

- `DbSession`
- auth/session injection
- request-scoped helpers

Avoid putting business logic in dependencies.
A dependency should mostly provide a resource, not make domain decisions.

## 2) Preferred conversion style

### Prefer `model_validate(...)` for ORM -> read schema

For direct ORM-to-read-schema conversion, prefer:

- `TaskRead.model_validate(task)`
- `ApprovalRead.model_validate(approval)`
- `CompiledPlanNodeRead.model_validate(node)`

This is cleaner than hand-copying fields when the schema matches the model closely.

### Prefer explicit presenter helpers for nested responses

For nested or combined responses, prefer presenter functions that build typed nested models.

Preferred:

- build `RunInspectAttemptRead`, `RunInspectFlowRead`, `RunInspectFlowNodeRead`
- return one final `RunInspectResponse`

Avoid building large nested `list[dict[str, Any]]` payloads when the structure is known.
That was one of the main causes of the Pylance/Pyright complaints during cleanup.

### Use `model_dump(...)` mainly for persisted snapshots or externalized structured data

`model_dump(...)` is still the right fit when:

- persisting normalized snapshots
- computing hashes from structured data
- serializing seed/config content for storage

Less ideal use:

- ad-hoc route response assembly for known typed responses

## 3) Enum placement

### Keep shared/domain enums in `app/core/enums.py`

Current runtime/registry enums belong there because they are shared by:

- DB models
- schemas
- services
- compiler/runtime logic

Examples:

- `RunStatus`
- `AttemptStatus`
- `FlowStatus`
- `WorkflowMode`
- `ApprovalStatus`

### Only add `api_enums.py` if the enum is HTTP-only

Create a separate API-specific enum module only if values are specific to transport concerns, for example:

- query sort order
- filter mode aliases
- request-only display variants
- response formatting toggles that should not leak into domain logic

Right now, a separate `api_enums.py` is **not recommended** because there is no clear HTTP-only enum set yet.

## 4) Suggested tools

### Formatting

Use:

```bash
make format-api
```

Current formatter:

- `ruff format`

### Linting

Use:

```bash
make lint-api
```

Current linter:

- `ruff check`

### Type checking

Use either the explicit commands:

```bash
make typecheck-api
make pyright-api
```

or the combined pre-test quality pass:

```bash
make check-api
```

Current roles:

- `mypy` = stricter repo type discipline
- `pyright`/Pylance = editor-grade structural/type inference check

Notes:

- `apps/api/pyrightconfig.json` is the preferred config entrypoint for Pyright/Pylance
- in VS Code Remote SSH, Pylance should follow the repo interpreter/venv
- `make pyright-api` is the preferred repo entrypoint for Pyright
- `make check-api` is the preferred bundled quality gate before running tests

### Unit tests

Use:

```bash
make test-api
```

### Real DB / integration tests

Use:

```bash
make test-api-db
```

This is the preferred verification path for registry/compiler/runtime changes.

### Runtime smoke validation

When changing HTTP/runtime behavior, prefer an extra smoke pass:

```bash
make docker-up
```

Then manually exercise the key path, e.g.:

- `/readyz`
- `/registry/bootstrap`
- `/workflows/{workflow_key}/compile`
- `/runs/from-workflow/{workflow_key}`
- `/runs/{run_id}`
- `/runs/checkpoints`

Finally:

```bash
make docker-down
```

## 5) Suggested flow before testing

Recommended order for normal API work:

1. **edit/refactor locally**
2. **format first**
   - `make format-api`
3. **run the bundled pre-test checks**
   - `make check-api`
4. **run fast unit tests**
   - `make test-api`
5. **run real DB integration tests if DB/runtime/API/compiler logic changed**
   - `make test-api-db`
6. **run docker smoke if endpoint behavior or compose runtime behavior changed materially**

This order is preferred because it catches:

- formatting drift
- obvious lint issues
- editor/type problems
- unit regressions
- real Postgres/runtime integration regressions

in that order, which is usually the cheapest path.

## 6) Suggested review checklist

Before considering a change clean enough to stop:

- are routes thin?
- is business logic in services instead of routes/dependencies?
- is API response shaping in presenters rather than services?
- are read responses typed instead of large nested raw dicts?
- is stable ordering pushed into ORM relationships where sensible?
- are enums in the right layer?
- did `make check-api` pass?
- if type debugging got weird, did both `mypy` and `pyright` pass individually?
- did real DB tests pass for persistence/runtime work?

## 7) Suggested next improvements

These are not applied yet, but they are the next sensible cleanup/quality steps:

- add CI for `lint-api`, `typecheck-api`, `pyright-api`, `test-api`, and `test-api-db`
- introduce typed domain exceptions instead of using `ValueError` for not-found/conflict cases
- add small presenter-focused tests and more explicit API error-path tests
- add a scripted runtime smoke path for bootstrap -> compile -> run -> checkpoint -> approval
- review additional indexes as new list/history/query endpoints land

## 8) Current preferred summary

Short version:

- **routes** = HTTP only
- **services** = domain + DB orchestration
- **presenters** = response shaping
- **schemas** = contracts
- **models** = persistence + stable ordering
- **deps** = injection only
- **enums** = keep shared ones in `app/core/enums.py`
- **checks before tests** = format -> check-api -> unit -> DB -> smoke
