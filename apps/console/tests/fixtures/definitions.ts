import type { components } from "../../src/api/generated/openapi";
import { TEST_UPDATED_AT } from "./console-api";

export const DEFINITIONS_SCREENSHOT_DIR =
    "/home/ubuntu/leo/projects/autoclaw/tmp/autoclaw-frontend/continuation-implementation/12-definitions/screenshots";

export const ROLE_KEY = "planning_lead";
export const SECOND_ROLE_KEY = "frontend_engineer";
export const POLICY_KEY = "standard-worker-command-run";
export const WORKFLOW_KEY = "frontend-console-continuation";

export function createDefinitionSummaryList(
    kind: components["schemas"]["DefinitionKind"],
    items: readonly components["schemas"]["DefinitionSummaryRead"][],
    nextCursor: string | null = null,
): components["schemas"]["DefinitionSummaryListResponse"] {
    return {
        items: [...items],
        kind,
        next_cursor: nextCursor,
    };
}

export function createRoleDefinitionRows(): readonly components["schemas"]["DefinitionSummaryRead"][] {
    return [
        {
            allowed_node_kinds: ["parent"],
            applies_to: null,
            budget_spec: null,
            current_revision_no: 4,
            description: "Parent/root coordinator for one owned subtree.",
            key: ROLE_KEY,
            labels: ["authoring"],
            title: "planning_lead",
            updated_at: "2026-06-29T14:10:00Z",
        },
        {
            allowed_node_kinds: ["worker"],
            applies_to: null,
            budget_spec: null,
            current_revision_no: 3,
            description: "Worker for one bounded frontend implementation slice.",
            key: SECOND_ROLE_KEY,
            labels: ["authoring"],
            title: "frontend_engineer",
            updated_at: "2026-06-29T13:45:00Z",
        },
    ];
}

export function createPolicyDefinitionRows(): readonly components["schemas"]["DefinitionSummaryRead"][] {
    return [
        {
            allowed_node_kinds: null,
            applies_to: ["worker"],
            budget_spec: {
                child_assignment_limit: null,
                retry_limit: 2,
            },
            current_revision_no: 5,
            description: "Guardrails for worker assignments that may need command runs.",
            key: POLICY_KEY,
            labels: ["authoring"],
            title: "standard-worker-command-run",
            updated_at: "2026-06-29T14:05:00Z",
        },
    ];
}

export function createWorkflowDefinitionRows(): readonly components["schemas"]["DefinitionSummaryRead"][] {
    return [
        {
            allowed_node_kinds: null,
            applies_to: null,
            budget_spec: null,
            current_revision_no: 6,
            description: "Continue AutoClaw console frontend delivery.",
            key: WORKFLOW_KEY,
            labels: ["authoring"],
            title: "frontend-console-continuation",
            updated_at: "2026-06-29T14:00:00Z",
        },
    ];
}

export function createRoleDefinitionDetail(
    key = ROLE_KEY,
): components["schemas"]["DefinitionRevisionDetailResponse"] {
    return {
        content: {
            allowed_node_kinds: key === ROLE_KEY ? ["parent"] : ["worker"],
            description:
                key === ROLE_KEY
                    ? "Parent/root coordinator for one owned subtree."
                    : "Worker for one bounded frontend implementation slice.",
            id: key,
            instruction:
                key === ROLE_KEY
                    ? "Coordinate only the current owned subtree.\nUse current assignments and checkpoints."
                    : "Implement only the current meaningful frontend scope.",
            labels: ["authoring"],
            title: key,
        },
        key,
        recorded_by: null,
        revision_no: key === ROLE_KEY ? 4 : 3,
        updated_at: TEST_UPDATED_AT,
    };
}

export function createPolicyDefinitionDetail(): components["schemas"]["DefinitionRevisionDetailResponse"] {
    return {
        content: {
            applies_to: ["worker"],
            budget_spec: {
                child_assignment_limit: null,
                retry_limit: 2,
            },
            capabilities: {
                command_run: "allow",
                human_request: {
                    allowed_kinds: [],
                    mode: "deny",
                },
            },
            description: "Guardrails for worker assignments that may need command runs.",
            id: POLICY_KEY,
            instruction:
                "Use controller-managed command runs only for commands expected to exceed the inline worker window.",
            labels: ["authoring"],
            title: POLICY_KEY,
        },
        key: POLICY_KEY,
        recorded_by: null,
        revision_no: 5,
        updated_at: TEST_UPDATED_AT,
    };
}

export function createWorkflowDefinitionDetail(): components["schemas"]["DefinitionRevisionDetailResponse"] {
    return {
        content: {
            description: "Continue AutoClaw console frontend delivery.",
            id: WORKFLOW_KEY,
            root: {
                child_defaults: null,
                children: [
                    {
                        child_defaults: null,
                        children: [
                            {
                                child_defaults: null,
                                children: null,
                                consumes: null,
                                criteria: null,
                                description: "Review one frontend scope.",
                                id: "review_frontend_scope",
                                instruction: "Review the current scope patch strictly.",
                                policy: "standard-worker-command-run",
                                produces: null,
                                provider_preference: null,
                                role: "frontend_code_reviewer",
                                title: "Review frontend scope",
                            },
                        ],
                        consumes: null,
                        criteria: null,
                        description: "Implement one meaningful frontend scope.",
                        id: "implement_frontend_scope",
                        instruction: "Implement only the assigned UI slice.",
                        policy: "standard-worker-command-run",
                        produces: null,
                        provider_preference: null,
                        role: "frontend_engineer",
                        title: "Implement frontend scope",
                    },
                ],
                criteria: null,
                description: "Coordinate implementation and release.",
                id: "root",
                instruction: "Dispatch implementation and review scopes.",
                policy: "standard-parent",
                produces: null,
                provider_preference: null,
                role: "planning_lead",
                title: "Root",
            },
        },
        key: WORKFLOW_KEY,
        recorded_by: null,
        revision_no: 6,
        updated_at: TEST_UPDATED_AT,
    };
}

export function createDefinitionVersions(
    kind: components["schemas"]["DefinitionKind"] = "role",
    key = ROLE_KEY,
    options: {
        readonly currentRevisionNo?: number;
        readonly nextCursor?: string | null;
        readonly revisions?: readonly number[];
    } = {},
): components["schemas"]["DefinitionRevisionHistoryResponse"] {
    const revisions = options.revisions ?? [options.currentRevisionNo ?? 4, 3, 2];
    return {
        current_revision_no: options.currentRevisionNo ?? revisions[0],
        items: revisions.map((revisionNo, index) => ({
            recorded_by: null,
            revision_no: revisionNo,
            updated_at: `2026-06-${String(29 - index).padStart(2, "0")}T14:00:00Z`,
        })),
        key,
        kind,
        next_cursor: options.nextCursor ?? null,
    };
}

export function createDefinitionDetailMap(): Record<
    string,
    components["schemas"]["DefinitionRevisionDetailResponse"]
> {
    return {
        [`policy:${POLICY_KEY}`]: createPolicyDefinitionDetail(),
        [`role:${ROLE_KEY}`]: createRoleDefinitionDetail(ROLE_KEY),
        [`role:${SECOND_ROLE_KEY}`]: createRoleDefinitionDetail(SECOND_ROLE_KEY),
        [`workflow:${WORKFLOW_KEY}`]: createWorkflowDefinitionDetail(),
    };
}

export function createDefinitionVersionsMap(): Record<
    string,
    components["schemas"]["DefinitionRevisionHistoryResponse"]
> {
    return {
        [`policy:${POLICY_KEY}`]: createDefinitionVersions("policy", POLICY_KEY, {
            currentRevisionNo: 5,
            revisions: [5],
        }),
        [`role:${ROLE_KEY}`]: createDefinitionVersions("role", ROLE_KEY),
        [`role:${SECOND_ROLE_KEY}`]: createDefinitionVersions("role", SECOND_ROLE_KEY, {
            currentRevisionNo: 3,
            revisions: [3],
        }),
        [`workflow:${WORKFLOW_KEY}`]: createDefinitionVersions("workflow", WORKFLOW_KEY, {
            currentRevisionNo: 6,
            revisions: [6, 5],
        }),
    };
}
