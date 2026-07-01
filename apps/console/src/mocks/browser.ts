import { setupWorker } from "msw/browser";

import { createConsoleApiHandlers } from "./handlers";
import {
    createConsoleMockScenario,
    createLongRuntimeTaskRow,
    createMixedRuntimeTaskRows,
    createRuntimeFlowSummary,
    createRuntimeFlowSummaryList,
} from "../../tests/fixtures/console-api";
import { createDefinitionSummaryList } from "../../tests/fixtures/definitions";
import {
    SECOND_TASK_START_WORKFLOW_KEY,
    TASK_START_WORKFLOW_KEY,
    createTaskStartWorkflowDetail,
    createTaskStartWorkflowRows,
    createTaskStartWorkflowVersions,
} from "../../tests/fixtures/task-start";

let isStarted = false;

export async function enableMockApi(): Promise<void> {
    if (isStarted) {
        return;
    }

    const worker = setupWorker(...createConsoleApiHandlers(createDevMockScenario()));
    await worker.start({
        onUnhandledRequest: "bypass",
        serviceWorker: {
            url: "/mockServiceWorker.js",
        },
    });

    isStarted = true;
}

function createDevMockScenario() {
    const scenario = createConsoleMockScenario({
        taskList: createRuntimeFlowSummaryList(
            [...createMixedRuntimeTaskRows(), createLongRuntimeTaskRow()],
            "cursor-page-2",
        ),
        taskListPages: {
            "cursor-page-2": createRuntimeFlowSummaryList([
                createRuntimeFlowSummary({
                    status: "succeeded",
                    task_id: "task-second-page",
                    task_summary: "Second cursor page.",
                    task_title: "Review accepted page",
                    updated_at: "2026-06-29T07:00:00Z",
                }),
            ]),
        },
    });

    return {
        ...scenario,
        definitionDetails: {
            ...scenario.definitionDetails,
            [`workflow:${TASK_START_WORKFLOW_KEY}`]:
                createTaskStartWorkflowDetail(TASK_START_WORKFLOW_KEY),
            [`workflow:${SECOND_TASK_START_WORKFLOW_KEY}`]: createTaskStartWorkflowDetail(
                SECOND_TASK_START_WORKFLOW_KEY,
            ),
        },
        definitionLists: {
            ...scenario.definitionLists,
            workflows: createDefinitionSummaryList("workflow", createTaskStartWorkflowRows(), null),
        },
        definitionVersionsByDefinition: {
            ...scenario.definitionVersionsByDefinition,
            [`workflow:${TASK_START_WORKFLOW_KEY}`]:
                createTaskStartWorkflowVersions(TASK_START_WORKFLOW_KEY),
            [`workflow:${SECOND_TASK_START_WORKFLOW_KEY}`]: createTaskStartWorkflowVersions(
                SECOND_TASK_START_WORKFLOW_KEY,
            ),
        },
    };
}
