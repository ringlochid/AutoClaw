import { useCallback, useEffect, useMemo, useReducer, useRef } from "react";

import { AutoClawApiError, type ConsoleErrorView } from "../../api/client";
import type { components } from "../../api/generated/openapi";
import { mergeTaskEvents } from "../../api/sse";
import {
    readTaskDetailBootstrap,
    streamTaskDetailEvents,
    writeTaskControlAction,
    type TaskControlAction,
    type TaskDetailBootstrap,
} from "./task-detail-data";
import {
    buildSelectedContext,
    buildTaskDetailView,
    getDefaultEventId,
    getDefaultNodeKey,
    type TaskDetailTab,
    type TaskDetailView,
} from "./task-detail-model";

export type TaskEventStreamStatus = "closed" | "connecting" | "live" | "reconnecting" | "reset";

export interface TaskDetailController {
    readonly actionError: ConsoleErrorView | null;
    readonly actionPending: TaskControlAction | null;
    readonly closeDetail: () => void;
    readonly detailOpen: boolean;
    readonly error: ConsoleErrorView | null;
    readonly isLoading: boolean;
    readonly isRefreshing: boolean;
    readonly openDetail: () => void;
    readonly refresh: () => void;
    readonly resetGraph: () => void;
    readonly selectedContext: ReturnType<typeof buildSelectedContext> | null;
    readonly selectedEventId: string | null;
    readonly selectedNodeKey: string | null;
    readonly selectEvent: (eventId: string) => void;
    readonly selectNode: (nodeKey: string) => void;
    readonly setDetailTab: (tab: TaskDetailTab) => void;
    readonly streamError: ConsoleErrorView | null;
    readonly streamResetStaleCursor: string | null;
    readonly streamStatus: TaskEventStreamStatus;
    readonly tab: TaskDetailTab;
    readonly taskAction: (action: TaskControlAction) => void;
    readonly view: TaskDetailView | null;
    readonly zoomIn: () => void;
    readonly zoomOut: () => void;
    readonly zoomPercent: number;
}

interface TaskDetailState {
    readonly actionError: ConsoleErrorView | null;
    readonly actionPending: TaskControlAction | null;
    readonly bootstrap: TaskDetailBootstrap | null;
    readonly detailOpen: boolean;
    readonly error: ConsoleErrorView | null;
    readonly events: readonly components["schemas"]["TaskEventRecord"][];
    readonly isLoading: boolean;
    readonly isRefreshing: boolean;
    readonly refreshToken: number;
    readonly selectedEventId: string | null;
    readonly selectedNodeKey: string | null;
    readonly streamError: ConsoleErrorView | null;
    readonly streamResetStaleCursor: string | null;
    readonly streamStatus: TaskEventStreamStatus;
    readonly tab: TaskDetailTab;
    readonly zoomPercent: number;
}

type TaskDetailAction =
    | { readonly type: "action-error"; readonly error: ConsoleErrorView }
    | { readonly action: TaskControlAction; readonly type: "action-start" }
    | { readonly task: components["schemas"]["RuntimeFlowRead"]; readonly type: "action-success" }
    | {
          readonly bootstrap: TaskDetailBootstrap;
          readonly isRefresh: boolean;
          readonly type: "bootstrap-success";
      }
    | { readonly isRefresh: boolean; readonly type: "load-start" }
    | { readonly error: ConsoleErrorView; readonly type: "load-error" }
    | { readonly type: "close-detail" }
    | { readonly event: components["schemas"]["TaskEventRecord"]; readonly type: "live-event" }
    | {
          readonly events: readonly components["schemas"]["TaskEventRecord"][];
          readonly type: "live-events";
      }
    | { readonly type: "open-detail" }
    | { readonly type: "refresh" }
    | { readonly type: "reset-graph" }
    | { readonly eventId: string; readonly type: "select-event" }
    | { readonly nodeKey: string; readonly type: "select-node" }
    | { readonly status: TaskEventStreamStatus; readonly type: "stream-status" }
    | { readonly staleCursor: string | null; readonly type: "stream-reset" }
    | { readonly error: ConsoleErrorView; readonly type: "stream-error" }
    | { readonly tab: TaskDetailTab; readonly type: "tab" }
    | { readonly type: "zoom-in" }
    | { readonly type: "zoom-out" };

const initialState: TaskDetailState = {
    actionError: null,
    actionPending: null,
    bootstrap: null,
    detailOpen: false,
    error: null,
    events: [],
    isLoading: true,
    isRefreshing: false,
    refreshToken: 0,
    selectedEventId: null,
    selectedNodeKey: null,
    streamError: null,
    streamResetStaleCursor: null,
    streamStatus: "closed",
    tab: "overview",
    zoomPercent: 100,
};

const MIN_ZOOM_PERCENT = 75;
const MAX_ZOOM_PERCENT = 175;

export function useTaskDetailController(taskId: string | null): TaskDetailController {
    const [state, dispatch] = useReducer(taskDetailReducer, initialState);
    const hasBootstrapRef = useRef(false);
    const lastTaskIdRef = useRef<string | null>(null);

    useEffect(() => {
        if (taskId === null) {
            dispatch({
                error: {
                    code: "missing_task_id",
                    fieldErrors: [],
                    isRetryable: false,
                    source: "http",
                    status: null,
                    suggestedNextStep: "Open Task Detail from a task row.",
                    summary: "Task Detail requires a task id in the route.",
                    title: "Missing Task Id",
                },
                type: "load-error",
            });
            return;
        }

        const currentTaskId = taskId;
        const abortController = new AbortController();
        if (lastTaskIdRef.current !== currentTaskId) {
            hasBootstrapRef.current = false;
            lastTaskIdRef.current = currentTaskId;
        }
        const isRefresh = hasBootstrapRef.current;

        async function runTaskDetailRead(): Promise<void> {
            dispatch({ isRefresh, type: "load-start" });
            try {
                const bootstrap = await readTaskDetailBootstrap(
                    currentTaskId,
                    abortController.signal,
                );
                hasBootstrapRef.current = true;
                dispatch({ bootstrap, isRefresh, type: "bootstrap-success" });
                dispatch({ status: "connecting", type: "stream-status" });

                const streamCursor = bootstrap.snapshot.stream_head_event_id ?? null;
                const streamResult = await streamTaskDetailEvents({
                    cursor: streamCursor,
                    onEvent: (event) => {
                        dispatch({ event, type: "live-event" });
                    },
                    resetAfterCursorReset: async (staleCursor) => {
                        dispatch({ staleCursor, type: "stream-reset" });
                        const resetBootstrap = await readTaskDetailBootstrap(
                            currentTaskId,
                            abortController.signal,
                        );
                        hasBootstrapRef.current = true;
                        dispatch({
                            bootstrap: resetBootstrap,
                            isRefresh: true,
                            type: "bootstrap-success",
                        });
                        dispatch({ status: "reconnecting", type: "stream-status" });
                    },
                    signal: abortController.signal,
                    taskId: currentTaskId,
                });

                if (streamResult.events.length > 0) {
                    dispatch({ events: streamResult.events, type: "live-events" });
                }
                if (streamResult.didResetCursor) {
                    dispatch({
                        staleCursor: streamResult.staleCursor,
                        type: "stream-reset",
                    });
                } else {
                    dispatch({ status: "live", type: "stream-status" });
                }
            } catch (error) {
                if (isAbortError(error)) {
                    return;
                }
                if (!hasBootstrapRef.current) {
                    dispatch({ error: toErrorView(error), type: "load-error" });
                    return;
                }
                dispatch({ error: toErrorView(error), type: "stream-error" });
            }
        }

        void runTaskDetailRead();

        return () => {
            abortController.abort();
        };
    }, [state.refreshToken, taskId]);

    const view = useMemo(() => {
        if (state.bootstrap === null) {
            return null;
        }

        return buildTaskDetailView({
            bootstrap: state.bootstrap,
            events: state.events,
        });
    }, [state.bootstrap, state.events]);

    const selectedContext = useMemo(() => {
        if (view === null) {
            return null;
        }

        return buildSelectedContext({
            eventId: state.selectedEventId,
            nodeKey: state.selectedNodeKey,
            view,
        });
    }, [state.selectedEventId, state.selectedNodeKey, view]);

    const taskAction = useCallback(
        (action: TaskControlAction) => {
            if (state.bootstrap === null || taskId === null) {
                return;
            }

            dispatch({ action, type: "action-start" });
            void writeTaskControlAction({
                action,
                activeFlowRevisionId: state.bootstrap.task.active_flow_revision_id,
                taskId,
            })
                .then((task) => {
                    dispatch({ task, type: "action-success" });
                })
                .catch((error: unknown) => {
                    if (isAbortError(error)) {
                        return;
                    }
                    dispatch({ error: toErrorView(error), type: "action-error" });
                });
        },
        [state.bootstrap, taskId],
    );

    return {
        actionError: state.actionError,
        actionPending: state.actionPending,
        closeDetail: () => {
            dispatch({ type: "close-detail" });
        },
        detailOpen: state.detailOpen,
        error: state.error,
        isLoading: state.isLoading,
        isRefreshing: state.isRefreshing,
        openDetail: () => {
            dispatch({ type: "open-detail" });
        },
        refresh: () => {
            dispatch({ type: "refresh" });
        },
        resetGraph: () => {
            dispatch({ type: "reset-graph" });
        },
        selectedContext,
        selectedEventId: state.selectedEventId,
        selectedNodeKey: state.selectedNodeKey,
        selectEvent: (eventId) => {
            dispatch({ eventId, type: "select-event" });
        },
        selectNode: (nodeKey) => {
            dispatch({ nodeKey, type: "select-node" });
        },
        setDetailTab: (tab) => {
            dispatch({ tab, type: "tab" });
        },
        streamError: state.streamError,
        streamResetStaleCursor: state.streamResetStaleCursor,
        streamStatus: state.streamStatus,
        tab: state.tab,
        taskAction,
        view,
        zoomIn: () => {
            dispatch({ type: "zoom-in" });
        },
        zoomOut: () => {
            dispatch({ type: "zoom-out" });
        },
        zoomPercent: state.zoomPercent,
    };
}

function taskDetailReducer(state: TaskDetailState, action: TaskDetailAction): TaskDetailState {
    switch (action.type) {
        case "load-start":
            return {
                ...state,
                actionError: null,
                error: null,
                isLoading: !action.isRefresh,
                isRefreshing: action.isRefresh,
                streamError: null,
            };
        case "bootstrap-success":
            return applyBootstrapSuccess(state, action.bootstrap);
        case "load-error":
            return {
                ...state,
                bootstrap: null,
                error: action.error,
                events: [],
                isLoading: false,
                isRefreshing: false,
                streamStatus: "closed",
                streamResetStaleCursor: null,
            };
        case "live-event":
            return {
                ...state,
                events: mergeTaskEvents(state.events, [action.event]),
                streamError: null,
                streamStatus: "live",
            };
        case "live-events":
            return {
                ...state,
                events: mergeTaskEvents(state.events, action.events),
                streamError: null,
            };
        case "stream-status":
            return {
                ...state,
                streamStatus: action.status,
            };
        case "stream-reset":
            return {
                ...state,
                streamError: null,
                streamResetStaleCursor: action.staleCursor,
                streamStatus: "reset",
            };
        case "stream-error":
            return {
                ...state,
                streamError: action.error,
                streamResetStaleCursor: null,
                streamStatus: "closed",
            };
        case "select-node":
            return applyNodeSelection(state, action.nodeKey);
        case "select-event":
            return applyEventSelection(state, action.eventId);
        case "open-detail":
            return {
                ...state,
                detailOpen: true,
            };
        case "close-detail":
            return {
                ...state,
                detailOpen: false,
            };
        case "tab":
            return {
                ...state,
                tab: action.tab,
            };
        case "refresh":
            return {
                ...state,
                refreshToken: state.refreshToken + 1,
            };
        case "action-start":
            return {
                ...state,
                actionError: null,
                actionPending: action.action,
            };
        case "action-success":
            return applyActionSuccess(state, action.task);
        case "action-error":
            return {
                ...state,
                actionError: action.error,
                actionPending: null,
            };
        case "zoom-in":
            return {
                ...state,
                zoomPercent: Math.min(MAX_ZOOM_PERCENT, state.zoomPercent + 15),
            };
        case "zoom-out":
            return {
                ...state,
                zoomPercent: Math.max(MIN_ZOOM_PERCENT, state.zoomPercent - 15),
            };
        case "reset-graph":
            return {
                ...state,
                zoomPercent: 100,
            };
    }
}

function applyBootstrapSuccess(
    state: TaskDetailState,
    bootstrap: TaskDetailBootstrap,
): TaskDetailState {
    const view = buildTaskDetailView({
        bootstrap,
        events: bootstrap.events,
    });
    const selectedNodeKey = state.selectedNodeKey ?? getDefaultNodeKey(view);
    const selectedEventId = state.selectedEventId ?? getDefaultEventId(view, selectedNodeKey);

    return {
        ...state,
        bootstrap,
        error: null,
        events: bootstrap.events,
        isLoading: false,
        isRefreshing: false,
        selectedEventId,
        selectedNodeKey,
        streamError: null,
    };
}

function applyActionSuccess(
    state: TaskDetailState,
    task: components["schemas"]["RuntimeFlowRead"],
): TaskDetailState {
    if (state.bootstrap === null) {
        return {
            ...state,
            actionPending: null,
        };
    }

    return {
        ...state,
        actionError: null,
        actionPending: null,
        bootstrap: {
            ...state.bootstrap,
            task,
        },
    };
}

function applyNodeSelection(state: TaskDetailState, nodeKey: string): TaskDetailState {
    if (state.bootstrap === null) {
        return {
            ...state,
            selectedNodeKey: nodeKey,
        };
    }

    const view = buildTaskDetailView({
        bootstrap: state.bootstrap,
        events: state.events,
    });

    return {
        ...state,
        selectedEventId: getDefaultEventId(view, nodeKey),
        selectedNodeKey: nodeKey,
    };
}

function applyEventSelection(state: TaskDetailState, eventId: string): TaskDetailState {
    const selectedEvent = state.events.find((event) => event.event_id === eventId);

    return {
        ...state,
        selectedEventId: eventId,
        selectedNodeKey: selectedEvent?.node_key ?? state.selectedNodeKey,
    };
}

function toErrorView(error: unknown): ConsoleErrorView {
    if (error instanceof AutoClawApiError) {
        return error.errorView;
    }

    return {
        code: "task_detail_error",
        fieldErrors: [],
        isRetryable: true,
        source: "http",
        status: null,
        suggestedNextStep: "Retry the Task Detail read.",
        summary: error instanceof Error ? error.message : "Task Detail could not load.",
        title: "Task Detail Error",
    };
}

function isAbortError(error: unknown): boolean {
    return error instanceof AutoClawApiError && error.errorView.source === "abort";
}
