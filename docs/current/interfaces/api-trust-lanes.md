# Current operator roles and API trust lanes

Status: Current

Last verified: 2026-04-26

This page owns the exact current operator definition, trust-lane split, and the difference between operator, worker, controller, parent, and provider in the current system.

For the exact current path families and route nouns, see `api-surface-and-route-map.md`.

## `CurrentOperatorDefinitionContract`

In the current system, `operator` means a trusted principal allowed to inspect or steer runtime state through operator-facing surfaces.

An operator may be:

- a human using browser or CLI surfaces
- a trusted external automation client authenticated into operator surfaces

Operator is defined by authority and allowed actions, not by embodiment alone.

## `CurrentUserVsOperatorContract`

- `user` initiates or owns business work such as task start or upload
- `operator` inspects, controls, unblocks, retries, resolves approval, or otherwise steers runtime state

The same human may play both roles, but the authority is different.

## `RoleBoundaryMatrix`

| Role         | Current meaning                                                  | Owns                                                                                | Does not own                                             |
| ------------ | ---------------------------------------------------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------------------- |
| `user`       | business/task initiator                                          | task brief, upload intent, start intent                                             | runtime steering by default                              |
| `operator`   | trusted runtime steering principal                               | inspect, continue, pause, cancel, retry, approval resolve, watchdog recovery review | bounded delegated execution, runtime truth               |
| `worker`     | delegated node worker                                            | callbacks, bounded outputs, context publication, replan request                     | operator control, broad audit, guarded writes by default |
| `controller` | runtime truth owner                                              | durable state transitions, boundary loop, manifests, attempts, approvals, sessions  | delegated execution content                              |
| `parent`     | authored structural parent, flattened into runtime metadata only | current authored hierarchy metadata                                                 | first-class target-style `parent.gate` authority         |
| `provider`   | transport adapter such as OpenClaw                               | session routing and execution transport                                             | controller truth or operator authority                   |

`worker` is never `operator`.

`parent` is not `operator`.

## `OperatorLaneMatrix`

| Lane                 | Typical caller                                                          | Current capability level                                                                          | Notes                                          |
| -------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| public/operator lane | operator                                                                | inspect, continue, pause, cancel, retry, approval resolve, operator summary reads                 | standard operator lane                         |
| deeper internal lane | controller, bridge plugin, trusted operator tooling, trusted automation | runtime slice, timeline, audit, worker-bundle reads, watchdog control, internal approval creation | mixed lane; not every caller on it is operator |
| browser bootstrap    | browser console                                                         | auth/bootstrap only                                                                               | not a reusable operator secret lane            |
| worker callback lane | delegated worker                                                        | bounded callback mutation only                                                                    | explicitly non-operator                        |

Lane and role are not identical in the current system.

The internal lane is primarily a callback/controller lane, but trusted operator tooling may use deeper query or control surfaces on that same lane.

## Current trust lanes

### 1. Public/operator API

Protected by `X-AutoClaw-API-Key` via `require_api_key`.

Current grouped surfaces:

- `/flows/*`
- `/tasks/*`
- `/approvals/*`
- `/registry/*`

Current operator actions on this lane include:

- flow inspect and operator snapshot
- continue, pause, cancel
- node retry when eligible
- approval read and resolve
- operator-facing registry reads and selected writes

### 2. Internal callback/controller lane with deeper operator tooling

Protected by `X-AutoClaw-API-Key` via `require_internal_api_key`.

Current grouped surfaces:

- `/internal/flows/*`
- `/internal/approvals/*`
- `/internal/registry/*`
- `/internal/tasks/*`
- `/internal/compiler/*`

Current lane uses include:

- controller mutation
- worker callback mutation
- watchdog and dispatch control
- deeper audit and query
- trusted operator tooling or trusted automation when deeper runtime drilldown is needed

This lane is not a browser operator lane and is not equivalent to the operator role by itself. It is also current implementation truth only; the redesign later splits this mixed namespace into `/callback/...` and `/observability/...`.

### 3. Browser bootstrap

`GET /console/config`

Current hardening rule:

- bootstrap teaches the browser how to authenticate
- it does not provide a reusable operator secret

## `CurrentOperatorActionTable`

| Operator action                      | Current lane         | Current effect                                                            |
| ------------------------------------ | -------------------- | ------------------------------------------------------------------------- |
| inspect flow summary                 | public/operator      | read `GET /flows/{flow_id}` or `/flows/{flow_id}/operator`                |
| continue flow                        | public/operator      | re-enter `advance_flow_until_boundary(...)` and then attempt dispatch     |
| pause flow                           | public/operator      | pause open nodes and block active session progress                        |
| cancel flow                          | public/operator      | cancel open attempts, end sessions, expire approvals, supersede manifests |
| retry node                           | public/operator      | only when current retry rule allows it                                    |
| resolve approval                     | public/operator      | apply approval outcome, then re-enter `advance_flow_until_boundary(...)`  |
| inspect runtime slice or audit       | deeper internal lane | read richer assembled views over runtime truth                            |
| inspect or trigger watchdog recovery | deeper internal lane | run or inspect watchdog control paths                                     |
| inspect registry snapshot            | deeper internal lane | read deeper registry/runtime support views                                |

## `CurrentOperatorNegativeRule`

Operator is not:

- the worker
- the controller
- the provider
- the authored structural parent
- an ordinary browser user without trusted auth

## Evidence

- inspected code in `autoclaw-main/apps/api/app/api/router.py`
- inspected code in `autoclaw-main/apps/api/app/api/routes/flows.py`
- inspected code in `autoclaw-main/apps/api/app/api/routes/approvals.py`
- inspected code in `autoclaw-main/apps/api/app/runtime/control.py`
- inspected source-pack docs in `../../archive/source-packs/old_version_docs/api-route-trust-lanes.md`
