# Design workflows and instructions

Status: Reference

Use this guide before writing role, policy, or workflow YAML. A good AutoClaw workflow starts from the purpose, evidence path, and completion criteria, then chooses the smallest role and node structure that can prove the work is done.

## Core rule

Design the workflow around the question it must answer:

- what purpose does this run serve?
- what evidence must exist before closure?
- what criteria would make release, retry, or blocked state honest?

Do not start by listing agents. Roles are reusable capabilities. Workflows are purpose-specific evidence paths.

## Choose the simplest shape

Use the lowest-complexity shape that reliably fits the work.

| Shape | Use when | Avoid when |
| --- | --- | --- |
| Single worker | One bounded output and one proof loop are enough. | The work needs review, dependencies, or separate evidence. |
| Sequential chain | Each step depends on the previous step. | Steps can run independently or require backtracking. |
| Purpose routing | Similar requests need different paths. | The distinction is only cosmetic. |
| Parent orchestration | The parent must inspect evidence and choose the next child dynamically. | The sequence is already fixed and small. |
| Parallel specialists | Independent perspectives or independent sections improve confidence. | Outputs must be tightly synchronized at every step. |
| Review loop | Clear criteria allow useful critique and correction. | There is no hard standard to review against. |
| Human checkpoint | A decision, approval, missing input, or risk tradeoff needs human judgment. | The node can proceed from current evidence. |

Complexity adds coordination cost. Add parents, reviewers, or human requests only when they improve evidence quality or safety.

## Separate role, policy, workflow, and task detail

Use each authored object for one kind of truth.

| Object | Owns | Should not own |
| --- | --- | --- |
| Role | reusable capability and mode posture | one task's scope, paths, secrets, or launch detail |
| Policy | budget, retry posture, human request capability, command-run capability | role identity or workflow structure |
| Workflow | node tree, durable consumes, produces, criteria, and node-local guidance | runtime checkpoints, hidden handoffs, or live registry truth |
| Task-compose | concrete launch task, selected workflow, and local roots | reusable behavior rules |

When the same wording could live in several places, prefer the narrowest stable owner. Put reusable behavior in roles or policies. Put purpose-specific evidence flow in the workflow. Put one-off user detail in task-compose.

## Design roles

Write roles as stable specialists:

- name one capability profile, such as `product_planner` or `scope_reviewer`
- keep allowed node kinds narrow
- teach the role what to inspect first
- state what it must publish
- state what it must not do
- avoid task-specific file paths, host setup, or launch details

Good role instructions usually answer:

- what evidence should this worker read first?
- what mode is it in: research, planning, implementation, review, verification, marketing, delivery coordination, or release?
- what output should the parent/root expect?
- what should the worker refuse to widen?

## Design policies

Policies should be behavioral guardrails, not alternate roles.

Use policy instruction for:

- retry or child-assignment budget posture
- when human input is allowed
- when long command runs are allowed
- evidence and checkpoint expectations
- boundaries such as "do not publish externally" or "do not implement"

Keep human request and command-run capabilities separate. A node can have one, both, or neither.

Use human request capability for:

- `direction` when the next path depends on human judgment
- `approval` when work should not continue without explicit permission
- `input` when required facts are missing
- `review` when a human review gate is part of the workflow

Use command-run capability only for controller-managed long-running command work. Ordinary shell commands should stay inline and comfortably under two minutes. If a command is likely to exceed that, use a command-run-enabled policy or redesign the assignment so the worker does not stall the dispatch.

## Design workflows

Author workflows as evidence paths.

Each node should have:

- a purpose in `description`
- optional node-local execution guidance in `instruction`
- required inputs in `consumes`
- required outputs in `produces`
- hard acceptance or guardrail rules in `criteria`

Use `criteria` only for requirements that can block closure. Put softer preferences, review rubrics, and behavior guidance in role, policy, or node instruction.

Use parent nodes when the workflow needs local orchestration:

- the parent must decide which child to assign next
- the parent must inspect child evidence before release
- the subtree may need replan, retry, or failure analysis
- child outputs need coordination before root closure

Use workers when the assignment has one bounded mode and one expected output surface.

## Workflow archetypes

Start with small and medium archetypes. Compose larger workflows from them after the evidence path is proven.

| Archetype | Purpose | Primary artifacts |
| --- | --- | --- |
| Idea discovery | compare directions before committing | discovery context, option brief, scope critique, recommendation |
| Planning only | create an execution plan without building | scope brief, work breakdown, plan review, final plan |
| MVP build | prove core user value with a thin usable slice | MVP scope, patch, demo verification, code review, product-fit review |
| Core-only build | build a foundation layer without full-product scope | core contract plan, patch, verification, review |
| Feature implementation | add a feature to an existing product | context report, integration plan, patch, verification, review |
| Bug fix | reproduce, fix, verify, review, and release one defect | triage report, fix plan, patch, verification, review |
| Marketing campaign | plan campaign work without external publishing | audience research, campaign brief, risk review, campaign package |
| Project management | coordinate delivery without implementation | objectives, work breakdown, risk review, delivery plan |

Similar-looking workflows should still differ when their purpose differs. An MVP build optimizes for proof of value. A core-only build optimizes for durable contracts. A bug fix optimizes for reproduction and regression proof. A marketing campaign optimizes for audience, proof, approvals, and channel fit.

## Instruction checklist

Before saving a definition set, check that the instruction layers answer these questions:

- does the root know what final closure means?
- does each parent know how to route child work and evaluate child evidence?
- does each worker know its bounded mode?
- does each review node have criteria to judge?
- does each implementation node know what not to touch?
- does each planning node explicitly avoid implementation?
- do human request policies state when and why to ask?
- do command-run policies state that normal commands should stay under about two minutes?
- do produced artifacts give later nodes enough evidence without relying on hidden transcript memory?

## Common mistakes

Avoid these patterns:

- one giant workflow that tries to handle every purpose
- a generic assistant role that hides specialist responsibility
- review nodes with no hard criteria
- policies that grant both human requests and command runs by default
- implementation workers that also plan, review, and release
- product or marketing workflows that silently perform external actions
- task-specific paths or secrets inside reusable role and policy definitions
- criteria that read like suggestions instead of closure gates

When in doubt, split the workflow by purpose first, then reduce it until every node has a reason to exist.

