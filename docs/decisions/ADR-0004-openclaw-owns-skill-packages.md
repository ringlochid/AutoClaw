# ADR-0004 — OpenClaw Owns Skill Packages

- **Status:** Accepted
- **Date:** 2026-04-13

## Context

AutoClaw is built on top of OpenClaw.
Skills in this ecosystem may include `SKILL.md`, scripts, references, and nested assets.

## Decision

OpenClaw owns actual skill package source and execution behavior by default.
AutoClaw stores references, metadata, compatibility, and version pinning for those skills.

## Consequences

- AutoClaw avoids duplicating skill source unnecessarily
- the boundary between framework and runtime host stays cleaner
- AutoClaw must implement good skill reference / version pinning in the registry
