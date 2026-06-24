# Adapter contract

Status: Target

This page defines how V2 adapters may integrate with AutoClaw without becoming runtime truth owners.

## Core rule

Adapters are translation layers over controller-owned truth.

An adapter may provide transport, approval signals, user-input callbacks, session handles, callbacks, or streamed events. It must not silently redefine:

- task lineage truth
- waiting-cause truth
- continuation legality
- assignment success
- checkpoint truth
- task event chronology

## Canonical adapter responsibilities

An adapter may own:

- adapter-native session or conversation identifiers
- transport request and response handling
- adapter-native approval or interruption callbacks
- adapter-native event or notification streams
- adapter-local auth, permission, and tool-surface plumbing

The controller owns:

- task, flow, assignment, attempt, and waiting-cause truth
- pending human requests and long-running command runs
- normalized task event records
- legality and continuation decisions
- the meaning of success, failure, retry, and escalation

## Normalization rule

Any adapter-originating signal must be normalized into one of these controller-owned lanes before it affects behavior:

- normalized `task_event`
- pending human request
- command-run update
- terminal controller error

No adapter-native object, callback, or stream event becomes live controller truth without normalization.

## Source-grounding rule

Every adapter-specific page must use these sections in this order:

1. `Confirmed External Behavior`
2. `AutoClaw Mapping`
3. `Open Assumptions / Non-goals`

Rules:

- only externally confirmed facts belong in `Confirmed External Behavior`
- AutoClaw target translation belongs in `AutoClaw Mapping`
- uncertainty, desired future behavior, or implementation placeholders belong in `Open Assumptions / Non-goals`
- controller-core pages must not import adapter terminology as if it were generic controller truth

## Event-ingest rule

When an adapter offers streamed events:

- raw adapter ordering is input detail only
- controller event ordering is commit order of normalized controller records
- adapter sequence numbers may survive as secondary debug detail only
- reconnect, replay, and dedupe for control UI/API reads must use controller task-event ids, not adapter-local cursors alone

## Session rule

Adapter sessions, threads, or conversations may provide continuity context, but they do not replace controller lineage.

Rules:

- adapter session identity is adapter-private unless a mapping page explicitly states how it is persisted as controller-linked evidence
- controller continuation legality must not depend on adapter memory alone
- if adapter continuity conflicts with controller truth, controller truth wins

## Related pages

- [Controller contract and resumable execution](controller-contract-and-resumable-execution.md)
- [Control API and task event stream](../interfaces/control-api-and-task-event-stream.md)
- [Codex app-server adapter](adapters/codex-app-server.md)
- [Claude Agent SDK adapter](adapters/claude-agent-sdk.md)
- [V1 OpenClaw worker and gateway contract](../../v1/architecture/openclaw-worker-and-gateway-contract.md)
