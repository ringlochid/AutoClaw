# Current-to-target mapping

Status: Reference

This page is a high-level migration orientation map only.

## Core replacement map

| Current concept                                   | Target replacement                                               |
| ------------------------------------------------- | ---------------------------------------------------------------- |
| flat flagship workflow with dotted ids            | nested ownership tree plus typed dependency selectors            |
| current mixed worker and operator assumptions     | explicit worker bridge plus separate operator parity             |
| catch-all runtime content mutation                | typed artifacts, handoffs, review outputs, and result records    |
| approval-era intervention model                   | blocked outcomes, whole-flow pause, and bounded parent decisions |
| install/docs spread across repo-local assumptions | packaged install truth plus exact root CLI onboarding            |

## Detailed appendix

Use [Current schema, route, and plugin migration appendix](current-schema-route-and-plugin-migration-appendix.md) for concrete keep, replace, remove, and support-only-lane outcomes.

## Rule

Use this page for migration orientation only. Use `docs/redesign/` for canonical target behavior.
