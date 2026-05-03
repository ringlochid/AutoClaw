# Current definition registry and publish lifecycle

Status: Current

Last verified: 2026-04-25

This page defines the current definition registry lifecycle for roles, policies, workflows, and skills.

## Current definition truth

Current file discovery is an ingest source.

Current live definition truth after bootstrap/import is the DB-backed registry:

- definition records
- version records
- published and draft status
- skill registry and skill versions

Current runtime and compile paths use the registry, not the filesystem files, after ingest.

## Current discovery and bootstrap

Current discovery rules are defined in `registry_service.py` and summarized in `definition-precedence-and-skill-version-defaults.md`.

Current bootstrap behavior:

- discover packaged definition files
- overlay filesystem overrides by filename
- validate identity rules
- upsert definition records
- upsert version records
- optionally mark versions as published

Current internal bootstrap route:

- `POST /internal/registry/bootstrap`

## Current read surfaces

Current registry read surfaces include:

- list roles
- list policies
- list workflows
- list skills
- list versions for roles, policies, workflows, and skills
- internal registry snapshot
- public workflow validation preview

Current routes live in `autoclaw-main/apps/api/app/api/routes/registry.py`.

## Current write lifecycle

Current write lifecycle is:

1. create or update draft version
2. validate where needed
3. publish a specific version

Current write surfaces exist for:

- skills
- roles
- policies
- workflows

## Current guarded write behavior

Current registry writes already use guarded/CAS-shaped fields.

Examples:

- `expected_draft_version`
- `expected_published_version`

Current definition writes also accept write-audit metadata through headers:

- `X-AutoClaw-Actor`
- `X-AutoClaw-Source-Session`
- `X-AutoClaw-Source-Agent`
- `X-AutoClaw-Source-Node-Attempt`
- `X-AutoClaw-Reason`

Current docs must treat these as part of the real write contract, not as optional commentary.

## Current validation and publish rules

Current workflow validation preview:

- validates a `WorkflowDefinitionSeed`
- returns normalized plan preview
- does not itself publish or launch

Current publish routes:

- publish a specific version number
- can reject on stale version expectations
- can reject on invalid definition content

## Current skill-specific rule

Current registry still carries `skill_refs` and skill registry/version surfaces.

That is current truth only. It is not redesign guidance.

## Minimal example

```text
bootstrap
  -> discover files
  -> validate identity
  -> upsert definition rows
  -> upsert version rows
  -> mark published when requested
```

## Expanded example

```text
workflow draft update
  -> PUT /registry/workflows/{key}/draft
  -> include expected_draft_version when guarding against stale writes
  -> write audit metadata may be forwarded in headers
  -> POST /registry/workflows/validate to preview normalized plan
  -> POST /registry/workflows/{key}/versions/{version}/publish
  -> include expected_published_version when guarding publication
```

## Evidence

- inspected code in `autoclaw-main/apps/api/app/services/registry_service.py`
- inspected code in `autoclaw-main/apps/api/app/api/routes/registry.py`
- inspected code in `autoclaw-main/apps/api/app/registry/publish.py`
- inspected code in `autoclaw-main/apps/api/app/api/deps.py`

## Related current pages

- `definitions-compiler-and-launch.md`
- `definition-precedence-and-skill-version-defaults.md`
- `current-definition-bootstrap-and-task-upload.md`
- `api-surface-and-route-map.md`

## Redesign pointer

For the target definition registry and guarded publish contract, see `../../redesign/interfaces/definition-registry-and-publish-contract.md` and `../../redesign/interfaces/guarded-registry-and-runtime-writes.md`.
