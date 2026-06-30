import { AutoClawApiError, requestJson, type ConsoleErrorView } from "../../api/client";
import type { components } from "../../api/generated/openapi";
import {
    cancelCommandRunRoute,
    commandRunLogRoute,
    commandRunRoute,
    commandRunsRoute,
    controlTaskRoute,
} from "../../api/routes";
import { mapCommandRunDetailView, type CommandRunDetailView } from "./command-run-model";

const COMMAND_RUN_PAGE_SIZE = 25;

export type CommandRunListResponse = components["schemas"]["CommandRunListResponse"];
export type CommandRunCancelResponse = components["schemas"]["CommandRunCancelResponse"];
export type CommandRunLogReadResponse = components["schemas"]["CommandRunLogReadResponse"];

export async function readCommandRunsPageData(
    taskId: string,
    signal: AbortSignal,
): Promise<{
    readonly commandRunList: CommandRunListResponse;
    readonly taskTitle: string | null;
}> {
    const [commandRunList, taskTitle] = await Promise.all([
        readCommandRunPage({ cursor: null, signal, taskId }),
        readCommandRunTaskTitle(taskId, signal),
    ]);

    return { commandRunList, taskTitle };
}

export async function readCommandRunPage({
    cursor,
    signal,
    taskId,
}: {
    readonly cursor: string | null;
    readonly signal: AbortSignal | undefined;
    readonly taskId: string;
}): Promise<CommandRunListResponse> {
    const route = commandRunsRoute(taskId, {
        cursor,
        limit: COMMAND_RUN_PAGE_SIZE,
    });
    return requestJson<CommandRunListResponse>({
        path: route.path,
        query: route.query,
        signal,
    });
}

export async function readCommandRunDetail(
    taskId: string,
    runId: string,
): Promise<CommandRunDetailView> {
    const route = commandRunRoute(taskId, runId);
    const record = await requestJson<components["schemas"]["CommandRunRecord"]>({
        path: route.path,
    });
    return mapCommandRunDetailView(record);
}

export async function readCommandRunLog(
    taskId: string,
    runId: string,
): Promise<CommandRunLogReadResponse> {
    const route = commandRunLogRoute(taskId, runId);
    return requestJson<CommandRunLogReadResponse>({
        path: route.path,
    });
}

async function readCommandRunTaskTitle(
    taskId: string,
    signal: AbortSignal,
): Promise<string | null> {
    const route = controlTaskRoute(taskId);
    try {
        const task = await requestJson<components["schemas"]["RuntimeFlowRead"]>({
            path: route.path,
            signal,
        });
        return task.task_title;
    } catch (error) {
        if (isAbortError(error)) {
            throw error;
        }

        return null;
    }
}

export async function cancelCommandRun(
    taskId: string,
    runId: string,
): Promise<CommandRunCancelResponse> {
    const route = cancelCommandRunRoute(taskId, runId);
    return requestJson<CommandRunCancelResponse>({
        method: "POST",
        path: route.path,
    });
}

export function toErrorView(error: unknown): ConsoleErrorView {
    if (error instanceof AutoClawApiError) {
        return error.errorView;
    }

    return {
        code: "unknown_error",
        fieldErrors: [],
        isRetryable: false,
        source: "network",
        status: null,
        suggestedNextStep: null,
        summary: error instanceof Error ? error.message : "An unknown console error occurred.",
        title: "Unknown Error",
    };
}

export function isAbortError(error: unknown): boolean {
    return error instanceof Error && error.name === "AbortError";
}
