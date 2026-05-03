# Code quality gate

Status: Reference

Use this gate for every phase that touched repo code. For the exact shared gate commands, use [AGENTS.md](../../../AGENTS.md). For measurable thresholds, use [STYLE.md](../../../STYLE.md).

## Checklist

- [ ] every touched surface passed the relevant repo-native quality gates from `../../../AGENTS.md`
- [ ] the exact gates run were recorded with pass or fail status
- [ ] touched functions meet the refactor threshold rule from `../../../STYLE.md`, or an explicit review exception was recorded
- [ ] touched files meet the split-review threshold rule from `../../../STYLE.md`, or an explicit review exception was recorded
- [ ] naming is explicit and domain-correct
- [ ] stale abstractions were removed rather than preserved as ghosts
- [ ] async usage follows framework reality rather than fashion
- [ ] ORM-backed fanout paths were reviewed for N+1 or accidental lazy-load risk
- [ ] aggressive refactor happened where the touched phase area required it

## Failure rule

If a relevant quality gate failed or a touched area still needs clear refactoring, the phase remains open unless there is an explicit, phase-bounded blocker recorded in review.
