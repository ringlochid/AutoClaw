# Prompt layer (vnext)

Status: Target

This folder defines how Vnext extends the current prompt architecture without replacing the controller-truth-first model.

## Core model

Vnext keeps these baseline rules:

- controller-owned truth remains the source for prompt assembly
- prompt artifacts remain derived read surfaces
- support files remain support-only and do not become ordinary prompt truth
- exact prompt text still belongs to shipped or generated prompt assets rather than to UI-only previews

Vnext adds these first-class prompt concerns:

- rendered prompt preview
- prompt diff between current truth and draft content
- role and policy preview
- capability-sensitive preview for human-request and async-job permissions
- prompt regression fixtures that lock future design expectations

## Start here

Read in this order:

1. [Prompt system vnext](prompt-system-vnext.md)
2. [Prompt regression suite](prompt-regression-suite.md)
3. [V1 prompt-layer front door](../../v1/prompt-layer/README.md) for the current baseline

## Scope rule

This folder defines future target prompt behavior and prompt-facing validation concerns.

It does not define:

- the shipped current prompt assets
- execution-program prompt regeneration commands
- adapter-private transport wrappers as controller truth
