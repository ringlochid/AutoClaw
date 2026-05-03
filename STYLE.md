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
- keep backend concerns curated under their owning folders, for example `core/`,
  `schemas/`, `compiler/`, `db/`, `api/`, and `services/`
- do not scatter the same concern across unrelated modules when one owning
  folder can hold it cleanly
- record any phase-bounded exception explicitly in review

## Refactor triggers

- any touched function over **80 non-comment, non-blank lines** must be extracted or carry an explicit review exception
- any touched file over **400 lines** must be reviewed for splitting when responsibilities can be separated without adding cross-module chaos
- any touched file over **600 lines** should not grow further unless a phase-bounded exception is recorded
- mixed-responsibility files should be split once the current phase touches the overlapping responsibilities anyway

## Side effects and transactions

- keep transaction boundaries in service or domain layers, not routes
- keep orchestration in services or domain modules
- keep externally visible side effects behind named functions with narrow call sites
- do not hide network, filesystem, or DB writes inside vague helper stacks

## Python rules

- prefer explicit return types
- prefer explicit typed interfaces and domain models
- prefer `pathlib.Path`
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

- use `DeclarativeBase`, `Mapped[...]`, and `mapped_column()` as the standard declarative mapping style
- keep table-level `Index`, `UniqueConstraint`, and `CheckConstraint` explicit and named where they encode contract or migration truth
- prefer dialect-portable SQLAlchemy types and constraint patterns on runtime and registry tables because the shipped DB lanes include both SQLite and Postgres
- prefer portable enum storage for shipped cross-DB surfaces, for example SQLAlchemy `Enum(..., native_enum=False, create_constraint=True)` or an equivalent explicit string-plus-constraint pattern, unless canon explicitly freezes a Postgres-only enum strategy
- avoid Postgres-only column types or operators such as dialect-native enum-only assumptions, `JSONB`, `ARRAY`, or dialect-specific index/operator behavior on shared runtime paths unless canon explicitly requires them and the review records the reason
- when a dialect-specific DB feature is unavoidable, isolate it behind a narrow persistence boundary and keep both the SQLite smoke lane and the Postgres strong-verification lane explicit in tests and review evidence
- choose relationship loading strategy deliberately on ORM-backed list and fanout paths
- avoid N+1 by default; if a code path can fan out over related objects, choose eager loading up front
- use `selectinload()` by default for collection loading unless joined loading is clearly better for the query shape
- use `joinedload()` only when row explosion and duplication are understood and acceptable
- use `raiseload()` or equivalent guardrails where accidental lazy loads would hide correctness or performance issues
- do not hide business rules inside giant ad-hoc query blocks

Source: [SQLAlchemy declarative mapping](https://docs.sqlalchemy.org/en/20/orm/declarative_styles.html)
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
