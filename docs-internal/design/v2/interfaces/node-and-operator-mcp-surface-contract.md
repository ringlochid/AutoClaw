# Node and operator MCP surface contract

Status: Target

This page defines the V2 shared MCP contract for AutoClaw node and operator surfaces across `openclaw`, `codex`, and `claude`.

## Core rule

AutoClaw should keep one provider-neutral logical MCP contract:

- one shared `node` surface
- one shared `operator` surface

Provider-specific adapters may launch, authenticate, or mount those surfaces differently, but they should not fork the logical tool vocabulary without a proven hard incompatibility.

## Lowest-common-denominator profile

The shared AutoClaw MCP contract should assume only the profile that all targeted providers can reliably use:

- tools-first interaction
- `stdio` or streamable HTTP or HTTP transport
- JSON-schema tool input contracts
- plain-text plus structured-result fallback for tool outputs
- no correctness dependency on prompts, resources, channels, tool-search, or dynamic tool-refresh extensions
- no provider-specific tool names

Rules:

- MCP server `instructions` may help clients, but they must not be the only place that critical semantics live
- provider-specific approval or permission models are adapter concerns, not tool-schema forks
- if one provider needs a different auth or transport wrapper, split that wrapper rather than the logical tool namespace

## Shared surface split

The shared logical surfaces are:

- `node`
- `operator`

`node` owns provider-neutral current-node execution tools such as:

- definition lookup
- checkpoint recording
- boundary close or yield
- parent or root structural mutation
- controller-owned `human_request` and `command_run` tools that open external waits directly, with `command_run` reserved for long command work that is expected to exceed about two minutes

`operator` owns provider-neutral task-control tools such as:

- definition upload or start-task writes
- read-only definition draft-set discovery and detail inspection
- runtime read and control
- human-request inspection and resolution
- running command-run cancellation
- support-state and observability refs

Rules:

- `human_request` and `command_run` are already part of the V2 shared `node` surface; they are not deferred future vocabulary
- those tools create controller waiting states directly and therefore do not borrow workflow boundary-acceptance semantics
- the owner contracts for their input and output envelopes remain the human-request and command-run pages rather than this index page
- operator-side command-run cancel is a dedicated control action over an already-open run; it is not the same thing as whole-task pause or whole-task cancel
- mutating definition draft authoring belongs to the `/authoring` workbench API, not to the shared operator MCP tool vocabulary
- operator MCP may expose read-only draft-set discovery, for example `list_definition_draft_sets` and `get_definition_draft_set`, so automation can find current draft refs and inspect saved draft readbacks without becoming a second editor lane

## Compatibility boundary

Provider compatibility is decided at launch, not by inventing separate MCP contracts.

Rules:

- if a selected provider cannot use the required shared `node` or `operator` surface, runtime fails or falls back before dispatch acceptance
- ordinary node MCP access is a provider/runtime compatibility fact, not a per-dispatch capability matrix
- provider-specific session ids, approval callbacks, OAuth flows, or tool allow-lists remain adapter-local behavior

## No-split rule

Do not create provider-specific logical routes such as:

- `/codex/node`
- `/claude/node`
- `/openclaw/operator`

unless a real hard incompatibility appears in practice.

If a split ever becomes necessary, split only:

- transport wrapper
- auth wrapper
- adapter launcher

Do not split:

- logical tool names
- node versus operator trust separation
- controller-owned request and response semantics

## Related contracts

- [Provider preference and runtime config](provider-selection-and-runtime-config.md)
- [Provider-aware setup, configure, and doctor](provider-aware-setup-and-doctor.md)
- [Capability, security, and audit](capability-security-and-audit.md)
- [Control API and task event stream](control-api-and-task-event-stream.md)
- [Codex app-server adapter](../architecture/adapters/codex-app-server.md)
- [Claude Agent SDK adapter](../architecture/adapters/claude-agent-sdk.md)
