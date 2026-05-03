# Rewrite done gate

Status: Reference

Use this gate only when the redesign landing pack itself is considered complete.

- [ ] `../../../AGENTS.md` is the canonical root instruction surface
- [ ] `../../../AGENTS.md` is the single source of shared Codex execution policy and shared implementation quickstart
- [ ] `../../../AGENT.md` is a compatibility bridge only
- [ ] `../../../STYLE.md` owns measurable code-style and refactor rules
- [ ] `../../../STYLE_GUIDE.md` owns docs/style rules only
- [ ] execution prompts, gates, and how-to pages reference `../../../AGENTS.md` instead of mirroring shared policy
- [ ] `.` contains the reusable prompt families, verification prompts, and supporting prompts
- [ ] `.` contains rewrite, phase, review, reset, quality, and answer-sourcing gates
- [ ] `.` contains the cleanup-and-salvage checklist when Phase 0.5 exists
- [ ] `../phases` contains one master phase overview plus one page per phase
- [ ] `../maps` contains the repo salvage matrix when Phase 0.5 exists
- [ ] `../maps` contains the canonical implementation file lock map
- [ ] phase pages act as the sole phase-local execution contract owners
- [ ] phase pages act as WBS-backed phase-local delivery contract owners
- [ ] phase pages name implementation surfaces, do-not-edit surfaces, subagents rules, wave integration loops, and mandatory checklists
- [ ] execution routing points implementers to appendix owners for exhaustive API/schema/prompt detail
- [ ] reusable execution prompts are reference-first rather than large mirrored phase summaries
- [ ] reusable execution prompts are limited to pre-implementation review, phase planning, and post-implementation review
- [ ] the execution pack is aligned with the canonical redesign contracts
- [ ] the progressive minimal, normal, and maximal e2e matrix is defined
- [ ] bug tracking, triage, and reset how-to guides exist
- [ ] root and redesign readmes route implementers to the execution pack
- [ ] older packs are no longer needed as first-line execution guidance
