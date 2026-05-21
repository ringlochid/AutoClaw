# Execution Reviews

Status: Reference

This folder is the canonical repo-local home for mandatory phase reviews, closeout reviews, and explicit review exceptions.

Use this folder for:

- authoritative phase-scoped mandatory review writeups
- phase-done or closeout review notes
- explicit exceptions or blockers that remain after validation
- historical cross-phase closeout summaries that explicitly stay summary-only

Rules:

- authoritative mandatory reviews here evaluate landed work against canon; they do not replace the phase pages, gates, or implementation file lock map
- authoritative mandatory reviews must name exactly one selected phase and one current phase page, and must link the matching plan under `../plans/` and executed proof under `../evidence/`
- every authoritative mandatory review here must use the exact labels `selected phase:`, `current phase page:`, `selected work packages:`, `summary-only: no`, and `delegated slices:`
- when `delegated slices:` is `listed`, each delegated slice record must use the exact labels `slice id:`, `slice type:`, `owned surfaces:`, and `touched surfaces:`
- authoritative mandatory reviews should start from `./phase-review-template.md`
- every authoritative mandatory review must record delegated-slice compliance, proof lanes relied on, stale-logic search proof, kill-list proof, docs answer-sourcing proof, and any phase-bounded `STYLE.md` exceptions or an explicit `none`
- when a phase-bounded `STYLE.md` exception is recorded, state the exact surface, exact exception, reason, boundary, and owning follow-up
- cross-phase or aggregate closeout artifacts may exist here only as historical summaries; mark them `summary-only: yes` and do not use them as mandatory-review, reset-gate, or phase-done closure authority
