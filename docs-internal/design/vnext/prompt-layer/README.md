# Prompt layer (vnext)

Status: Target

This folder defines how Vnext keeps the current prompt architecture without replacing the controller-truth-first model.

## Core model

Vnext keeps these baseline rules:

- controller-owned truth remains the source for prompt assembly
- prompt artifacts remain derived read surfaces
- support files remain support-only and do not become ordinary prompt truth
- exact prompt text still belongs to shipped or generated prompt assets rather than to UI-owned shadow prompt surfaces
- Vnext keeps the current render-and-persist model rather than adding first-class prompt preview, diff, or regression lanes

## Start here

Read in this order:

1. [Prompt system vnext](prompt-system-vnext.md)
2. [V1 prompt-layer front door](../../v1/prompt-layer/README.md) for the current baseline

## Scope rule

This folder defines future target prompt behavior for dispatch generation, redispatch context, and capability overlays.

It does not define:

- the shipped current prompt assets
- execution-program prompt regeneration commands
- prompt preview, diff, or regression as first-class Vnext surfaces
- adapter-private transport wrappers as controller truth
