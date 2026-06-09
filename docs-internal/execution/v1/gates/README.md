# Execution gates

Status: Reference

This surface contains binary gates, the three execution-pack prompt families, and supporting helper snippets. Shared execution policy lives in [Root execution contract](../../../../AGENTS.md).

## Start here

- [Rewrite-done gate](rewrite-done-gate.md)
- [Cleanup and salvage checklist](cleanup-and-salvage-checklist.md)
- [Phase-done gate](phase-done-gate.md)
- [Mandatory review gate](mandatory-review-gate.md)
- [Reset gate](reset-gate.md)
- [Docs answer-sourcing checklist](docs-answer-sourcing-checklist.md)
- [Code quality gate](code-quality-gate.md)
- [Phase prompts](phase-implementation-prompts.md)
- [Verification prompts](verification-prompts.md)
- [Supporting prompts](supporting-prompts.md)

## Prompt families

- pre-implementation review
- phase plan
- post-implementation review

## Execution record home

- [Plans home](../plans/README.md) stores approved phase plans and WBS artifacts.
- [Evidence home](../evidence/README.md) stores executed validator, test, gate, reset, and smoke evidence.
- [Reviews home](../reviews/README.md) stores mandatory review outputs, closeout reviews, and explicit exceptions.

Supporting prompts in this folder are narrow helper snippets only. They do not create additional phase-local authority or a fourth execute-mode prompt family.

## Surface rule

Use this surface for binary gates and reusable prompts only. Use [Root execution contract](../../../../AGENTS.md) for shared execution policy and quickstart. Use [Coding standards](../../../../STYLE.md) for coding standards. Use the current phase page for phase-local delivery detail.
