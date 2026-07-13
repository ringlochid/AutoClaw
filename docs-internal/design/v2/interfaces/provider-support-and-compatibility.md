# Provider support and compatibility

Status: Target

This page defines the shared local support contract for the `codex`, `claude`, and `openclaw` providers.

## Support model

AutoClaw supports two deployment shapes:

| Provider | Target shape | Runtime ownership | Continuity hint | Initial status |
| --- | --- | --- | --- | --- |
| Codex | Managed local SDK | AutoClaw launches the SDK and bundled pinned runtime | Codex thread id | Targeted |
| Claude | Managed local SDK | AutoClaw launches the SDK and bundled compatible runtime | Claude session id | Targeted |
| OpenClaw | External Gateway | Operator installs and supervises OpenClaw | OpenClaw session key | Targeted with webchat baseline |

Targeted means the V2 contract is frozen but does not claim that the implementation has already shipped.

## Shared readiness contract

A provider is ready only when the named adapter can:

- start with the current task workspace and both prompt lanes
- attach or reach AutoClaw Node MCP
- preserve the existing AutoClaw task and node recognition values
- prevent provider-native approvals or questions from waiting invisibly
- return the effective optional provider session hint
- interrupt an active provider turn through the centralized stop path
- inherit or validate provider-owned authentication and native configuration
- run in the same filesystem and network namespace required by the local task

Operator MCP is not a provider launch prerequisite. Managed workers receive Node MCP only; Operator MCP remains an external operator surface.

Provider output streams and terminal events are not readiness requirements except where an adapter must drain them privately to keep its SDK or process healthy.

## Packaging contract

Managed provider dependencies are optional install extras:

```text
autoclaw[codex]
autoclaw[claude]
autoclaw[managed]
```

`autoclaw[codex]` installs the tested official Codex Python SDK and its pinned runtime. `autoclaw[claude]` installs the tested Claude Agent SDK and its bundled compatible runtime. `autoclaw[managed]` is the union of those two dependency sets.

OpenClaw is not part of `managed`; it remains a separately installed and supervised system.

AutoClaw pins and tests supported SDK versions. Doctor reports the AutoClaw adapter version, SDK version, bundled runtime version when discoverable, and whether a custom runtime path is in use.

## Native configuration and authentication

AutoClaw adds only the correctness overlay required for one dispatch. It does not recreate provider settings.

- Codex inherits normal user and trusted-project configuration and provider-owned ChatGPT or API authentication.
- Claude inherits selected native setting sources and uses supported API or cloud authentication for the product integration.
- OpenClaw inherits the externally managed Gateway configuration and credentials required by its documented client identity.

No raw provider secret is stored in AutoClaw's database or runtime config. Doctor may report credential type and presence without exposing credential content.

## Failure isolation

Each provider has independent readiness. One broken provider does not block AutoClaw startup or another provider's work.

Provider resolution happens before dispatch commit. Once committed, all control retries stay on the resolved provider. Provider start and stop failures are visible as bounded controller-owned control status, not as provider-event ingestion.

## Required conformance

The common conformance suite proves:

- fresh start and continuity resume
- full instruction refresh on resume
- fresh-session fallback with replacement hint
- Node MCP context, plan, progress, external wait, and boundary operations
- 15-minute watchdog progress depends only on semantic MCP commits
- provider-native approvals and questions cannot create hidden waits
- centralized six-call start and stop retry behavior
- app restart can reconstruct desired control from controller persistence without a provider event stream

Provider-specific pages own additional requirements and exact remediation.

## Compatibility pages

- [Codex support and compatibility](codex-support-and-compatibility.md)
- [Claude support and compatibility](claude-support-and-compatibility.md)
- [OpenClaw support and compatibility](openclaw-support-and-compatibility.md)
- [Provider CLI and doctor](provider-cli-and-doctor.md)
- [Provider selection and runtime config](provider-selection-and-runtime-config.md)
