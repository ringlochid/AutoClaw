# AutoClaw coding standards

Status: Reference

This file holds the repo-wide measurable engineering rules for touched code.
Keep it short. Put long-form examples and cleanup playbooks in
`.agents/standards/*`.

## Core engineering rules

- prefer explicit domain names over generic helpers
- keep side effects visible and centralized
- keep current truth and target truth separate
- delete stale abstractions instead of carrying them forward as ghosts
- remove dead code, duplicated logic, and unaccessed private helpers in touched owned surfaces unless a phase-bounded exception is recorded
- group backend concerns under clear owners such as `api/`, `compiler/`, `core/`, `db/`, `registry/`, `runtime/`, `schemas/`, and `services/`
- do not scatter one concern across unrelated modules when a named owner can hold it cleanly
- reserve underscore-prefixed top-level names for module-local implementation only
- when another module imports the helper, promote it to a public shared surface or move it into a named shared module
- record any phase-bounded exception explicitly in review

## Refactor triggers

- any touched function over **80** non-comment, non-blank lines must be extracted or carry an explicit review exception
- any touched file over **400** lines must be reviewed for splitting when responsibilities can separate cleanly
- any touched file over **600** lines should not grow further without a phase-bounded exception
- mixed-responsibility files should be split once the current slice touches the overlapping concerns anyway
- any touched compatibility shim, redundant branch, or duplicated logic path must be removed or carry an exact contract reason

## Module layout and naming

- keep one dominant responsibility per module
- when a second responsibility becomes reusable or independently testable, extract it into a sibling module or package named for that responsibility
- when three or more sibling files share the same family stem, stop growing the flat family and extract a responsibility-named package or support module
- in `apps/api/tests/**`, ignore the required `test_` prefix when evaluating family stems
- avoid new generic names such as `utils.py`, `helpers.py`, `misc.py`, `common.py`, or `support.py` when the responsibility can be named directly
- keep top-level shared surfaces explicit: shared helpers, adapters, selectors, and mappers should be public and non-underscored
- keep only explicit public-boundary exceptions flat: real `__init__.py` package surfaces, thin `cli.py` entrypoints, and required `conftest.py` discovery surfaces
- do not keep long-lived compatibility wrappers, import-only shims, or placeholder-only tracked trees as steady-state layout

Extended guidance: `.agents/standards/repo-layout.md`

## Top-level function structure

- keep imports first, then constants, type aliases, and exported contracts
- place public entrypoints and shared helpers before module-local helpers
- order functions from high-level orchestration to lower-level helpers
- keep helper families adjacent to the entrypoint or responsibility block they support
- do not interleave unrelated helper groups

## Side effects and transactions

- keep transaction boundaries in service or domain layers, not routes
- keep orchestration in services, domain modules, or clearly named runtime packages
- keep externally visible side effects behind named functions with narrow call sites
- do not hide network, filesystem, or DB writes inside vague helper stacks

## Python rules

- prefer explicit return types
- prefer explicit typed interfaces and domain models
- prefer `pathlib.Path`
- treat `scripts/docs/*` as ordinary Python code with lint and typing gates when touched
- keep externally visible Pydantic models explicit and version-current
- prefer Pydantic `BaseModel` over stdlib `dataclass` for controller-owned schema, compiler, presenter, and readback contracts
- keep SQLAlchemy usage explicit, typed, and in 2.x declarative style

## FastAPI rules

- routes should only do parsing, dependency injection, service calls, response mapping, and HTTP translation
- do not bury runtime, prompt, artifact, compiler, or registry business rules inside routes
- prefer `route -> service -> presenter/schema` separation
- do not introduce vague generic `handler` layers unless canon names a concrete responsibility they own
- use `async def` only when the code actually awaits non-blocking I/O
- use plain `def` for sync libraries that do not support `await`
- do not wrap blocking DB or API code in fake async just to make the signature look modern

Source: [FastAPI async docs](https://fastapi.tiangolo.com/async/)

## Pydantic v2 rules

- prefer `model_config = ConfigDict(...)` over deprecated `class Config`
- use `model_validate()` and `model_dump()` instead of v1 parse or dict helpers
- keep aliasing, `populate_by_name`, and `from_attributes` explicit where contracts depend on them
- use `frozen=True` on immutable contract models when callers should not mutate validated objects
- keep write models strict with `extra="forbid"` unless canon intentionally defines an open payload
- keep readback models explicit about where `extra="allow"` is intentional

Source: [Pydantic configuration](https://docs.pydantic.dev/latest/concepts/config/)

## SQLAlchemy rules

- use `DeclarativeBase`, `Mapped[...]`, and `mapped_column()` as the standard declarative mapping style
- keep table-level `Index`, `UniqueConstraint`, and `CheckConstraint` explicit and named when they encode contract or migration truth
- on new or touched relationships, prefer explicit paired `relationship(..., back_populates=...)` attributes over new `backref`
- when a relationship has multiple foreign key paths or self-reference ambiguity, set `foreign_keys=` or `remote_side=` explicitly
- when a mapped relationship already exists on a touched path, prefer relationship-based navigation and relationship-aware joins/loaders over hand-stitched foreign-key logic unless the query is intentionally aggregate-shaped
- persist canonical controller relationships as real relational links with DB-enforced integrity rather than parallel string or JSON echoes
- prefer dialect-portable types and constraint patterns on shared SQLite/Postgres runtime paths
- use child tables instead of JSON columns for authoritative relational runtime truth
- reserve JSON columns for secondary structured snapshots, authored bodies, debug material, or projections whose source of truth is explicit elsewhere
- choose relationship loading strategy deliberately and avoid N+1 by default
- use `selectinload()` by default for collection loading unless joined loading is clearly better for the query shape
- use `joinedload()` only when row explosion is understood and acceptable
- use `raiseload()` or equivalent guardrails where accidental lazy loads would hide correctness or performance problems

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

## Docs structure rule

- separate public product/operator docs, public reference/internals docs, and internal canon docs
- prefer `design/` over `redesign/` in steady-state internal naming
- keep internal canon under `docs-internal/**` in the steady state
- version internal canon explicitly with directories such as `v1/`, `v2/`, and `vnext/`
- keep public docs versionless by default unless multiple supported public product versions must coexist
- do not treat `docs/redesign`, `docs/current`, `docs/execution`, and `docs/archive` as the final public information architecture
- keep stable implementation-heavy reference in a dedicated internals or maintainer lane, not in onboarding or general concept pages
- keep design truth, current contrast, execution records, and archive material in internal canon paths until explicit replacements exist

Extended guidance: `.agents/standards/docs-structure.md`

## Standards map

Use these long-form guides when the work includes structural cleanup:

- `.agents/standards/repo-layout.md`
- `.agents/standards/readability-refactor.md`
- `.agents/standards/test-structure.md`
- `.agents/standards/docs-structure.md`
- `.agents/standards/integration-boundaries.md`

## Review exception rule

If a touched surface cannot meet these standards inside the current phase:

- record the exact exception
- explain why it is phase-bounded
- name the owning later phase or work package
- do not leave the deviation as an unexplained convenience shortcut
