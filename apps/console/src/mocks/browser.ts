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
    TASK_DETAIL_TASK_ID,
    createTaskDetailMockScenario,
} from "../../tests/fixtures/task-detail";
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
    const taskDetailScenario = createTaskDetailMockScenario();
    const taskListRows = createMixedRuntimeTaskRows()
        .filter((task) => task.task_id !== "task-runtime-copy-refresh")
        .map((task, index) =>
            withRelativeUpdatedAt(task, [29, 48, 60, 120, 135, 160][index] ?? 180),
        );
    const scenario = createConsoleMockScenario({
        commandRunList: taskDetailScenario.commandRunList,
        humanRequestList: taskDetailScenario.humanRequestList,
        snapshot: taskDetailScenario.snapshot,
        taskEvents: taskDetailScenario.taskEvents,
        taskEventStream: taskDetailScenario.taskEventStream,
        taskList: createRuntimeFlowSummaryList(
            [
                createRuntimeFlowSummary({
                    active_attempt_id: taskDetailScenario.taskRead.active_attempt_id,
                    active_flow_revision_id: taskDetailScenario.taskRead.active_flow_revision_id,
                    current_node_key: "copy_update",
                    status: taskDetailScenario.taskRead.status,
                    task_id: TASK_DETAIL_TASK_ID,
                    task_summary: "Update the current task-control labels.",
                    task_title: taskDetailScenario.taskRead.task_title,
                    updated_at: relativeUpdatedAt(6),
                    workflow_key: "runtime_copy_refresh",
                    workflow_manifest_ref: taskDetailScenario.taskRead.workflow_manifest_ref,
                }),
                ...taskListRows,
                withRelativeUpdatedAt(createLongRuntimeTaskRow(), 190),
            ],
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
        taskRead: taskDetailScenario.taskRead,
        trace: taskDetailScenario.trace,
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

function relativeUpdatedAt(minutesAgo: number): string {
    return new Date(Date.now() - minutesAgo * 60_000).toISOString();
}

function withRelativeUpdatedAt<T extends { readonly updated_at: string }>(
    task: T,
    minutesAgo: number,
): T {
    return {
        ...task,
        updated_at: relativeUpdatedAt(minutesAgo),
    };
}
