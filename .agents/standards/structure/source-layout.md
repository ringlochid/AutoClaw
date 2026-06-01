# Source layout standard

Status: Reference

Use this guide when restructuring the repo tree, choosing package roots,
consolidating transport layers, moving provider integrations, or deciding the
steady-state layout for tests and runtime code.

## Goals

- keep one obvious owner for each major source tree
- keep the monorepo organized by product/app, docs, infra, scripts, and
  authored inputs
- keep shipped backend code under one canonical import package
- keep transport surfaces thin and runtime/domain packages owner-driven
- let tests mirror product and boundary ownership rather than redesign history

## Monorepo root rules

The steady-state top level should stay product-oriented:

- `apps/**`: deployable applications and product surfaces
- `definitions/**`: authored workflow/role/policy or similar product inputs
- `docs/**`: public docs
- `docs-internal/**`: internal canon docs
- `infra/**`: deployment, runtime infra, packaging, migrations
- `scripts/**`: repo tooling, docs tooling, and testing helpers

Do not add new top-level directories just to sort code by language, build tool,
or temporary migration state when an existing owner already fits.

## Canonical backend package rule

- shipped backend Python code should converge to one canonical import package
- compatibility import paths may exist during migration, but they must stay
  thin and explicitly temporary
- do not let two long-lived source trees both act like the real backend owner

For AutoClaw, the steady-state direction should be a canonical backend package
such as `autoclaw/**`, not parallel first-class source trees with duplicated
ownership.

## Packaging-aware source root rule

- when packaging/import-path safety matters, prefer a packaging-aware source
  root such as `src/<package>/`
- the `src/` layout is the steady-state default when it helps prevent local
  import leakage and packaging mistakes
- use flat package layout only when the simplicity benefit clearly outweighs
  the import-path risk

For AutoClaw, a strong steady-state target is:

```text
apps/api/
  pyproject.toml
  src/
    autoclaw/
  tests/
```

## Transport-layer thinness

Transport owners exist to expose product surfaces, not to become business-logic
dumps.

- `api/**` should own HTTP parsing, dependency wiring, handler dispatch, and
  response mapping
- `cli/**` should own command parsing, prompting, rendering, and exit-status
  mapping
- transport owners should not become the long-term home of runtime, registry,
  or provider-integration business logic

For AutoClaw, this means CLI code should converge toward one coherent owner such
as:

```text
cli/
  commands/
  output/
  prompts/
  main.py
  root.py
```

instead of splitting durable CLI ownership across several top-level lanes.

## Domain-first backend structure

Prefer bounded-context or product-owner packages before top-level
implementation-mechanic packages.

- split first by domain owner: `dispatch`, `flow`, `checkpoint`, `watchdog`,
  `registry`, `compiler`
- split second by technical role inside that owner when needed: `service.py`,
  `writes.py`, `reads.py`, `recording.py`, `projection.py`
- avoid top-level owner buckets such as `control`, `effects`, or `helpers`
  when one bounded context can hold the same code more coherently

If a reader must hop across `control/`, `effects/`, and `projection/` to follow
one lifecycle, the layout is probably too mechanism-first.

## Integration substrate rule

When an external system grows into a substantial boundary:

- keep reusable integration substrate under a dedicated integration owner
- keep runtime or domain behavior that uses that integration under the runtime
  or domain package that owns the workflow
- keep public packaging or wrapper exposure thin and separate from the runtime
  substrate

Example steady-state pattern:

```text
integrations/
  openclaw/

runtime/
  dispatch/
    openclaw/
```

Do not scatter the same provider boundary across unrelated runtime, CLI, and
wrapper owners without an explicit split.

## Service-layer rule

- keep a `services/**` owner only if it has a precise, consistently applied
  meaning such as use-case orchestration
- do not keep an empty or generic `services/` bucket as a promise of future
  cleanliness
- if orchestration naturally belongs to a bounded context package, keep it
  there instead of inventing a generic service layer

## DB and schema ownership rule

- keep persistence truth under `db/**`
- keep wire/contract truth under `schemas/**`
- avoid parallel contract-model trees unless their semantic role is explicitly
  different from API/runtime schemas

If a runtime-specific contract lane exists, it must explain why it is not just
another schema tree.

## Test-tree rule

- steady-state tests should mirror product, feature, or boundary ownership
- phase-numbered trees are transitional only and should converge toward
  feature-owned lanes over time
- unit, integration, and e2e remain the top-level proof lanes, but the folders
  beneath them should reflect product concepts rather than redesign chronology

Prefer:

```text
tests/
  unit/
    cli/
    compiler/
    registry/
    runtime/
    integrations/
  integration/
    api/
    cli/
    db/
    runtime/
    integrations/
  e2e/
    workflows/
    gateway/
    operator/
```

Avoid keeping `phase2/`, `phase3/`, `phase4a/`, and similar folders as the
long-term primary source of test ownership once the redesign history is no
longer the important axis.

For AutoClaw, this test-tree direction is canonical enough that new structural
test-layout work should follow it by default unless a phase-local migration
exception is recorded.

## AutoClaw steady-state direction

The strongest long-term direction for AutoClaw source layout is:

```text
apps/api/
  pyproject.toml
  src/
    autoclaw/
      api/
      cli/
      compiler/
      registry/
      runtime/
      integrations/
      db/
      schemas/
      platform/
      config.py
      paths.py
      main.py
  tests/
```

Key implications:

- `autoclaw/` becomes the canonical backend package
- `api/` and `cli/` stay thin
- runtime packages become domain-first
- provider integration substrate becomes explicit
- tests converge to feature/domain ownership

## Review checklist

- does each top-level source tree have one obvious owner
- is there one canonical shipped backend package
- are transport layers thin
- is the main runtime layout domain-first rather than mechanism-first
- is provider integration substrate separated from runtime usage
- does the test tree reflect product or feature ownership rather than redesign
  chronology
