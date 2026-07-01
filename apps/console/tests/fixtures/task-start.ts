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
    return createWorkflowDefinitionRows();
}

export function createTaskStartWorkflowDetail(
    key = TASK_START_WORKFLOW_KEY,
): components["schemas"]["DefinitionRevisionDetailResponse"] {
    return createWorkflowDefinitionDetail(key);
}

export function createTaskStartWorkflowVersions(
    key = TASK_START_WORKFLOW_KEY,
): components["schemas"]["DefinitionRevisionHistoryResponse"] {
    return createDefinitionVersions("workflow", key, {
        currentRevisionNo: key === SECOND_TASK_START_WORKFLOW_KEY ? 3 : 5,
        revisions: key === SECOND_TASK_START_WORKFLOW_KEY ? [3, 2] : [5, 4],
    });
}
