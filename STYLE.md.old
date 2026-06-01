# AutoClaw coding standards

Status: Reference

This file is the canonical coding-standard surface for repo code touched during
the redesign landing. Treat it as a frozen implementation-control surface after
Phase 0.

## Core engineering rules

- prefer explicit domain names over generic helpers
- keep side effects visible and centralized
- keep current truth and target truth separate
- delete stale abstractions instead of carrying them forward as ghosts
- remove dead code and duplicated logic when the owning phase reopens that
  responsibility; do not keep unused private helpers as speculative future
  hooks by default
- keep backend concerns curated under their owning folders, for example `core/`, `schemas/`, `compiler/`, `db/`, `api/`, and `services/`
- do not scatter the same concern across unrelated modules when one owning file/folder can hold it cleanly
- reserve underscore-prefixed top-level names for module-local implementation
  only; if another module imports the helper, promote it to a public name or
  move it into a named shared module
- record any phase-bounded exception explicitly in review

## Refactor triggers

- any touched function over **80 non-comment, non-blank lines** must be extracted or carry an explicit review exception
- any touched file over **400 lines** must be reviewed for splitting when responsibilities can be separated without adding cross-module chaos
- any touched file over **600 lines** should not grow further unless a phase-bounded exception is recorded
- mixed-responsibility files should be split once the current phase touches the overlapping responsibilities anyway
- any touched unaccessed private helper, redundant branch, or duplicated logic
  path must be removed or carry an explicit review exception with an exact
  framework or contract reason

## Module layout rules

- apply responsibility-oriented grouping across `apps/**`, `apps/api/tests/**`,
  and `scripts/docs/**`; do not leave one concern spread across a flat sibling
  family once a named package can own it cleanly
- when three or more sibling files share the same family stem, stop growing the
  family through repeated prefixes alone and extract a responsibility-named
  package or support module instead
- in `apps/api/tests/**`, ignore the required `test_` prefix when evaluating
  the family stem so families such as `test_phase3_runtime_*` still trigger the
  split rule
- keep one dominant responsibility per module; when a second responsibility
  becomes reusable or independently testable, extract it into a sibling module
  or subpackage named for that responsibility
- if multiple modules need the same helper, move it into a
  responsibility-named shared module instead of importing another module's
  local implementation surface
- keep only explicit public-boundary exceptions flat: stable high-fan-in
  modules, real package-barrel `__init__.py` surfaces, thin `cli.py`
  entrypoints, and required `conftest.py` discovery surfaces
- avoid new generic module names such as `utils.py`, `helpers.py`, or `misc.py`
  when the shared responsibility can be named directly
- keep top-level shared surfaces explicit: cross-module helpers, adapters,
  selectors, or mappers must use public non-underscored names
- do not keep long-lived compatibility wrappers, import-only shim modules, or
  star-import collector modules as steady-state layout; allow them only as
  exact phase-bounded migration exceptions recorded in review
- do not add placeholder-only tracked trees or packages that carry no real
  owned implementation, tests, or tooling

## Top-level function ordering rules

- keep imports first, then constants, type aliases, and exported contracts
  before the functions that rely on them
- place public entrypoints and public/shared helpers before module-local
  helpers
- order functions from highest-level orchestration to lower-level helpers so
  the primary control flow reads top-down
- keep helper families adjacent to the entrypoint or responsibility block they
  support; do not interleave unrelated helper groups

## Side effects and transactions

- keep transaction boundaries in service or domain layers, not routes
- keep orchestration in services or domain modules
- keep externally visible side effects behind named functions with narrow call sites
- do not hide network, filesystem, or DB writes inside vague helper stacks

## Python rules

- prefer explicit return types
- prefer explicit typed interfaces and domain models
- prefer `pathlib.Path`
- treat docs tooling under `scripts/docs/*` as ordinary Python code and keep
  its lint and typing gates explicit when touched
- keep externally visible Pydantic models explicit and version-current
- prefer Pydantic `BaseModel` over stdlib `dataclass` for controller-owned
  schema, compiler, presenter, and readback contract surfaces
- use Pydantic v2 model APIs such as `ConfigDict`, `model_validate()`, `model_dump()`, `field_validator`, and `model_validator`
- use `from_attributes=True` explicitly on ORM-backed read models instead of relying on implicit behavior
- when translating one typed object surface into another Pydantic contract,
  prefer `model_validate(..., from_attributes=True)` over wide field-by-field
  constructor calls when the source can be expressed as attributes cleanly
- keep SQLAlchemy usage explicit, typed, and in 2.x declarative style

## FastAPI rules

- routes should only do parsing, dependency injection, service calls, response mapping, and HTTP translation
- do not bury runtime, prompt, artifact, compiler, or registry business rules inside routes
- prefer `route -> service -> presenter/schema` separation for backend request handling
- do not introduce a vague generic `handler` layer unless canon names a concrete responsibility that cannot live in routes, services, or presenters
- use `async def` only when the code actually awaits non-blocking I/O
- use plain `def` for sync libraries that do not support `await`
- do not wrap blocking DB or API code in fake async just to make the route signature look modern

Source: [FastAPI async docs](https://fastapi.tiangolo.com/async/)

## Pydantic v2 rules

- prefer `model_config = ConfigDict(...)` over deprecated `class Config`
- use `model_validate()` / `model_dump()` instead of v1 parse or dict helpers
- keep aliasing, `populate_by_name`, and `from_attributes` explicit where contracts depend on them
- use `frozen=True` on immutable contract models when callers should not mutate
  the validated object after construction
- keep write models strict with `extra="forbid"` unless canon intentionally defines an open payload
- keep read models and audit/readback models explicit about where `extra="allow"` is intentional

Source: [Pydantic configuration](https://pydantic.dev/docs/validation/latest/concepts/config/)

## SQLAlchemy rules

- use relationships, mapped column, constraints and index(B-tree/GIN) when defining using sqlalchemy
- use trigram or vector for full text search(should consider compatibility with sqllite)
- use enum when possible for kind/state/type and similar data
- use `DeclarativeBase`, `Mapped[...]`, and `mapped_column()` as the standard declarative mapping style
- apply the relationship-modernization rules below to new or touched mapped edges and the query paths that primarily traverse them; do not churn untouched legacy mappings only for style alignment
- on new or touched mapped relationships, declare the `relationship()` attribute with an explicit `Mapped[...]` type on each side that the owned slice maintains
- on new or touched bidirectional relationships, prefer explicit paired `relationship(..., back_populates=...)` attributes; do not introduce new `backref` unless a bounded review exception records why preserving the legacy pattern is safer in that slice
- when a relationship has multiple foreign key paths, set `foreign_keys=` explicitly; when a self-referential relationship depends on local-vs-remote disambiguation, set `remote_side=` explicitly instead of relying on inference
- when a mapped relationship already exists on a touched path, prefer relationship-based navigation and relationship-aware joins/loaders over hand-stitching the same edge back together from foreign key columns, unless the query is intentionally aggregate- or report-shaped
- when canon names a relation, lineage owner, currentness owner, or graph edge as authoritative controller truth, persist it as a real relational link with DB-enforced integrity rather than a parallel string or JSON echo
- keep table-level `Index`, `UniqueConstraint`, and `CheckConstraint` explicit and named where they encode contract or migration truth
- prefer dialect-portable SQLAlchemy types and constraint patterns on runtime and registry tables because the shipped DB lanes include both SQLite and Postgres
- prefer portable enum storage for shipped cross-DB surfaces, for example SQLAlchemy `Enum(..., native_enum=False, create_constraint=True)` or an equivalent explicit string-plus-constraint pattern, unless canon explicitly freezes a Postgres-only enum strategy
- avoid Postgres-only column types or operators such as dialect-native enum-only assumptions, `JSONB`, `ARRAY`, or dialect-specific index/operator behavior on shared runtime paths unless canon explicitly requires them and the review records the reason
- when a dialect-specific DB feature is unavoidable, isolate it behind a narrow persistence boundary and keep both the SQLite smoke lane and the Postgres strong-verification lane explicit in tests and review evidence
- use child tables instead of JSON columns when the data is authoritative relational runtime truth such as graph membership, dependency edges, surfaced refs, lineage, or currentness that must be queryable and enforceable
- reserve JSON columns for secondary structured snapshots, authored bodies, debug material, or projections whose source of truth is still explicit elsewhere
- choose relationship loading strategy deliberately on new or touched ORM-backed list and fanout paths
- avoid N+1 by default; if a touched code path can fan out over related objects, choose eager loading up front
- use `selectinload()` by default for collection loading unless joined loading is clearly better for the query shape
- use `joinedload()` only when row explosion and duplication are understood and acceptable
- use `raiseload()` or equivalent guardrails where accidental lazy loads would hide correctness or performance issues
- do not hide business rules inside giant ad-hoc query blocks
- do not read canonical definition, registry, or runtime authority from repo files once that authority is assigned to controller-owned DB truth

Source: [SQLAlchemy declarative mapping](https://docs.sqlalchemy.org/en/20/orm/declarative_styles.html)
Source: [SQLAlchemy basic relationships](https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html)
Source: [SQLAlchemy backref guidance](https://docs.sqlalchemy.org/en/20/orm/backref.html)
Source: [SQLAlchemy join conditions](https://docs.sqlalchemy.org/en/20/orm/join_conditions.html)
Source: [SQLAlchemy relationship loading](https://docs.sqlalchemy.org/en/21/orm/queryguide/relationships.html)

## TypeScript, React, and plugin rules

- keep typed TS surfaces explicit
- avoid implicit-any drift and vague glue modules
- keep React and plugin modules cohesive and low-responsibility
- keep build and test behavior aligned with repo-native scripts

## Review exception rule

If a touched surface cannot meet these standards inside the current phase:

- record the exact exception
- explain why the exception is phase-bounded
- name the owning later work package or phase
- do not leave the deviation as an unexplained convenience shortcut
