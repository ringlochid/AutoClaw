import { getConsoleConfig, type ConsoleConfig } from "../app/config";

import {
    AutoClawApiError,
    createApiErrorFromResponse,
    createApiTransportError,
    isCursorResetError,
    resolveApiUrl,
    type ConsoleErrorView,
} from "./client";
import type { components } from "./generated/openapi";

export interface ServerSentEventFrame {
    readonly data: string;
    readonly event: string | null;
    readonly id: string | null;
}

export interface TaskEventStreamRequest {
    readonly headers: Headers;
    readonly url: URL;
}

export interface TaskEventStreamOptions {
    readonly config?: ConsoleConfig;
    readonly cursor?: string | null;
    readonly fetchImpl?: typeof fetch;
    readonly onEvent?: (event: components["schemas"]["TaskEventRecord"]) => void;
    readonly signal?: AbortSignal;
    readonly taskId: string;
}

export interface TaskEventStreamReadResult {
    readonly cursorResetRequired: boolean;
    readonly didResetCursor: boolean;
    readonly error: ConsoleErrorView | null;
    readonly events: readonly components["schemas"]["TaskEventRecord"][];
    readonly lastEventId: string | null;
    readonly staleCursor: string | null;
}

export interface TaskEventStreamReconnectOptions extends TaskEventStreamOptions {
    readonly resetAfterCursorReset: (
        staleCursor: string | null,
    ) => Promise<string | null> | string | null;
}

export function taskEventStreamUrl(
    taskId: string,
    options: {
        readonly config?: ConsoleConfig;
        readonly cursor?: string | null;
    } = {},
): string {
    return buildTaskEventStreamRequest(taskId, options).url.toString();
}

export function buildTaskEventStreamRequest(
    taskId: string,
    options: {
        readonly config?: ConsoleConfig;
        readonly cursor?: string | null;
    } = {},
): TaskEventStreamRequest {
    const config = options.config ?? getConsoleConfig();
    const url = resolveApiUrl(
        `/control/tasks/${encodeURIComponent(taskId)}/events/stream`,
        config,
        options.cursor === null || options.cursor === undefined
            ? undefined
            : { cursor: options.cursor },
    );
    const headers = new Headers({ Accept: "text/event-stream" });

    return { headers, url };
}

export async function readTaskEventStream({
    config = getConsoleConfig(),
    cursor = null,
    fetchImpl = fetch,
    onEvent,
    signal,
    taskId,
}: TaskEventStreamOptions): Promise<TaskEventStreamReadResult> {
    const request = buildTaskEventStreamRequest(taskId, { config, cursor });
    let response: Response;
    try {
        response = await fetchImpl(request.url, {
            headers: request.headers,
            method: "GET",
            signal,
        });
    } catch (error) {
        throw createApiTransportError(error);
    }

    if (!response.ok) {
        const apiError = await createApiErrorFromResponse(response);
        if (isCursorResetError(apiError.errorView)) {
            return {
                cursorResetRequired: true,
                didResetCursor: false,
                error: apiError.errorView,
                events: [],
                lastEventId: null,
                staleCursor: cursor,
            };
        }
        throw apiError;
    }

    if (response.body === null) {
        return {
            cursorResetRequired: false,
            didResetCursor: false,
            error: null,
            events: [],
            lastEventId: null,
            staleCursor: null,
        };
    }

    const seenEventIds = new Set<string>();
    const events: components["schemas"]["TaskEventRecord"][] = [];

    for await (const frame of readServerSentEventFrames(response.body, signal)) {
        const event = readTaskEventFromFrame(frame);
        if (event === null || seenEventIds.has(event.event_id)) {
            continue;
        }

        seenEventIds.add(event.event_id);
        events.push(event);
        onEvent?.(event);
        if (signal?.aborted) {
            break;
        }
    }

    const orderedEvents = mergeTaskEvents(events);
    return {
        cursorResetRequired: false,
        didResetCursor: false,
        error: null,
        events: orderedEvents,
        lastEventId: lastTaskEventCursor(orderedEvents),
        staleCursor: null,
    };
}

export async function reconnectTaskEventStream(
    options: TaskEventStreamReconnectOptions,
): Promise<TaskEventStreamReadResult> {
    const firstResult = await readTaskEventStream(options);
    if (!firstResult.cursorResetRequired) {
        return firstResult;
    }

    const refreshedStreamHead = await options.resetAfterCursorReset(firstResult.staleCursor);
    const secondResult = await readTaskEventStream({
        ...options,
        cursor: refreshedStreamHead,
    });
    return {
        ...secondResult,
        didResetCursor: true,
        staleCursor: firstResult.staleCursor,
    };
}

export async function* readServerSentEventFrames(
    body: ReadableStream<Uint8Array>,
    signal?: AbortSignal,
): AsyncGenerator<ServerSentEventFrame> {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
        while (!signal?.aborted) {
            const readResult = await reader.read();
            buffer += decoder.decode(readResult.value, { stream: !readResult.done });

            let boundary = findFrameBoundary(buffer);
            while (boundary !== null && !signal?.aborted) {
                const rawFrame = buffer.slice(0, boundary.index);
                buffer = buffer.slice(boundary.index + boundary.length);
                const frame = parseServerSentEventFrame(rawFrame);
                if (frame !== null) {
                    yield frame;
                }
                boundary = findFrameBoundary(buffer);
            }

            if (readResult.done) {
                break;
            }
        }

        if (buffer.trim() !== "" && !signal?.aborted) {
            const frame = parseServerSentEventFrame(buffer);
            if (frame !== null) {
                yield frame;
            }
        }
    } finally {
        reader.releaseLock();
    }
}

export function parseServerSentEventFrame(rawFrame: string): ServerSentEventFrame | null {
    const dataLines: string[] = [];
    let event: string | null = null;
    let id: string | null = null;

    for (const line of rawFrame.split(/\r?\n/)) {
        if (line === "" || line.startsWith(":")) {
            continue;
        }

        const separatorIndex = line.indexOf(":");
        const field = separatorIndex === -1 ? line : line.slice(0, separatorIndex);
        const rawValue = separatorIndex === -1 ? "" : line.slice(separatorIndex + 1);
        const value = rawValue.startsWith(" ") ? rawValue.slice(1) : rawValue;

        if (field === "data") {
            dataLines.push(value);
        } else if (field === "event") {
            event = value;
        } else if (field === "id") {
            id = value;
        }
    }

    if (dataLines.length === 0 && event === null && id === null) {
        return null;
    }

    return {
        data: dataLines.join("\n"),
        event,
        id,
    };
}

export function mergeTaskEvents(
    ...eventBatches: readonly (readonly components["schemas"]["TaskEventRecord"][])[]
): readonly components["schemas"]["TaskEventRecord"][] {
    const eventById = new Map<string, components["schemas"]["TaskEventRecord"]>();
    for (const eventBatch of eventBatches) {
        for (const event of eventBatch) {
            eventById.set(event.event_id, event);
        }
    }

    return [...eventById.values()].sort((left, right) => left.event_seq - right.event_seq);
}

export function lastTaskEventCursor(
    events: readonly components["schemas"]["TaskEventRecord"][],
): string | null {
    return events.at(-1)?.event_id ?? null;
}

function readTaskEventFromFrame(
    frame: ServerSentEventFrame,
): components["schemas"]["TaskEventRecord"] | null {
    if (frame.data.trim() === "") {
        return null;
    }

    const parsedData = parseJsonFrameData(frame.data);
    if (!isTaskEventRecord(parsedData)) {
        throw new AutoClawApiError({
            code: "invalid_sse_event",
            title: "Invalid SSE Event",
            summary:
                "The task event stream returned an event that did not match the task-event shape.",
            status: null,
            isRetryable: true,
            suggestedNextStep: "Reconnect to the task event stream.",
            fieldErrors: [],
            source: "network",
        });
    }

    if (frame.id !== null && frame.id !== parsedData.event_id) {
        throw new AutoClawApiError({
            code: "conflicting_sse_event_id",
            title: "Conflicting SSE Event Id",
            summary: "The task event stream frame id did not match the payload event id.",
            status: null,
            isRetryable: true,
            suggestedNextStep: "Reconnect to the task event stream.",
            fieldErrors: [],
            source: "network",
        });
    }

    if (frame.event !== null && frame.event !== parsedData.event_type) {
        throw new AutoClawApiError({
            code: "conflicting_sse_event_type",
            title: "Conflicting SSE Event Type",
            summary: "The task event stream frame type did not match the payload event type.",
            status: null,
            isRetryable: true,
            suggestedNextStep: "Reconnect to the task event stream.",
            fieldErrors: [],
            source: "network",
        });
    }

    return parsedData;
}

function parseJsonFrameData(data: string): unknown {
    try {
        return JSON.parse(data) as unknown;
    } catch {
        return null;
    }
}

function isTaskEventRecord(value: unknown): value is components["schemas"]["TaskEventRecord"] {
    if (!isRecord(value)) {
        return false;
    }

    return (
        typeof value.event_id === "string" &&
        typeof value.event_seq === "number" &&
        typeof value.task_id === "string" &&
        typeof value.event_type === "string" &&
        typeof value.event_source === "string" &&
        typeof value.occurred_at === "string" &&
        typeof value.event_hash === "string"
    );
}

function findFrameBoundary(
    buffer: string,
): { readonly index: number; readonly length: number } | null {
    const lineFeedBoundary = buffer.indexOf("\n\n");
    const carriageBoundary = buffer.indexOf("\r\n\r\n");

    if (lineFeedBoundary === -1 && carriageBoundary === -1) {
        return null;
    }

    if (lineFeedBoundary === -1) {
        return { index: carriageBoundary, length: 4 };
    }

    if (carriageBoundary === -1 || lineFeedBoundary < carriageBoundary) {
        return { index: lineFeedBoundary, length: 2 };
    }

    return { index: carriageBoundary, length: 4 };
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}
