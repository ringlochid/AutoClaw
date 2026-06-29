# AutoClaw frontend launch plan

## Uploaded definitions

Live registry now has these frontend roles:

- `frontend_engineer`
- `frontend_contract_integrator`
- `frontend_visual_verifier`
- `frontend_code_reviewer`
- `frontend_contract_planner`

Live registry now has these frontend workflows:

- `frontend-console-delivery-program`
- `frontend-feature-slice`
- `frontend-suite-release-review`

## Launch order

Use the task-compose files under `references/frontend/task-compose/` in this order:

1. `00-plan-contract-lock.yaml`
2. `10-api-config-foundation.yaml`
3. `20-tasks-page.yaml`
4. `30-task-detail-sse.yaml`
5. `40-human-requests-page.yaml`
6. `50-command-runs-page.yaml`
7. `60-definitions-page.yaml`
8. `70-task-start-page.yaml`
9. `80-definition-editor-page.yaml`
10. `99-suite-release-review.yaml`

Do not start implementation slices until `00-plan-contract-lock.yaml` has produced the current plan, locked contracts, and launch-readiness review.

## Root bindings

Every compose binds:

- workspace: `/home/ubuntu/leo/projects/autoclaw`
- context/evidence: `/home/ubuntu/leo/projects/autoclaw/tmp/autoclaw-frontend/<slice>`

The planning task must write comprehensive plans under `references/frontend` and locked frontend contracts under `docs-internal/design/v2/console`.

## Start command

Start the planning/contract-lock task first:

```bash
./.venv/bin/autoclaw task-compose start --file references/frontend/task-compose/00-plan-contract-lock.yaml --json
```

Starting a task changes runtime state. Review the compose before launch.
