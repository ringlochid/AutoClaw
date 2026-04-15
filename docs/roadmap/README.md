# Roadmap Index

Use this folder as the **implementation migration plan** for AutoClaw.
It should describe what must be built, removed, or cut over — not pretend the current code already matches the target model.

## Reading order

1. `current.md` — honest status of the codebase vs target contract
2. `00-principles.md` — invariants that every phase must preserve
3. `01-phase-1-kernel-and-data-model.md`
4. `02-phase-2-registry-and-compiler.md`
5. `03-phase-3-runtime-and-openclaw-integration.md`
6. `04-phase-4-operator-console.md`
7. `05-phase-5-replan-watchdog-and-approval.md`
8. `06-phase-6-advanced-hierarchy-and-packs.md`
9. `06.5-phase-6.5-pre-phase-7-stabilization.md`
10. `07-phase-7-controller-driven-looping-and-governance.md`
11. `08-phase-8-production-openclaw-bridge-and-native-plugin-adapter.md`
12. `backlog.md` — deferred work only
13. `suggestion.md` — engineering style and verification guide

## Rules for this folder

- Treat `docs/architecture/**` as the target contract.
- Treat `current.md` as the truth about what the code does today.
- Do not describe legacy `run -> attempt -> flow` structures as the desired target.
- Do not put core migration work into `backlog.md`; backlog is for real deferrals.
- If a phase removes misleading earlier assumptions, say so explicitly.
