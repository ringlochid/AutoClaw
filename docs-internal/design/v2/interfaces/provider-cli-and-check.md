# Provider CLI and check

Status: Target

This page owns the V2 operator CLI for local setup, passive status, provider-native identity, and bounded provider checks. It does not own runtime provider selection, adapter semantics, browser mutation, or release conformance.

## Product shape

The CLI combines guided terminal entry points with small deterministic commands. The guided flow is orchestration only: it delegates each accepted step to the same local initialization, provider configuration, default-selection, identity, and check operations available as direct commands. It does not introduce a resumable onboarding journal or a second configuration path.

```text
autoclaw
autoclaw status
autoclaw init
autoclaw setup
autoclaw providers list
autoclaw providers status [provider]
autoclaw providers check <provider>
autoclaw providers login <provider>
autoclaw providers logout <provider>
autoclaw providers configure <provider>
autoclaw providers set-default <provider>
```

Database, service, registry, definition, and diagnostic commands remain separately invocable. Provider commands never become hidden prerequisites for unrelated controller work.

## Zero-provider state

Zero configured providers is a valid controller state. Without Codex, Claude, or OpenClaw readiness, an operator can still:

- initialize AutoClaw-local state;
- inspect passive status;
- maintain and reset the database;
- author, validate, publish, and inspect definitions;
- inspect task history and committed events; and
- run diagnostics that do not require a provider turn.

Only operations that require a dispatch need a valid provider route. A directly awaited continue returns a precise route failure before D2; an already committed asynchronous task/boundary source may instead move to `runtime_transition_failed` for repair. API startup, service startup, status, and registry work do not depend on provider readiness.

## Bare command and status

Bare `autoclaw` and `autoclaw status` are passive, read-only summaries. They do not:

- spawn a provider or model turn;
- make provider network calls;
- refresh authentication;
- write readiness caches;
- repair configuration;
- open a task or dispatch;
- run a compatibility matrix; or
- start background runtime owners.

Status reports configured and observable local facts without presenting an earlier check result as current readiness. Machine output keeps explicit `not_checked` values where freshness is unknown. Human output labels the view as local configuration and points to the exact `providers check` command instead of repeating diagnostic-shaped `not_checked` rows for every provider.

The summary may show:

- AutoClaw config and data paths;
- database configuration/schema visibility from a local nonmutating read;
- service configuration and observable state;
- configured default provider route;
- installed provider integration availability;
- native identity/home location without secret contents; and
- current enabled/experimental/unsupported labels from target support policy.

## Init and setup

On an interactive terminal, `autoclaw init` and `autoclaw setup` are guided flows. `--non-interactive` disables prompts, and non-TTY or `--json` invocation never waits for input. Explicit command options remain usable in either mode.

Interactive human output uses terminal-aware structure and semantic color for sections, current state, success, warnings, and failures. It remains readable without color and as plain text when output is redirected. JSON output is not decorated.

`autoclaw init` guides AutoClaw-local initialization only. A fresh run shows the recommended config path, data path, database, and loopback API settings, allows the user to review alternatives, and confirms before writing. When config already exists, rerunning offers to keep and verify it, explicitly replace it, or cancel; it never overwrites or resets state merely because the command was rerun. The shipped database path still creates an empty current schema or verifies an exact current schema. Schema replacement remains the separate destructive `autoclaw db reset` operation. `init` does not log in to providers, mutate provider selection, install OpenClaw, or start an agent turn.

`autoclaw setup` guides provider setup. It shows current provider/default state, asks for the primary/default provider when one was not supplied, configures that route, explicitly selects it as the default, performs the bounded provider check, offers the supported provider-native login flow when authentication is required, and asks whether to configure additional providers. Additional providers do not replace the selected primary default. OpenClaw remains selectable, including as the default, while its experimental and user-managed configuration status is disclosed.

Every accepted setup step commits independently through its owning operation. Cancellation therefore preserves completed explicit steps, and rerunning derives the next prompts from current config instead of a setup journal. Setup is not one all-or-nothing transaction and does not silently repair provider, database, or service state.

Guidance distinguishes effective environment overrides from provider enablement persisted in the selected TOML file. It never recommends `set-default` for an environment-only provider because that command can select only a provider enabled in the persisted configuration; it recommends `providers configure` first.

## Provider list and status

`providers list` reports installed integration definitions and their product status: managed target, experimental, unsupported, or unavailable.

`providers status` is passive. It resolves the same service identity and provider home that runtime launch will use, then reports local facts such as executable/library presence, configured route, selected native home, and whether required local fields are present. It does not prove authentication or reachability unless those facts are directly readable without a provider operation.

## Provider check

`providers check <provider>` is an explicit fresh bounded diagnostic. It may:

- inspect the provider's native executable, library, and configuration under the runtime service identity;
- perform the provider's documented non-agent authentication or reachability check;
- validate deterministic adapter and managed/compatibility MCP prerequisites;
- report sanitized compatibility/version facts; and
- return stable machine-readable failure categories.

It must not:

- create a task, flow, assignment, attempt, dispatch, binding, or Node MCP invocation;
- run a model turn;
- mutate provider configuration or authentication state;
- refresh credentials through an undocumented flow;
- call runtime Node tools;
- write a persistent readiness cache; or
- substitute for pinned release conformance tests.

Stable outcome categories distinguish at least `ready`, `not_configured`, `not_installed`, `authentication_failed`, `unreachable`, `incompatible`, `policy_blocked`, and `check_failed`.

Authentication and reachability are separate `not_checked | passed | failed` axes. An adapter changes an axis from `not_checked` only when its bounded diagnostic directly proves that fact. A successful overall check therefore does not imply that both axes were inspected.

Human output renders those axes as `confirmed`, `failed`, or `not tested`; machine output retains the stable enum values. A Codex `account/read` response with a typed ChatGPT or API-key account directly confirms authentication. Missing required OpenAI authentication reports failure. Credential sources whose validity is not proved by that response, including managed cloud credentials, remain `not_checked`. The account read does not prove remote model reachability.

## Login and logout

Provider identity remains provider-owned. `providers login` and `providers logout` may invoke the provider's supported native command or SDK flow, but AutoClaw does not parse, copy, normalize, encrypt, or store the resulting credential.

The command must identify the operating-system service account and native provider home that runtime will use. A login performed under another user or home does not make the AutoClaw service ready.

Codex uses its native `CODEX_HOME` behavior. Claude uses supported API/cloud or vendor-native configuration. OpenClaw owns its Gateway identity and user configuration.

## Provider configuration boundary

AutoClaw stores provider selection and non-secret route settings only. It does not maintain a second provider profile or credential store.

The CLI never:

- copies provider token caches;
- writes dispatch MCP credentials into provider config;
- patches `openclaw.json`;
- weakens OpenClaw bind, sandbox, tools, exec, approval, or deny lists;
- changes Codex or Claude global tool policy to make one dispatch work; or
- silently falls back from an explicitly selected route.

Managed Codex/Claude MCP connection material is injected dynamically for one dispatch by the adapter. OpenClaw compatibility MCP is configured and maintained by the user.

### Configure and default selection

`autoclaw providers configure <provider>` validates and commits AutoClaw-owned enablement plus non-secret route settings. Direct invocation and setup use this same operation; setup does not maintain a second configuration path.

When configuration succeeds, its transaction fills `runtime.default_provider` only when no default exists. Configuring a later provider preserves the existing default. Guided setup routes the user's explicit primary-provider choice through the same default-selection operation exposed by `autoclaw providers set-default <provider>`; additional-provider steps do not replace it.

`autoclaw providers set-default <provider>` is the owning operation that replaces an existing default, whether invoked directly or by guided setup after an explicit primary-provider choice. It requires an enabled, deterministically valid configured route. OpenClaw is eligible while retaining its experimental label.

A failed or rolled-back configure operation leaves the default unchanged. Later check, authentication, reachability, compatibility, or runtime-start failure also leaves it unchanged and never selects a fallback. A missing, disabled, or broken configured default produces an explicit route error. Disabling or removing the current default must explicitly clear it or select a replacement.

## Runtime readback

Passive CLI runtime summaries consume controller read models. They may show:

- resolved provider and selection source;
- `provider_native_access: {effective, source}` where `effective` is `full | restricted | denied`;
- `network_access: {effective, source}` where `effective` is `allow | deny`;
- dispatch state `starting | open | closed`;
- provider-start attempt count, next retry time, retry kind, and sanitized error;
- watchdog activity/deadline and recovery count;
- pause reason and legal operator actions; and
- active human-request or command-run source.

They never show raw credentials, managed binding material, provider output, provider events, provider/MCP session IDs as authority, raw human answers, or command logs.

Provider start has no finite attempt maximum. A display therefore says `attempt N; next retry ...`, not `attempt N/M` or `exhausted`. Watchdog replacement retains its separate bounded cap and pause outcome.

For both capability axes, `source` is `default | policy_definition | task_policy | controller`. Equal effective ceilings report `controller > task_policy > policy_definition > default`; adapter-local hard ceilings report `controller`.

## Command behavior and output

Mutating commands state the requested mutation before performing it and return one stable result. Read commands remain read-only. JSON output is versioned by its owning contract and uses the same semantic categories as human output.

Failures identify the exact command, provider route, service identity/home, and safe next explicit action. They do not recommend destructive reset, global policy weakening, or provider fallback unless the owning command truly requires it.

## Browser boundary

Provider configuration, login/logout, enablement, and default mutation are CLI-only in the loopback phase. The console may display passive provider status and controller readbacks, but browser provider mutation is out of scope. This target does not introduce a server session, cookie lifecycle, CSRF-token system, TLS/proxy mode, or remote-browser authentication to reopen it.

## Removed commands and concepts

The target removes:

- monolithic `autoclaw onboard`;
- generic `doctor --fix` as a hidden mutation owner;
- broad `configure --section all` orchestration;
- OpenClaw-first setup or service gating;
- persistent provider readiness/`last_check` caches;
- AutoClaw-owned provider profiles and alternate homes;
- implicit provider fallback; and
- provider start or Node MCP calls inside checks.

Focused subsystem diagnostics may retain a read-only `check` command. Repair remains an explicit owning mutation, not an option hidden in a diagnostic.

## Required proof

- controller initialization, API/service startup, registry work, and passive status succeed with zero providers;
- bare/status commands perform no provider network or model work and no writes;
- check creates no task, dispatch, binding, Node MCP call, config change, or credential refresh;
- setup/status/check/runtime resolve the same service identity and native provider home;
- interactive init preserves existing state by default, confirms replacement, and never resets a mismatched schema;
- non-TTY, `--non-interactive`, and `--json` invocation never waits for input;
- guided setup and direct commands share provider configuration, default-selection, identity, and check operations;
- guided setup offers supported native login when authentication is required and preserves the chosen primary default while adding providers;
- first successful configuration fills only an empty default, later configuration preserves it, and only set-default replaces it;
- configure/check/authentication/start failures never mutate the default or trigger fallback;
- explicit provider routes never fall back;
- OpenClaw commands never mutate user-owned global configuration;
- CLI readbacks show indefinite provider-start retry without a fake maximum; and
- JSON and human output redact credentials and binding material.

## Related

- [Provider selection and runtime config](provider-selection-and-runtime-config.md)
- [Provider support and compatibility](provider-support-and-compatibility.md)
- [Capability, security, and audit](capability-security-and-audit.md)
- [Minimal provider adapter contract](../architecture/adapter-contract.md)
- [Runtime lifecycle and watchdog](../architecture/runtime-lifecycle-and-watchdog.md)
- [ADR-0011: provider routing, defaults, and capability resolution](../../../adr/ADR-0011-provider-routing-defaults-and-capability-resolution.md)
