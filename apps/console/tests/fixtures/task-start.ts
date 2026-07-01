import type { components } from "../../src/api/generated/openapi";
import {
    WORKFLOW_KEY,
    createDefinitionVersions,
    createWorkflowDefinitionDetail,
    createWorkflowDefinitionRows,
} from "./definitions";

export const TASK_START_SCREENSHOT_DIR =
    "/home/ubuntu/leo/projects/autoclaw/tmp/autoclaw-frontend/full-delivery-design-parity/06-task-start/screenshots";

export const TASK_START_WORKFLOW_KEY = WORKFLOW_KEY;
export const SECOND_TASK_START_WORKFLOW_KEY = "normal-parent-first-release";

export function createTaskStartWorkflowRows(): readonly components["schemas"]["DefinitionSummaryRead"][] {
    return [
        ...createWorkflowDefinitionRows(),
        {
            allowed_node_kinds: null,
            applies_to: null,
            budget_spec: null,
            current_revision_no: 3,
            description:
                "Execute one implementation subtree, review it, then release from current evidence.",
            key: SECOND_TASK_START_WORKFLOW_KEY,
            labels: ["authoring"],
            title: "normal-parent-first-release",
            updated_at: "2026-06-29T13:30:00Z",
        },
    ];
}

export function createTaskStartWorkflowDetail(
    key = TASK_START_WORKFLOW_KEY,
): components["schemas"]["DefinitionRevisionDetailResponse"] {
    if (key === SECOND_TASK_START_WORKFLOW_KEY) {
        return {
            content: {
                description:
                    "Execute one implementation subtree, review it, then release from current evidence.",
                id: SECOND_TASK_START_WORKFLOW_KEY,
                root: {
                    child_defaults: null,
                    children: null,
                    criteria: null,
                    description: "Coordinate the release lane.",
                    id: "root",
                    instruction: "Run one parent-first release sequence.",
                    policy: "standard-parent",
                    produces: null,
                    provider_preference: null,
                    role: "planning_lead",
                    title: "Root",
                },
            },
            key,
            recorded_by: null,
            revision_no: 3,
            updated_at: "2026-06-29T13:30:00Z",
        };
    }

    return createWorkflowDefinitionDetail();
}

export function createTaskStartWorkflowVersions(
    key = TASK_START_WORKFLOW_KEY,
): components["schemas"]["DefinitionRevisionHistoryResponse"] {
    return createDefinitionVersions("workflow", key, {
        currentRevisionNo: key === SECOND_TASK_START_WORKFLOW_KEY ? 3 : 6,
        revisions: key === SECOND_TASK_START_WORKFLOW_KEY ? [3, 2] : [6, 5],
    });
}
