# ADR-0004: OpenClaw Owns Skill Packages

## Status

Accepted

## Decision

OpenClaw remains the owner of skill internals, execution tools, and agent behavior.
AutoClaw stores only pinned skill references and runtime binding metadata.

## Consequences

### 1. What AutoClaw may store

AutoClaw may store the pinning and dispatch data needed to resolve a skill safely:

- `provider`
- `key`
- `version_label`
- `skill_version_id`
- `runtime_name` (the exact `SKILL.md` `name`)
- `source_uri` / `source_ref`
- `artifact_ref`
- `artifact_sha256`
- `manifest_summary` parsed from `SKILL.md` frontmatter

This data exists to support search, provenance, packaging, and runtime materialization.
It does not make AutoClaw the default authoring owner of skill logic.

### 2. What AutoClaw should compile

Compiled execution truth should be a **node-local effective skill binding set**.
Role/workflow skill references remain authoring/default layers, but runtime dispatch should consume only the resolved node-local bindings.

Illustrative binding shape:

```json
{
  "provider": "openclaw",
  "key": "contract-checker",
  "runtime_name": "autoclaw-contract-checker",
  "version_label": "2026-04-17",
  "skill_version_id": "uuid",
  "source_ref": "clawhub://openclaw/contract-checker@2026-04-17",
  "artifact_ref": "s3://autoclaw-skills/contract-checker/2026-04-17.skill",
  "artifact_sha256": "abc123",
  "manifest": {
    "name": "contract-checker",
    "description": "Check frontend/backend contract drift"
  },
  "state": "required"
}
```

### 3. What AutoClaw should not own by default

AutoClaw should not, by default, invent a second skill-logic format or become the canonical home of:

- raw `SKILL.md` behavior
- skill-local `scripts/`
- skill-local `references/`
- OpenClaw tool/runtime semantics

Those remain OpenClaw concerns unless there is a later explicit architecture change.

### 4. Dispatch and materialization rule

Before a node executes delegated work, AutoClaw should:

1. resolve the node-local effective skill bindings
2. materialize or verify the required OpenClaw skill packages for the delegated session
3. apply a session-level skill filter that reflects `allowed` / `required` / `blocked`
4. fail closed if a `required` skill cannot be materialized or verified

Node execution should not rely on prompt luck alone to make a required skill available.
