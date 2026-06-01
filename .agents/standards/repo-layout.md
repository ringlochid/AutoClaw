# Repo layout standard

Status: Reference

Use this guide when the work includes moving files, splitting packages,
renaming families, or cleaning flat tree sprawl.

## Goals

- keep one dominant responsibility per directory and module family
- make ownership obvious from the path alone
- keep long-lived shared surfaces named and intentional
- stop repeating prefix families once a named package can own the concern
  cleanly
- keep public docs, public reference docs, and internal canon docs distinct in
  both naming and layout

## Root map

- `apps/api/app/**`: shipped backend code and internal runtime/controller
  surfaces
- `apps/api/tests/**`: unit, integration, and e2e proof for backend behavior
- `apps/console/**`: frontend and console-specific build/test surfaces
- `definitions/**`: authored workflow, role, and policy inputs
- `docs/**`: public product, operator, reference, and help docs
- `docs-internal/design/**`: target design truth, versioned by product era
- `docs-internal/current/**`: shipped-behavior contrast, versioned by product era
- `docs-internal/execution/**`: implementation routing, plans, evidence, and
  reviews, versioned by owning program or product era
- `docs-internal/archive/**`: historical material only
- `docs-internal/adr/**`: durable accepted decisions
- `scripts/docs/**`: docs and prompt tooling
- `scripts/testing/**`: test runners and support scripts
- `.agents/standards/**`: agent-only long-form standards

## Package extraction rules

- if three or more sibling files share the same family stem, extract a package
  or support module named for the real responsibility
- if one file mixes unrelated concerns and the current slice touches both,
  split it now instead of adding more branches
- if a shared helper is imported across modules, move it into a named shared
  module instead of importing another module's local implementation
- if a path already names the responsibility cleanly, prefer extending that
  owner over adding a parallel directory

## Naming rules

- prefer names that expose the domain concern directly
- avoid placeholder names such as `utils`, `helpers`, `misc`, `common`,
  `support`, or `wrapper` unless the directory truly owns that narrow concern
- avoid version suffixes or temporary migration names in steady-state code
  paths
- use version directories, not filename suffixes, for versioned internal docs
- keep public shared helpers non-underscored
- keep test filenames aligned with the feature or contract they verify, not
  with incidental helper names

## Backend layout guidance

- keep route surfaces under `apps/api/app/api/**`
- keep CLI entrypoints and noun-family orchestration under
  `apps/api/app/cli/**` and `apps/api/app/cli_commands/**`
- keep persistence and ORM models under `apps/api/app/db/**`
- keep controller-owned schemas under `apps/api/app/schemas/**`
- keep compile-time workflow logic under `apps/api/app/compiler/**`
- keep runtime orchestration under `apps/api/app/runtime/**`
- keep business logic and cross-route orchestration under
  `apps/api/app/services/**`
- keep registry lookup and definition-truth surfaces under
  `apps/api/app/registry/**`

## Test layout guidance

- keep unit, integration, and e2e surfaces separate
- do not let helper-heavy test families hide what lane they belong to
- if an integration or e2e family grows into several concerns, extract
  subpackages by responsibility rather than by repeated filename prefixes

## Docs layout guidance

- do not place product truth in `.agents/standards/**`
- do not place execution evidence in public docs or shipped-behavior contrast
  pages
- do not use archive pages as living source of truth
- keep public docs under `docs/**`
- keep internal canon under `docs-internal/**`
- use `design/` rather than `redesign/` in steady-state internal naming
- make internal version eras explicit with directories such as `v1/`, `v2/`,
  and `vnext/`
- do not use the public docs tree as a catch-all for versioned implementation
  programs, historical design drafts, or execution artifacts

## Local instruction files

If local guidance becomes necessary later, the first candidates should be:

- `apps/api/app/AGENTS.md`
- `apps/api/tests/AGENTS.md`
- `docs/AGENTS.md`
- `docs-internal/AGENTS.md`

Add them only when a subtree genuinely needs different local routing or
validator rules.
