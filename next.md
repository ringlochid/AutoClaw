# Next Plan (MAX-complex workflow, non-UI)

## Current inspection result
- `autoclaw-worker` workspace was checked for available skills and operator tooling before planning.
- Existing repo docs and code were reviewed (Phase-8 bridge fixes, `docs/e2e/phase8-happy-path.md`, workflow/runtime tests).
- No existing definition package is currently tagged as an "AI-powered tools in education industry" workflow.
- Search confirms no education-specific definition text in current `definitions/` or docs, so the next work is a new definition package.

## Objective
Prepare a deployable MAX-complex workflow for:
**"AI-powered tools in education industry"**
so after gateway/API restart the run is reproducible via real DB bootstrap + flow start.

## Next plan (no UI changes)

1. **Scan worker skills and map reusable primitives**
   - Inspect `~/.openclaw/workspaces/autoclaw-worker/skills/*` and identify any existing skills usable for:
     - market discovery / problem discovery
     - tool definition / capability selection
     - policy/constraints logic
     - governance / checkpoint gating
   - Record a minimal mapped list in `definitions/` notes.

2. **Author definition bundle (repo side)**
   - Add workflow definition:
     - `definitions/workflows/ai-powered-tools-education-industry.yaml`
   - Add supporting role/policy/skill definitions in:
     - `definitions/roles/`
     - `definitions/policies/`
     - `definitions/skills/` (if needed by the workflow)
   - Keep IDs/keys consistent with existing naming style (`education-*`, `workflow-education-*`, etc.).

3. **Version-safe local scan + validation**
   - Run local schema + lint-style checks (if configured) for the new files.
   - Verify references resolve between workflow nodes, roles, skills, and policies.

4. **Bootstrap real registry state for test DB**
   - Use restart-safe DB URL path behavior already fixed.
   - Run:
     - `AUTOCLAW_DATABASE_URL=sqlite+aiosqlite:////tmp/autoclaw-phase8/autoclaw.db`
     - `autoclaw db upgrade`
     - `autoclaw db bootstrap --config /home/ubuntu/.config/autoclaw/config.toml`
   - Confirm counts in `workflow_definitions`, `role_definitions`, `policy_definitions`, `skill_registry` include new package.

5. **Real execution rehearsal (post-gateway restart)**
   - Start server/API on `127.0.0.1:8015` using the current gateway/run args.
   - Execute:
     - `POST /internal/registry/bootstrap` (internal key)
     - `POST /flows/from-workflow/<new-key-or-workflow-id>`
     - track checkpoints + context-manifest flow
   - Ensure no manual payload hacks are required for basic flow progress.

6. **Close the loop with evidence**
   - Update:
     - `docs/e2e/phase8-happy-path.md` (add dedicated section for education MAX-complex run)
     - `docs/flows/` with concise runbook links
     - `memory/2026-04-19.md` when handoff is complete
   - Add/adjust integration checks if needed for the new definitions.

## Acceptance criteria
- [ ] A new education MAX-complex workflow definition exists in source (`definitions/*`).
- [ ] Registry bootstrap succeeds on fresh DB with that package.
- [ ] Flow can be started via API after restart without schema-route hacks.
- [ ] End-to-end run moves through context-manifest and checkpoint gates with expected final status.
- [ ] Documentation and `next.md` plan are up to date.
