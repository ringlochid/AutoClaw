# Claude Agent SDK adapter

Status: Target

This page defines the V2 target mapping for the Claude Agent SDK.

## Confirmed External Behavior

The confirmed external behavior for the Claude Agent SDK is:

- the SDK exposes built-in tools, hooks, subagents, MCP, permissions, and sessions as first-class capabilities: [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)
- tool use is mediated by permission modes, allow and deny rules, and a `canUseTool` callback for unresolved runtime approval decisions: [Configure permissions](https://code.claude.com/docs/en/agent-sdk/permissions)
- user input is requested in two documented situations: tool approval and clarifying questions through `AskUserQuestion`: [Handle approvals and user input](https://code.claude.com/docs/en/agent-sdk/user-input)
- `AskUserQuestion` is available by default unless the allowed tool list is explicitly restricted, and current docs say it is not available in subagents spawned through the Agent tool: [Handle approvals and user input](https://code.claude.com/docs/en/agent-sdk/user-input)
- hooks run on agent events such as tool calls, session lifecycle events, and execution stopping, and can allow, deny, modify, or log behavior: [Hooks](https://code.claude.com/docs/en/agent-sdk/hooks)
- MCP servers can be attached as external tool surfaces for the agent: [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)

## AutoClaw Mapping

AutoClaw maps the Claude Agent SDK into the controller model as follows:

- Claude sessions are adapter-side continuity context, not controller lineage truth
- `canUseTool` approval prompts may be normalized into AutoClaw typed pending human requests when a human decision must become part of controller truth
- `AskUserQuestion` maps to AutoClaw `direction`, `input`, or `review` request kinds after controller normalization
- Claude SDK lifecycle and permission outputs may narrow effective behavior, add audit detail, or sanitize inputs, but they must not widen AutoClaw's controller-owned capability set
- any MCP surfaces attached to the Claude SDK must still preserve AutoClaw's operator versus node trust split rather than exposing one mixed catalog
- Claude-side tool results, hooks, and session memory become controller-relevant only after the AutoClaw adapter normalizes them into controller-owned task events, pending requests, or other persisted source records

## Open Assumptions / Non-goals

- This page does not assume one Claude SDK session maps one-to-one with every future AutoClaw task without additional implementation proof.
- This page does not assume `AskUserQuestion` parity for nested subagent flows because the current docs explicitly limit it there.
- This page does not promote Claude hook event names, permission modes, or session ids into controller-core vocabulary.
- This page does not promote Claude tool-permission vocabulary into AutoClaw's core human-request model.

## Related contracts

- [Adapter contract](../adapter-contract.md)
- [Human request and approval contract](../../interfaces/human-request-and-approval-contract.md)
- [Capability, security, and audit](../../interfaces/capability-security-and-audit.md)
- [Control API and task event stream](../../interfaces/control-api-and-task-event-stream.md)
- [Claude support and compatibility](../../interfaces/claude-support-and-compatibility.md)
