import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";

import { ArrowRight, RefreshCw, Search } from "lucide-react";
import { Link } from "react-router-dom";

import { PageFrame } from "../../components/layout";
import {
    Button,
    FormField,
    IdRefText,
    StatePanel,
    StatusChip,
    Surface,
    TimestampText,
    type StatusTone,
} from "../../components/ui";
import {
    AutoClawApiError,
    getNextCursor,
    requestJson,
    type ConsoleErrorView,
} from "../../api/client";
import type { components } from "../../api/generated/openapi";
import { runtimeTasksRoute, type RuntimeTasksQuery } from "../../api/routes";
import { mapTaskRow, type TaskRow } from "../../api/view-models";
import { classNames } from "../../lib/classNames";

type TaskStatusFilter = NonNullable<RuntimeTasksQuery["status"]>;
type TaskSort = NonNullable<RuntimeTasksQuery["sort"]>;

interface TaskPageState {
    readonly criteriaKey: string;
    readonly error: ConsoleErrorView | null;
    readonly hasLoaded: boolean;
    readonly isLoading: boolean;
    readonly isLoadingMore: boolean;
    readonly isRefreshing: boolean;
    readonly listGeneration: number;
    readonly nextCursor: string | null;
    readonly rows: readonly TaskRow[];
}

interface TaskPageController {
    readonly clearNarrowing: () => void;
    readonly hasActiveNarrowing: boolean;
    readonly loadMore: () => void;
    readonly pageState: TaskPageState;
    readonly query: string;
    readonly refresh: () => void;
    readonly setQuery: (value: string) => void;
    readonly setSort: (value: TaskSort) => void;
    readonly setStatus: (value: TaskStatusFilter) => void;
    readonly sort: TaskSort;
    readonly status: TaskStatusFilter;
    readonly statusSummary: string;
}

type TaskPageStateSetter = Dispatch<SetStateAction<TaskPageState>>;

const TASK_PAGE_SIZE = 25;
const INITIAL_TASK_CRITERIA_KEY = buildTaskListCriteriaKey({
    sort: "updated_at_desc",
    status: "any",
    trimmedQuery: "",
});

const STATUS_FILTERS: readonly { readonly label: string; readonly value: TaskStatusFilter }[] = [
    { label: "All statuses", value: "any" },
    { label: "Pending", value: "pending" },
    { label: "Running", value: "running" },
    { label: "Blocked", value: "blocked" },
    { label: "Paused", value: "paused" },
    { label: "Succeeded", value: "succeeded" },
    { label: "Cancelled", value: "cancelled" },
];

const SORT_OPTIONS: readonly { readonly label: string; readonly value: TaskSort }[] = [
    { label: "Updated newest", value: "updated_at_desc" },
    { label: "Updated oldest", value: "updated_at_asc" },
    { label: "Title A-Z", value: "task_title_asc" },
    { label: "Title Z-A", value: "task_title_desc" },
];

const initialState: TaskPageState = {
    criteriaKey: INITIAL_TASK_CRITERIA_KEY,
    error: null,
    hasLoaded: false,
    isLoading: true,
    isLoadingMore: false,
    isRefreshing: false,
    listGeneration: 0,
    nextCursor: null,
    rows: [],
};

export function TasksPage() {
    const controller = useTaskPageController();

    return (
        <PageFrame
            actions={
                <Button
                    disabled={controller.pageState.isLoading || controller.pageState.isRefreshing}
                    icon={
                        <RefreshCw
                            className={controller.pageState.isRefreshing ? "animate-spin" : ""}
                        />
                    }
                    onClick={controller.refresh}
                >
                    Refresh
                </Button>
            }
            description="Scan current runtime tasks, narrow the list, and open one task."
            eyebrow="Runtime"
            title="Tasks"
        >
            <Surface
                actions={
                    <StatusChip
                        tone={controller.pageState.error === null ? "neutral" : "danger"}
                        withDot
                    >
                        {controller.statusSummary}
                    </StatusChip>
                }
                label="Runtime list"
                title="Task rows"
            >
                <div className="space-y-4">
                    <TaskControls controller={controller} />
                    <TaskListState
                        error={controller.pageState.error}
                        hasActiveNarrowing={controller.hasActiveNarrowing}
                        isLoading={controller.pageState.isLoading}
                        onClearNarrowing={controller.clearNarrowing}
                        onRetry={controller.refresh}
                        rows={controller.pageState.rows}
                    />
                    <TaskListFooter controller={controller} />
                </div>
            </Surface>
        </PageFrame>
    );
}

function useTaskPageController(): TaskPageController {
    const [query, setQuery] = useState("");
    const [status, setStatus] = useState<TaskStatusFilter>("any");
    const [sort, setSort] = useState<TaskSort>("updated_at_desc");
    const [refreshToken, setRefreshToken] = useState(0);
    const [pageState, setPageState] = useState<TaskPageState>(initialState);
    const listGenerationRef = useRef(0);
    const trimmedQuery = query.trim();
    const criteriaKey = buildTaskListCriteriaKey({ sort, status, trimmedQuery });
    const hasActiveNarrowing = trimmedQuery.length > 0 || status !== "any";

    useTaskListReadEffect({
        criteriaKey,
        listGenerationRef,
        refreshToken,
        setPageState,
        sort,
        status,
        trimmedQuery,
    });

    return {
        clearNarrowing: () => {
            setQuery("");
            setStatus("any");
        },
        hasActiveNarrowing,
        loadMore: () => {
            void loadMoreTaskPage({
                criteriaKey,
                pageState,
                setPageState,
                sort,
                status,
                trimmedQuery,
            });
        },
        pageState,
        query,
        refresh: () => {
            setRefreshToken((value) => value + 1);
        },
        setQuery,
        setSort,
        setStatus,
        sort,
        status,
        statusSummary: getStatusSummary(pageState, hasActiveNarrowing),
    };
}

function useTaskListReadEffect({
    criteriaKey,
    listGenerationRef,
    refreshToken,
    setPageState,
    sort,
    status,
    trimmedQuery,
}: {
    readonly criteriaKey: string;
    readonly listGenerationRef: { current: number };
    readonly refreshToken: number;
    readonly setPageState: TaskPageStateSetter;
    readonly sort: TaskSort;
    readonly status: TaskStatusFilter;
    readonly trimmedQuery: string;
}) {
    useEffect(() => {
        const abortController = new AbortController();
        const listGeneration = listGenerationRef.current + 1;
        listGenerationRef.current = listGeneration;
        beginTaskListRead(setPageState, criteriaKey, listGeneration);
        void readTaskPage({
            cursor: null,
            signal: abortController.signal,
            sort,
            status,
            trimmedQuery,
        })
            .then((page) => {
                applyTaskListPage(setPageState, page, criteriaKey, listGeneration);
            })
            .catch((error: unknown) => {
                applyTaskListError(setPageState, error, criteriaKey, listGeneration);
            });

        return () => {
            abortController.abort();
        };
    }, [criteriaKey, listGenerationRef, refreshToken, setPageState, sort, status, trimmedQuery]);
}

function TaskControls({ controller }: { readonly controller: TaskPageController }) {
    return (
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_13rem_14rem]">
            <div>
                <label
                    className="block font-mono text-label font-medium uppercase text-muted"
                    htmlFor="tasks-query"
                >
                    Search
                </label>
                <div className="relative mt-2">
                    <Search
                        aria-hidden="true"
                        className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
                    />
                    <input
                        className={controlClassName("pl-10")}
                        id="tasks-query"
                        onChange={(event) => {
                            controller.setQuery(event.target.value);
                        }}
                        placeholder="Search tasks"
                        type="search"
                        value={controller.query}
                    />
                </div>
            </div>
            <TaskSelect
                id="tasks-status"
                label="Status"
                onChange={(value) => {
                    controller.setStatus(value as TaskStatusFilter);
                }}
                options={STATUS_FILTERS}
                value={controller.status}
            />
            <TaskSelect
                id="tasks-sort"
                label="Sort"
                onChange={(value) => {
                    controller.setSort(value as TaskSort);
                }}
                options={SORT_OPTIONS}
                value={controller.sort}
            />
        </div>
    );
}

function TaskSelect({
    id,
    label,
    onChange,
    options,
    value,
}: {
    readonly id: string;
    readonly label: string;
    readonly onChange: (value: string) => void;
    readonly options: readonly { readonly label: string; readonly value: string }[];
    readonly value: string;
}) {
    return (
        <FormField id={id} label={label}>
            <select
                className={controlClassName()}
                onChange={(event) => {
                    onChange(event.target.value);
                }}
                value={value}
            >
                {options.map((option) => (
                    <option key={option.value} value={option.value}>
                        {option.label}
                    </option>
                ))}
            </select>
        </FormField>
    );
}

function TaskListFooter({ controller }: { readonly controller: TaskPageController }) {
    const { pageState } = controller;
    if (pageState.rows.length === 0) {
        return null;
    }

    return (
        <footer className="flex flex-col gap-3 border-t border-outline-soft pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-compact text-muted">
                {pageState.nextCursor === null
                    ? "End of current task results."
                    : "More tasks are available."}
            </p>
            <Button
                disabled={
                    pageState.nextCursor === null ||
                    pageState.isLoading ||
                    pageState.isLoadingMore ||
                    pageState.isRefreshing
                }
                onClick={controller.loadMore}
            >
                {pageState.isLoadingMore ? "Loading" : "Load more"}
            </Button>
        </footer>
    );
}

function TaskListState({
    error,
    hasActiveNarrowing,
    isLoading,
    onClearNarrowing,
    onRetry,
    rows,
}: {
    readonly error: ConsoleErrorView | null;
    readonly hasActiveNarrowing: boolean;
    readonly isLoading: boolean;
    readonly onClearNarrowing: () => void;
    readonly onRetry: () => void;
    readonly rows: readonly TaskRow[];
}) {
    if (isLoading) {
        return (
            <StatePanel summary="Reading current task rows." title="Loading tasks" tone="loading" />
        );
    }

    if (error !== null) {
        return (
            <StatePanel
                action={<Button onClick={onRetry}>Retry</Button>}
                summary={error.summary}
                title={isAuthError(error) ? "Access to tasks failed" : "Tasks could not load"}
                tone={isAuthError(error) ? "auth" : "error"}
            />
        );
    }

    if (rows.length === 0) {
        if (hasActiveNarrowing) {
            return (
                <StatePanel
                    action={<Button onClick={onClearNarrowing}>Clear filters</Button>}
                    summary="No task rows match the current search or status filter."
                    title="No matching tasks"
                    tone="empty"
                />
            );
        }

        return (
            <StatePanel
                summary="The runtime task list is empty."
                title="No tasks available"
                tone="empty"
            />
        );
    }

    return (
        <div>
            <div className="hidden border-y border-outline-soft bg-surface-muted px-3 py-2 font-mono text-label font-medium uppercase text-muted lg:grid lg:grid-cols-[minmax(0,1fr)_9rem_12rem_7rem] lg:items-center lg:gap-4">
                <span>Tasks</span>
                <span>Status</span>
                <span>Updated</span>
                <span className="sr-only">Open</span>
            </div>
            <ol aria-label="Task rows" className="space-y-2 pt-3">
                {rows.map((row) => (
                    <TaskRowItem key={row.taskId} row={row} />
                ))}
            </ol>
        </div>
    );
}

function TaskRowItem({ row }: { readonly row: TaskRow }) {
    return (
        <li>
            <article className="grid min-w-0 gap-3 rounded-card border border-outline-soft bg-surface-low p-4 shadow-hairline transition-colors hover:border-primary/35 focus-within:border-primary/45 focus-within:bg-primary-soft/40 lg:grid-cols-[minmax(0,1fr)_9rem_12rem_7rem] lg:items-center lg:gap-4">
                <div className="min-w-0">
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                        <h2 className="min-w-0 truncate font-display text-compact font-semibold text-foreground">
                            {row.title}
                        </h2>
                        <span className="lg:hidden">
                            <TaskStatusChip status={row.status} />
                        </span>
                    </div>
                    <p className="mt-1 max-w-4xl break-words text-compact text-muted">
                        {row.summary}
                    </p>
                    <TaskRowMetadata row={row} />
                </div>
                <div className="hidden lg:block">
                    <TaskStatusChip status={row.status} />
                </div>
                <div className="min-w-0">
                    <p className="font-mono text-label font-medium uppercase text-muted lg:sr-only">
                        Updated
                    </p>
                    <TimestampText className="text-foreground" value={row.updatedAt} />
                </div>
                <div className="flex lg:justify-end">
                    <Link
                        aria-label={`Open ${row.title}`}
                        className="inline-flex h-control items-center justify-center gap-2 rounded-control border border-outline bg-surface-low px-3 text-utility font-semibold text-foreground transition-colors hover:border-primary/45 hover:text-primary-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                        to={taskDetailPath(row.taskId)}
                    >
                        <span>Open</span>
                        <ArrowRight aria-hidden="true" className="size-4 shrink-0" />
                    </Link>
                </div>
            </article>
        </li>
    );
}

function TaskRowMetadata({ row }: { readonly row: TaskRow }) {
    const items = [
        row.workflowKey === null ? null : { label: "Workflow", value: row.workflowKey },
        row.currentNodeKey === null ? null : { label: "Node", value: row.currentNodeKey },
    ].filter((item): item is { readonly label: string; readonly value: string } => item !== null);

    return (
        <dl className="mt-2 hidden min-w-0 flex-wrap gap-x-3 gap-y-1 md:flex">
            {items.map((item) => (
                <div className="flex min-w-0 items-baseline gap-1" key={item.label}>
                    <dt className="font-mono text-label font-medium uppercase text-muted">
                        {item.label}
                    </dt>
                    <dd className="min-w-0">
                        <IdRefText className="block max-w-80 truncate" value={item.value} />
                    </dd>
                </div>
            ))}
        </dl>
    );
}

function TaskStatusChip({ status }: { readonly status: components["schemas"]["FlowStatus"] }) {
    return (
        <StatusChip tone={statusTone(status)} withDot>
            {statusLabel(status)}
        </StatusChip>
    );
}

function statusTone(status: components["schemas"]["FlowStatus"]): StatusTone {
    switch (status) {
        case "running":
            return "active";
        case "succeeded":
            return "success";
        case "blocked":
        case "cancelled":
            return "danger";
        case "paused":
        case "pending":
            return "warning";
    }
}

function statusLabel(status: components["schemas"]["FlowStatus"]): string {
    return status.replace(/_/g, " ");
}

function getStatusSummary(pageState: TaskPageState, hasActiveNarrowing: boolean): string {
    if (pageState.isLoading) {
        return "Loading";
    }
    if (pageState.isRefreshing) {
        return "Refreshing";
    }
    if (pageState.error !== null) {
        return isAuthError(pageState.error) ? "Access problem" : "Read error";
    }
    if (pageState.rows.length === 0) {
        return hasActiveNarrowing ? "No results" : "Empty";
    }
    return "Ready";
}

function beginTaskListRead(
    setPageState: TaskPageStateSetter,
    criteriaKey: string,
    listGeneration: number,
): void {
    setPageState((currentState) => ({
        ...currentState,
        criteriaKey,
        error: null,
        isLoading: !currentState.hasLoaded,
        isLoadingMore: false,
        isRefreshing: currentState.hasLoaded,
        listGeneration,
        nextCursor: null,
    }));
}

function applyTaskListPage(
    setPageState: TaskPageStateSetter,
    page: components["schemas"]["RuntimeFlowSummaryListResponse"],
    criteriaKey: string,
    listGeneration: number,
): void {
    setPageState((currentState) => {
        if (!isCurrentTaskListRead(currentState, criteriaKey, listGeneration)) {
            return currentState;
        }

        return {
            ...currentState,
            error: null,
            hasLoaded: true,
            isLoading: false,
            isLoadingMore: false,
            isRefreshing: false,
            nextCursor: getNextCursor(page),
            rows: page.items.map(mapTaskRow),
        };
    });
}

function applyTaskListError(
    setPageState: TaskPageStateSetter,
    error: unknown,
    criteriaKey: string,
    listGeneration: number,
): void {
    if (isAbortError(error)) {
        return;
    }

    setPageState((currentState) => {
        if (!isCurrentTaskListRead(currentState, criteriaKey, listGeneration)) {
            return currentState;
        }

        return {
            ...currentState,
            error: toErrorView(error),
            hasLoaded: true,
            isLoading: false,
            isLoadingMore: false,
            isRefreshing: false,
            rows: currentState.hasLoaded ? currentState.rows : [],
        };
    });
}

async function loadMoreTaskPage({
    criteriaKey,
    pageState,
    setPageState,
    sort,
    status,
    trimmedQuery,
}: {
    readonly criteriaKey: string;
    readonly pageState: TaskPageState;
    readonly setPageState: TaskPageStateSetter;
    readonly sort: TaskSort;
    readonly status: TaskStatusFilter;
    readonly trimmedQuery: string;
}): Promise<void> {
    if (
        pageState.nextCursor === null ||
        pageState.isLoading ||
        pageState.isLoadingMore ||
        pageState.isRefreshing ||
        pageState.criteriaKey !== criteriaKey
    ) {
        return;
    }

    const cursor = pageState.nextCursor;
    const listGeneration = pageState.listGeneration;
    setPageState((currentState) =>
        isCurrentTaskListRead(currentState, criteriaKey, listGeneration)
            ? { ...currentState, error: null, isLoadingMore: true }
            : currentState,
    );

    try {
        const page = await readTaskPage({ cursor, signal: undefined, sort, status, trimmedQuery });
        setPageState((currentState) => {
            if (
                !isCurrentTaskListRead(currentState, criteriaKey, listGeneration) ||
                currentState.isLoading ||
                currentState.isRefreshing
            ) {
                return currentState;
            }

            return {
                ...currentState,
                error: null,
                isLoadingMore: false,
                nextCursor: getNextCursor(page),
                rows: [...currentState.rows, ...page.items.map(mapTaskRow)],
            };
        });
    } catch (error) {
        setPageState((currentState) => {
            if (!isCurrentTaskListRead(currentState, criteriaKey, listGeneration)) {
                return currentState;
            }

            return {
                ...currentState,
                error: toErrorView(error),
                isLoadingMore: false,
            };
        });
    }
}

function isCurrentTaskListRead(
    pageState: TaskPageState,
    criteriaKey: string,
    listGeneration: number,
): boolean {
    return pageState.criteriaKey === criteriaKey && pageState.listGeneration === listGeneration;
}

function buildTaskListCriteriaKey({
    sort,
    status,
    trimmedQuery,
}: {
    readonly sort: TaskSort;
    readonly status: TaskStatusFilter;
    readonly trimmedQuery: string;
}): string {
    return JSON.stringify([trimmedQuery, status, sort]);
}

async function readTaskPage({
    cursor,
    signal,
    sort,
    status,
    trimmedQuery,
}: {
    readonly cursor: string | null;
    readonly signal: AbortSignal | undefined;
    readonly sort: TaskSort;
    readonly status: TaskStatusFilter;
    readonly trimmedQuery: string;
}): Promise<components["schemas"]["RuntimeFlowSummaryListResponse"]> {
    const route = runtimeTasksRoute({
        cursor,
        limit: TASK_PAGE_SIZE,
        q: trimmedQuery.length === 0 ? null : trimmedQuery,
        sort,
        status,
    });

    return requestJson<components["schemas"]["RuntimeFlowSummaryListResponse"]>({
        path: route.path,
        query: route.query,
        signal,
    });
}

function controlClassName(className?: string): string {
    return classNames(
        "h-control w-full min-w-0 rounded-control border border-outline bg-surface-low px-3 text-compact text-foreground shadow-hairline transition-colors placeholder:text-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/15",
        className,
    );
}

function taskDetailPath(taskId: string): string {
    return `/tasks/${encodeURIComponent(taskId)}`;
}

function isAbortError(error: unknown): boolean {
    return error instanceof AutoClawApiError && error.errorView.source === "abort";
}

function toErrorView(error: unknown): ConsoleErrorView {
    if (error instanceof AutoClawApiError) {
        return error.errorView;
    }

    return {
        code: "unknown_error",
        fieldErrors: [],
        isRetryable: true,
        source: "http",
        status: null,
        suggestedNextStep: "Retry the task list read.",
        summary: error instanceof Error ? error.message : "The task list could not be read.",
        title: "Unknown Error",
    };
}

function isAuthError(error: ConsoleErrorView): boolean {
    return (
        error.status === 401 ||
        error.status === 403 ||
        error.code === "illegal_caller" ||
        error.code === "capability_rejected" ||
        error.code === "auth_required" ||
        error.code === "permission_denied"
    );
}
