import { ArrowRight, ChevronDown, FileText, RefreshCw, SquareX } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { PageFrame } from "../../components/layout";
import {
    Button,
    CodeBlock,
    IdRefText,
    PropertyGrid,
    StatePanel,
    StatusChip,
    Surface,
    TimestampText,
} from "../../components/ui";
import { classNames } from "../../lib/classNames";
import {
    isAuthError,
    isStaleActionError,
    useCommandRunsController,
    type CommandRunLogState,
    type CommandRunsController,
} from "./command-run-controller";
import {
    formatOptionalNumber,
    isTerminalCommandRunState,
    renderOptionalText,
    type CommandRunDetailView,
    type CommandRunRowView,
} from "./command-run-model";

export function CommandRunsPage() {
    const { taskId } = useParams();
    const controller = useCommandRunsController(taskId ?? null);

    return (
        <PageFrame
            actions={
                <div className="flex flex-wrap items-center gap-2">
                    <OpenTaskDetailLink taskId={controller.taskId} />
                    <Button
                        disabled={controller.isLoading || controller.isRefreshing}
                        icon={
                            <RefreshCw className={controller.isRefreshing ? "animate-spin" : ""} />
                        }
                        onClick={controller.refresh}
                    >
                        Refresh
                    </Button>
                </div>
            }
            description="Inspect task-scoped controller command runs, open details, read logs on demand, and cancel legal active runs."
            eyebrow={controller.taskId ?? "Runtime"}
            title="Command Runs"
        >
            <Surface
                actions={
                    <StatusChip tone={controller.error === null ? "neutral" : "danger"} withDot>
                        {controller.statusSummary}
                    </StatusChip>
                }
                label="Task command runs"
                title="Run records"
            >
                <CommandRunsState controller={controller} />
            </Surface>
        </PageFrame>
    );
}

function CommandRunsState({ controller }: { readonly controller: CommandRunsController }) {
    if (controller.isLoading) {
        return (
            <StatePanel
                summary="Reading controller-managed command runs for this task."
                title="Loading Command Runs"
                tone="loading"
            />
        );
    }

    if (controller.error !== null) {
        return (
            <StatePanel
                action={<Button onClick={controller.refresh}>Retry</Button>}
                summary={controller.error.summary}
                title={
                    isAuthError(controller.error)
                        ? "Access to Command Runs failed"
                        : "Command Runs could not load"
                }
                tone={isAuthError(controller.error) ? "auth" : "error"}
            />
        );
    }

    if (controller.rows.length === 0) {
        return (
            <StatePanel
                action={<OpenTaskDetailLink taskId={controller.taskId} />}
                summary="The controller did not return command-run records for this task."
                title="No command runs"
                tone="empty"
            />
        );
    }

    return (
        <div className="space-y-4">
            <ol aria-label="Command run rows" className="space-y-3">
                {controller.rows.map((row) => (
                    <li key={row.runId}>
                        <CommandRunRow controller={controller} row={row} />
                    </li>
                ))}
            </ol>
            <CommandRunsFooter controller={controller} />
        </div>
    );
}

function CommandRunRow({
    controller,
    row,
}: {
    readonly controller: CommandRunsController;
    readonly row: CommandRunRowView;
}) {
    const isExpanded = controller.expandedRunId === row.runId;
    const cancelError = controller.cancelErrorsByRunId[row.runId] ?? null;

    return (
        <article
            className={classNames(
                "min-w-0 rounded-card border bg-surface-low shadow-hairline transition-colors focus-within:border-primary/45",
                isExpanded ? "border-primary/50" : "border-outline-soft",
            )}
        >
            <div className="grid min-w-0 gap-3 p-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-start">
                <button
                    aria-expanded={isExpanded}
                    className="min-w-0 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                    onClick={() => {
                        controller.toggleExpandedRun(row.runId);
                    }}
                    type="button"
                >
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                        <ChevronDown
                            aria-hidden="true"
                            className={classNames(
                                "size-4 shrink-0 text-muted transition-transform",
                                isExpanded && "rotate-180",
                            )}
                        />
                        <StatusChip tone={row.stateTone} withDot>
                            {row.stateLabel}
                        </StatusChip>
                        <span className="font-mono text-label font-medium uppercase text-muted">
                            Run id
                        </span>
                        <IdRefText className="max-w-64 truncate" value={row.runId} />
                    </div>
                    <h2 className="mt-2 min-w-0 break-words font-display text-compact font-semibold text-foreground">
                        {row.description ?? row.command}
                    </h2>
                    <p className="mt-1 min-w-0 break-words font-mono text-utility text-muted">
                        {row.command}
                    </p>
                    {row.summary === null ? null : (
                        <p className="mt-2 max-w-4xl break-words text-compact text-muted">
                            {row.summary}
                        </p>
                    )}
                </button>
                <div className="flex min-w-0 flex-wrap items-center gap-2 lg:justify-end">
                    {row.canCancel ? (
                        <Button
                            disabled={controller.isCancellingRunId !== null}
                            icon={<SquareX />}
                            onClick={() => {
                                controller.cancelRun(row.runId);
                            }}
                            variant="danger"
                        >
                            {controller.isCancellingRunId === row.runId ? "Cancelling" : "Cancel"}
                        </Button>
                    ) : null}
                </div>
            </div>
            {cancelError === null ? null : <CommandRunActionError error={cancelError} />}
            {isExpanded ? <CommandRunExpandedDetail controller={controller} row={row} /> : null}
        </article>
    );
}

function CommandRunExpandedDetail({
    controller,
    row,
}: {
    readonly controller: CommandRunsController;
    readonly row: CommandRunRowView;
}) {
    const detail = controller.detailViewsByRunId[row.runId] ?? null;
    const detailError = controller.detailErrorsByRunId[row.runId] ?? null;
    const isLoading = controller.isDetailLoadingRunId === row.runId && detail === null;

    if (isLoading) {
        return (
            <div className="border-t border-outline-soft p-4">
                <StatePanel
                    summary="Reading the full controller command-run record."
                    title="Loading run detail"
                    tone="loading"
                />
            </div>
        );
    }

    if (detailError !== null && detail === null) {
        return (
            <div className="border-t border-outline-soft p-4">
                <StatePanel
                    action={
                        <Button onClick={() => controller.retryDetail(row.runId)}>Retry</Button>
                    }
                    summary={detailError.summary}
                    title="Run detail could not load"
                    tone="error"
                />
            </div>
        );
    }

    if (detail === null) {
        return null;
    }

    return (
        <div className="space-y-4 border-t border-outline-soft p-4">
            <CommandRunCommandSection detail={detail} />
            <div className="grid min-w-0 gap-4 lg:grid-cols-3">
                <CommandRunResultSection detail={detail} />
                <CommandRunTimingSection detail={detail} />
                <CommandRunProvenanceSection detail={detail} />
            </div>
            <CommandRunLogSection
                detail={detail}
                logState={controller.logStatesByRunId[detail.runId] ?? null}
                onToggleLogs={() => {
                    controller.toggleLogs(detail.runId);
                }}
            />
        </div>
    );
}

function CommandRunCommandSection({ detail }: { readonly detail: CommandRunDetailView }) {
    return (
        <section className="min-w-0 rounded-card border border-outline-soft bg-surface p-4">
            <div className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(12rem,18rem)]">
                <div className="min-w-0">
                    <p className="font-mono text-label font-medium uppercase text-muted">Command</p>
                    <p className="mt-2 break-words font-mono text-utility text-foreground">
                        {detail.command}
                    </p>
                    <p className="mt-3 break-words text-compact text-muted">{detail.description}</p>
                </div>
                <div className="min-w-0">
                    <p className="font-mono text-label font-medium uppercase text-muted">Workdir</p>
                    <IdRefText
                        className="mt-2 block rounded-control border border-outline-soft bg-surface-low px-3 py-2"
                        value={detail.workdir ?? "Not reported"}
                    />
                </div>
            </div>
        </section>
    );
}

function CommandRunResultSection({ detail }: { readonly detail: CommandRunDetailView }) {
    const terminalResult = detail.terminalResult;
    return (
        <Surface
            label="Result"
            title={isTerminalCommandRunState(detail.state) ? "Terminal result" : "Latest result"}
        >
            <PropertyGrid
                className="!grid-cols-1 sm:!grid-cols-1 lg:!grid-cols-1"
                items={[
                    { label: "State", value: detail.state },
                    {
                        label: "Summary",
                        value: renderOptionalText(terminalResult?.summary ?? detail.latestUpdate),
                    },
                    {
                        label: "Exit code",
                        value: formatOptionalNumber(terminalResult?.exit_code ?? null),
                    },
                    { label: "Signal", value: renderOptionalText(terminalResult?.signal ?? null) },
                ]}
            />
        </Surface>
    );
}

function CommandRunTimingSection({ detail }: { readonly detail: CommandRunDetailView }) {
    return (
        <Surface label="Timing" title="Controller timestamps">
            <PropertyGrid
                className="!grid-cols-1 sm:!grid-cols-1 lg:!grid-cols-1"
                items={[
                    { label: "Created", value: <TimestampText value={detail.createdAt} /> },
                    {
                        label: "Started",
                        value:
                            detail.startedAt === null ? (
                                "Not reported"
                            ) : (
                                <TimestampText value={detail.startedAt} />
                            ),
                    },
                    {
                        label: "Ended",
                        value:
                            detail.endedAt === null ? (
                                "Not reported"
                            ) : (
                                <TimestampText value={detail.endedAt} />
                            ),
                    },
                    {
                        label: "Timeout",
                        value:
                            detail.timeoutSeconds === null
                                ? "Not reported"
                                : `${String(detail.timeoutSeconds)} seconds`,
                    },
                ]}
            />
        </Surface>
    );
}

function CommandRunProvenanceSection({ detail }: { readonly detail: CommandRunDetailView }) {
    return (
        <Surface label="Provenance" title="Controller lineage">
            <PropertyGrid
                className="!grid-cols-1 sm:!grid-cols-1 lg:!grid-cols-1"
                items={[
                    { label: "Dispatch", value: <IdRefText value={detail.dispatchId} /> },
                    { label: "Attempt", value: renderOptionalId(detail.attemptId) },
                    { label: "Run id", value: <IdRefText value={detail.runId} /> },
                    {
                        label: "Cancel requested",
                        value:
                            detail.cancellationRequestedAt === null ? (
                                "Not reported"
                            ) : (
                                <TimestampText value={detail.cancellationRequestedAt} />
                            ),
                    },
                    {
                        label: "Cancel actor",
                        value: renderOptionalId(detail.cancellationRequestedByActorRef),
                    },
                    {
                        label: "Terminal source",
                        value: renderOptionalText(detail.terminalEventSource),
                    },
                    {
                        label: "Terminal actor",
                        value: renderOptionalId(detail.terminalActorRef),
                    },
                ]}
            />
        </Surface>
    );
}

function CommandRunLogSection({
    detail,
    logState,
    onToggleLogs,
}: {
    readonly detail: CommandRunDetailView;
    readonly logState: CommandRunLogState | null;
    readonly onToggleLogs: () => void;
}) {
    const logRef = detail.logRef;

    return (
        <section className="min-w-0 rounded-card border border-outline-soft bg-surface p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                    <p className="font-mono text-label font-medium uppercase text-muted">
                        Log access
                    </p>
                    {logRef === null ? (
                        <p className="mt-1 text-compact text-muted">
                            This run does not expose a log ref.
                        </p>
                    ) : (
                        <IdRefText className="mt-1 block" value={logRef} />
                    )}
                </div>
                {logRef === null ? null : (
                    <Button icon={<FileText />} onClick={onToggleLogs}>
                        {logState?.isVisible === true ? "Hide logs" : "View logs"}
                    </Button>
                )}
            </div>
            {logState?.error === undefined || logState.error === null ? null : (
                <div className="mt-4">
                    <StatePanel
                        summary={logState.error.summary}
                        title="Logs could not load"
                        tone={logState.error.status === 404 ? "stale" : "error"}
                    />
                </div>
            )}
            {logState?.isVisible === true && logState.isLoading ? (
                <div className="mt-4">
                    <StatePanel
                        summary="Reading persisted command-run logs."
                        title="Loading logs"
                        tone="loading"
                    />
                </div>
            ) : null}
            {logState?.isVisible === true && logState.content !== null ? (
                <div className="mt-4">
                    <CodeBlock title="Logs">{logState.content}</CodeBlock>
                </div>
            ) : null}
        </section>
    );
}

function CommandRunActionError({
    error,
}: {
    readonly error: {
        readonly code: string;
        readonly suggestedNextStep: string | null;
        readonly summary: string;
    };
}) {
    const isStale = isStaleActionError(error.code);
    return (
        <div className="border-t border-outline-soft px-4 pb-4">
            <StatePanel
                summary={
                    <span>
                        {error.summary}
                        {error.suggestedNextStep === null ? null : (
                            <span className="mt-1 block">{error.suggestedNextStep}</span>
                        )}
                    </span>
                }
                title={isStale ? "Cancel state changed" : "Cancel failed"}
                tone={isStale ? "stale" : "error"}
            />
        </div>
    );
}

function CommandRunsFooter({ controller }: { readonly controller: CommandRunsController }) {
    return (
        <footer className="flex flex-col gap-3 border-t border-outline-soft pt-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-compact text-muted">
                {controller.nextCursor === null
                    ? "End of current command-run results."
                    : "More command runs are available."}
            </p>
            <Button
                disabled={
                    controller.nextCursor === null ||
                    controller.isLoading ||
                    controller.isLoadingMore ||
                    controller.isRefreshing
                }
                onClick={controller.loadMore}
            >
                {controller.isLoadingMore ? "Loading" : "Load more"}
            </Button>
        </footer>
    );
}

function OpenTaskDetailLink({ taskId }: { readonly taskId: string | null }) {
    const to = taskId === null ? "/tasks" : `/tasks/${encodeURIComponent(taskId)}`;

    return (
        <Link
            className="inline-flex h-control items-center justify-center gap-2 rounded-control border border-outline bg-surface-low px-3 text-utility font-semibold text-foreground transition-colors hover:border-primary/45 hover:text-primary-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            to={to}
        >
            <span>Open task detail</span>
            <ArrowRight aria-hidden="true" className="size-4 shrink-0" />
        </Link>
    );
}

function renderOptionalId(value: string | null) {
    return value === null ? "Not reported" : <IdRefText value={value} />;
}
