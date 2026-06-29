# AutoClaw frontend task-compose set

Use these launch files in order. Do not start a later implementation slice until the plan/contract lock and prerequisite slice evidence are current.

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

All composes bind the workspace to `/home/ubuntu/leo/projects/autoclaw` and keep task context/evidence under `/home/ubuntu/leo/projects/autoclaw/tmp/autoclaw-frontend/<slice>`.
