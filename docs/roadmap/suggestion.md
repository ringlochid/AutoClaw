# Suggested Implementation Order, Code Placement, and Verification Style

Use this as the **practical working style** for `apps/api` while the runtime migration is in progress.
It combines:

- cutover order
- where logic should live
- style/readability rules
- indexing/reuse guidance
- formatting/type-check/test flow

This is a suggested implementation guide, not a substitute for the architecture contract.

## 1) Recommended cutover order

1. **Lock the target contract**
   - roadmap + architecture agree on the same names and invariants

2. **Additive schema first**
   - add `flows.task_id`, `flows.seed_compiled_plan_id`, `flows.active_flow_revision_id`
   - add `flow_revisions`, `node_attempts`, `context_items`, `context_manifests`
   - add node-attempt scoped checkpoints/approvals

3. **Materialize the new runtime path**
   - create flow-first services/runtime logic that materialize `flow_revision`, `flow_nodes`, and `flow_edges`
   - stop relying on `run -> attempt -> flow` as the ownership model

4. **Move control events to the new truth**
   - checkpoint writes target `node_attempt`
   - approval rows target `flow_id` / `node_attempt_id`
   - add `wait_reason = context`

5. **Wire delegated execution correctly**
   - add `node_sessions`
   - add manifest projection + acknowledgement gate
   - only release real execution after bootstrap succeeds

6. **Switch APIs and read models**
   - move runtime APIs from `runs` to `flows`
   - update operator/read-model surfaces to the new contract

7. **Cut off legacy writes**
   - stop creating/updating legacy `runs`, top-level `attempts`, and run-scoped approvals

8. **Delete dead legacy runtime code**
   - remove compatibility shims, legacy routes, dead indexes, and obsolete assumptions

## 2) Preferred logic placement

### Routes: HTTP boundary only

Put these in `app/api/routes/*`:

- path/query/body parsing
- auth/dependency wiring
- HTTP status handling
- domain-error -> HTTP translation
- transaction boundary (`commit` on successful writes)
- calling presenter helpers

Avoid putting these in routes:

- ORM query logic
- scheduler/runtime decisions
- registry/compiler logic
- nested response assembly
- ad-hoc sorting/reshaping of ORM graphs

Good route shape:

1. accept request
2. call domain/runtime/compiler service
3. translate domain errors
4. commit if needed
5. return presenter/schema output

### Runtime logic: `app/runtime/*`

Put runtime-specific behavior here:

- flow creation/materialization from compiled plans
- revision activation and adoption
- node scheduling / runnable-node resolution
- node-attempt lifecycle
- checkpoint handling
- approval/recovery transitions
- context-manifest bootstrap gating
- delegated session lifecycle rules

This is where the new flow-first execution logic should live.
Do not bury the core runtime model in generic route handlers or random helpers.

### Compiler logic: `app/compiler/*`

Put these here:

- definition validation
- graph normalization
- compile-time lineage resolution
- immutable plan creation / hashing

Compiler code should stay compile-focused.
Do not let runtime mutation logic drift into compiler modules.

### Registry logic: `app/registry/*`

Put these here:

- published version lookup/selection
- registry bootstrap/publish flows
- registry-specific validation and lifecycle rules

### Services: cross-domain orchestration only

Put these in `app/services/*` when the work spans multiple domains or when you need a thin composition layer above runtime/compiler/registry modules.

Good fits:

- combining registry + compiler + runtime startup flow
- reusable read loaders used by multiple routes
- migration-bridge helpers during cutover

Avoid turning `app/services/*` into a dumping ground for all business logic.
If logic clearly belongs to runtime/compiler/registry, keep it there.

### Presenters: ORM/domain -> API response shape

Put these in `app/api/presenters/*`:

- ORM/domain -> Pydantic read model conversion
- nested response shaping
- ordered API view assembly
- API-only view reshaping

Keep presenter logic out of services where possible.
That keeps services reusable outside HTTP.

### Schemas: contracts only

Put these in `app/schemas/*`:

- request models
- response models
- nested DTOs
- validation constraints for the API/domain boundary

Prefer explicit typed nested models over large raw `dict[str, Any]` payloads when the shape is known.
That gives better:

- Pylance/Pyright support
- navigation
- refactor safety
- readability

### Models: persistence structure only

Put these in `app/db/models/*`:

- table structure
- relationships
- intrinsic ordering that is broadly useful
- index declarations that match real query shapes

Do not put service orchestration or response-shaping logic in ORM models.

### Dependencies: injection only

Put these in `app/api/deps.py` or similar:

- DB session injection
- auth/session injection
- request-scoped resource helpers

Avoid putting domain decisions in dependencies.

### Core / integrations

- `app/core/*` = shared enums, typed errors, config, small cross-cutting helpers
- `app/integrations/*` = provider/client boundaries and transport adapters

## 3) Reusable logic rules

Prefer a small number of good reusable helpers over duplicated route logic.

Good reusable targets:

- compiled-plan materialization helpers
- flow/revision/node graph loaders
- checkpoint append/update helpers
- approval resolution helpers
- context-manifest projection helpers
- presenter conversion helpers

Prefer reusable functions that return:

- ORM models
- typed domain values
- small dataclasses / typed tuples when needed

Avoid returning API response schemas from deep runtime/compiler code unless the code is explicitly in the presenter layer.

## 4) Readability and style choices

### Prefer explicit names over cute abstraction

Good code here should be easy to read in VS Code/Pylance, easy to grep, and easy to step through in a debugger.

Prefer:

- explicit function names
- typed parameters and returns
- small functions with one job
- obvious module ownership
- domain errors instead of anonymous `ValueError` blobs

Avoid:

- giant route handlers
- giant presenter functions with nested raw dict assembly
- helper layers that hide simple queries without adding meaning
- premature abstraction that makes the runtime harder to trace

### Prefer typed schema conversion

For direct ORM -> read-schema conversion, prefer `model_validate(...)` when the schema aligns with the model.
For nested/composed responses, prefer explicit presenter functions that build typed nested schemas.

Use `model_dump(...)` mainly for:

- persisted snapshots
- structured hashing payloads
- externalized config/state blobs

### Shared enum placement

Keep shared/domain enums in `app/core/enums.py` when they are used by models, schemas, services, and runtime/compiler logic.
Only split HTTP-only enums into a separate module if they are truly transport-specific.

## 5) Index and ordering guidance

Indexes should follow real read/write patterns, not guesswork.

### Put index definitions in the persistence layer

- declare stable schema-level indexes in ORM models / migrations
- do not treat ad-hoc `sorted(...)` calls in routes as a substitute for good relational design

### Prefer indexes for real query paths

Good candidates are list/history lookups such as:

- flow by task / active revision / status
- attempts by flow + node + number/time
- checkpoints by attempt + sequence
- approvals by flow / node / status
- context items by scope / flow / node / status
- manifests by node-attempt / status

### Prefer intrinsic ordering on relationships when broadly useful

If a relation is almost always read in one natural order, prefer `order_by=...` on the relationship rather than repeatedly sorting in service/route code.

### Do not add caches first

Prefer clean relational queries + the right indexes before introducing denormalized caches.
Only add caches after profiling proves they are needed.

## 6) Formatting, linting, and type checking

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

Use either:

```bash
make typecheck-api
make pyright-api
```

or the bundled pass:

```bash
make check-api
```

Roles:

- `mypy` = stricter repo type discipline
- `pyright` / Pylance = editor-grade structural/type inference check

Notes:

- `apps/api/pyrightconfig.json` is the preferred config entrypoint for Pyright/Pylance
- in VS Code Remote SSH, Pylance should follow the repo interpreter/venv
- `make pyright-api` is the preferred repo entrypoint for Pyright
- `make check-api` is the preferred bundled quality gate before tests

## 7) Tests and smoke validation

### Fast tests

```bash
make test-api
```

### Real DB / integration tests

```bash
make test-api-db
```

Use this for registry/compiler/runtime persistence changes.

### Runtime smoke validation

When changing runtime or HTTP behavior materially, prefer an extra smoke pass:

```bash
make docker-up
```

Then exercise the key path manually.
During migration, test both:

- current legacy runtime path if it still exists
- new flow-first path once introduced

Finally:

```bash
make docker-down
```

## 8) Suggested flow before testing

Recommended order for normal API work:

1. edit/refactor locally
2. format first — `make format-api`
3. run bundled checks — `make check-api`
4. run fast unit tests — `make test-api`
5. run DB/integration tests if runtime/compiler/API persistence changed — `make test-api-db`
6. run docker smoke if endpoint/runtime behavior changed materially

This order usually catches the cheapest failures first:

- formatting drift
- lint issues
- Pylance/Pyright/mypy-visible type problems
- unit regressions
- real DB/runtime integration regressions

## 9) Review checklist

Before stopping, check:

- are routes thin?
- does runtime logic live in `app/runtime/*` instead of routes?
- does compile logic live in `app/compiler/*`?
- does registry logic live in `app/registry/*`?
- are presenters doing response shaping instead of services?
- are response shapes typed instead of built from large raw dicts?
- are indexes/ordering handled in the persistence layer where sensible?
- is reusable logic extracted at the right layer instead of copy-pasted?
- did `make check-api` pass?
- if typing/debugging got weird, did both `mypy` and `pyright` pass individually?
- did real DB tests pass for persistence/runtime work?

## 10) Short version

- **routes** = HTTP only
- **runtime** = execution state transitions and scheduler logic
- **compiler** = compile/validate/normalize
- **registry** = published-definition lifecycle
- **services** = cross-domain orchestration only
- **presenters** = response shaping
- **schemas** = contracts
- **models** = persistence + intrinsic ordering/indexes
- **deps** = injection only
- **format/check/test order** = format -> check-api -> unit -> DB -> smoke
