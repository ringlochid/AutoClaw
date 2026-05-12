# Phase 0 Structural Debt Canon and Audit Proof Evidence

Status: Reference

selected phase: Phase 0
current phase page: docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md
selected work packages: P0-WP2, P0-WP3
summary-only: no
delegated slices: listed
slice id: phase0-canon-audit-rules
slice type: edit
owned surfaces: AGENTS.md, STYLE.md, docs/execution/gates/mandatory-review-gate.md, docs/execution/maps/file-priority-map.md, docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md, docs/execution/plans/phase-0-closeout-grammar-and-proof.md, docs/execution/evidence/phase-0-closeout-grammar-and-proof.md, docs/execution/reviews/phase-0-closeout-grammar-and-proof.md
touched surfaces: AGENTS.md, STYLE.md, docs/execution/gates/mandatory-review-gate.md, docs/execution/maps/file-priority-map.md, docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md, docs/execution/plans/phase-0-closeout-grammar-and-proof.md, docs/execution/evidence/phase-0-closeout-grammar-and-proof.md, docs/execution/reviews/phase-0-closeout-grammar-and-proof.md
slice id: phase0-docs-freeze-entrypoint-split
slice type: edit
owned surfaces: scripts/docs/docs_freeze/**, scripts/docs/markdown_format/**
touched surfaces: scripts/docs/docs_freeze/**, scripts/docs/markdown_format/**
slice id: phase0-prompt-catalog-and-audit-tool-entrypoint-split
slice type: edit
owned surfaces: scripts/docs/prompt_catalog/**, scripts/docs/style_audit/**
touched surfaces: scripts/docs/prompt_catalog/**, scripts/docs/style_audit/**
slice id: phase0-structural-debt-audit
slice type: review-only
owned surfaces: none
touched surfaces: none
slice id: phase0-docs-freeze-second-split
slice type: edit
owned surfaces: scripts/docs/docs_freeze/**, scripts/docs/markdown_format/**
touched surfaces: scripts/docs/docs_freeze/**, scripts/docs/markdown_format/**
slice id: phase0-prompt-catalog-and-audit-tool-second-split
slice type: edit
owned surfaces: scripts/docs/prompt_catalog/**, scripts/docs/style_audit/**
touched surfaces: scripts/docs/prompt_catalog/**, scripts/docs/style_audit/**
slice id: phase0-docs-tool-package-refactor
slice type: edit
owned surfaces: scripts/docs/docs_freeze/**, scripts/docs/prompt_catalog/**, scripts/docs/style_audit/**, scripts/docs/markdown_format/**
touched surfaces: scripts/docs/docs_freeze/**, scripts/docs/prompt_catalog/**, scripts/docs/style_audit/**, scripts/docs/markdown_format/**
slice id: phase0-tooling-followup-review
slice type: review-only
owned surfaces: none
touched surfaces: none

## Slice identity

- work package or slice: integrated evidence for the structural-debt cleanup
  canon plus the current `scripts/docs` package refactor and live proof refresh
- slice type: edit
- date: 2026-05-12

## Plan and review links

- approved plan: `../plans/phase-0-closeout-grammar-and-proof.md`
- mandatory review: `../reviews/phase-0-closeout-grammar-and-proof.md`
- review artifact: `../reviews/phase-0-closeout-grammar-and-proof.md`

## Scope executed

- updated `AGENTS.md` so helpers imported across modules are treated as shared
  surfaces that must use public non-underscored names
- added explicit module-layout and top-level function-ordering rules to
  `STYLE.md`
- aligned the mandatory review gate, file-priority map, and Phase 0 phase page
  so touched backend Python surfaces require repo-native proof from
  `make pyright-api` and later Phase 0-3 cleanup slices require the structural
  debt audit command
- kept `scripts/docs/*` lint and typing proof separate from the backend Python
  proof lane and structural-debt audit lane in Phase 0 canon
- regrouped docs-freeze, prompt-catalog, structural-audit, and markdown-format
  tooling into responsibility packages under `scripts/docs/docs_freeze/`,
  `scripts/docs/prompt_catalog/`, `scripts/docs/style_audit/`, and
  `scripts/docs/markdown_format/`
- kept the top-level CLI entrypoints thin and replaced the old entrypoint-local
  bootstrap wrappers with direct package imports
- split `scripts/docs/format_markdown.py` into a thin public CLI over the new
  `scripts/docs/markdown_format/` helpers so the formatter no longer carries
  file-size threshold debt
- updated the prompt-assets proof to import the prompt-catalog library surface
  instead of file-loading the CLI entrypoint
- reread the current Phase 1, Phase 2, and Phase 3 closeout review exception
  sections so the structural-debt cleanup wording reflects the live later-phase
  exception pressure without widening their ownership
- refreshed the authoritative Phase 0 evidence and review so they describe the
  current package layout, current proof counts, and the remaining exact Phase 0
  blockers truthfully

## Commands run

- `./.venv/bin/python -m scripts.docs.docs_freeze.cli`
  - outcome: `Docs freeze validation passed.`
- `./.venv/bin/python -m scripts.docs.prompt_catalog.cli validate`
  - outcome: `Prompt catalog validation passed.`
- `./.venv/bin/ruff check scripts/docs`
  - outcome: `All checks passed!`
- `./.venv/bin/mypy scripts/docs`
  - outcome: `Success: no issues found in 49 source files`
- `./.venv/bin/python -m scripts.docs.style_audit.cli --fail-on-findings`
  - outcome: `Execution STYLE audit ... No findings.`
- `make pyright-api`
  - outcome: `0 errors, 0 warnings, 0 informations`
- `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest -q tests/unit/test_runtime_prompt_assets.py`
  - outcome: `33 passed in 0.73s`
- `cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest -q tests`
  - outcome: `238 passed in 947.69s (0:15:47)`
- `make test-api-db`
  - outcome: `236 passed in 751.09s (0:12:31)`
- `rg -n "## Phase-bounded STYLE exceptions" docs/execution/reviews/phase-1-closeout-criteria-ownership-and-wp4.md docs/execution/reviews/phase-2-closeout-prompt-legality-and-proof.md docs/execution/reviews/phase-3-closeout-runtime-lineage-and-budget.md`
  - outcome: confirmed the required later-phase review exception sections were
    reread as structural-debt context inputs for this Phase 0 canon slice

## Validation summary

- docs freeze validator:
  - passed
- prompt-catalog validation:
  - passed
- prompt-assets unit proof:
  - passed
  - the direct CLI file-load regression is gone; the proof now runs through the
    prompt-catalog library surface instead
- repo-native backend Python proof command:
  - passed
  - `make pyright-api` remains a valid proof lane for touched backend Python
    surfaces under `apps/api/**`
- structural-debt inventory command:
  - passed with `--fail-on-findings`
  - the current tree now reports zero cross-module private imports, zero
    zero-reference private helpers, and zero file/function threshold findings
- scripts docs tooling thresholds:
  - passed
  - the current `scripts/docs` packages are under the `STYLE.md` file and
    function thresholds after the package refactor
- Phase 0 canon alignment:
  - passed
  - `AGENTS.md`, `STYLE.md`, the mandatory review gate, the file lock map, and
  the Phase 0 phase page now agree on cross-module helper naming,
  structural-debt inventory proof, and backend Python proof expectations
- broader backend proof lanes:
  - passed
  - the current parent tree is green on both the full local suite and the
    Docker/Postgres verification lane
- later-phase review exception reread:
  - passed
  - the current Phase 1, Phase 2, and Phase 3 closeout reviews still carry
  large-file or long-function exceptions, which this Phase 0 slice treats as
  structural-debt context rather than owned scope to widen into

## Artifacts changed

- `AGENTS.md`
- `STYLE.md`
- `docs/execution/gates/mandatory-review-gate.md`
- `docs/execution/maps/file-priority-map.md`
- `docs/execution/phases/phase-0-docs-contract-freeze-and-setup.md`
- `scripts/docs/docs_freeze/**`
- `scripts/docs/docs_freeze/**`
- `scripts/docs/prompt_catalog/**`
- `scripts/docs/prompt_catalog/**`
- `scripts/docs/style_audit/**`
- `scripts/docs/style_audit/**`
- `scripts/docs/format_markdown.py`
- `scripts/docs/markdown_format/**`
- `docs/execution/evidence/phase-0-closeout-grammar-and-proof.md`
- `docs/execution/reviews/phase-0-closeout-grammar-and-proof.md`

## Residual blockers

- none inside the owned Phase 0 docs-tooling surfaces
