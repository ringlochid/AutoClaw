import { useEffect, useRef } from "react";

import { RefreshCw } from "lucide-react";
import { useParams } from "react-router-dom";

import { PageFrame } from "../../components/layout";
import { Button, StatePanel } from "../../components/ui";
import { useTaskDetailController, type TaskDetailController } from "./task-detail-controller";
import { TaskEventLane } from "./task-detail-event-lane";
import { TaskGraph } from "./task-detail-graph";
import { TaskDetailModal } from "./task-detail-modal";
import { TaskActionControls, TaskDetailEyebrow, TaskSummaryHeader } from "./task-detail-summary";

const TASK_DETAIL_SKELETON_EVENT_ROWS = [0, 1, 2, 3] as const;
const TASK_DETAIL_SKELETON_CHILD_NODES = [0, 1, 2] as const;

export function TaskDetailPage() {
    const { taskId } = useParams();
    const controller = useTaskDetailController(taskId ?? null);

    useTaskDetailModalEscape(controller);

    if (controller.view === null) {
        return <TaskDetailUnavailableState controller={controller} taskId={taskId ?? null} />;
    }

    return <TaskDetailLoadedState controller={controller} />;
}

function TaskDetailUnavailableState({
    controller,
    taskId,
}: {
    readonly controller: TaskDetailController;
    readonly taskId: string | null;
}) {
    return (
        <PageFrame
            actions={
                <Button icon={<RefreshCw />} onClick={controller.refresh}>
                    Retry
                </Button>
            }
            className="w-full"
            description="Read current task state, event history, and task controls."
            eyebrow={taskId ?? "Runtime"}
            title="Task Detail"
        >
            {controller.isLoading ? (
                <TaskDetailLoadingSkeleton />
            ) : (
                <StatePanel
                    action={<Button onClick={controller.refresh}>Retry</Button>}
                    summary={controller.error?.summary ?? "Task Detail could not load."}
                    title={
                        isAuthError(controller.error)
                            ? "Access to Task Detail failed"
                            : "Task Detail could not load"
                    }
                    tone={isAuthError(controller.error) ? "auth" : "error"}
                />
            )}
        </PageFrame>
    );
}

function TaskDetailLoadingSkeleton() {
    return (
        <div aria-busy="true" aria-label="Loading Task Detail" className="space-y-4" role="status">
            <div className="grid min-w-0 items-start gap-3 lg:grid-cols-[minmax(0,1fr)_348px] xl:grid-cols-[minmax(0,1fr)_392px]">
                <section className="overflow-hidden rounded-card border border-outline-soft bg-surface-low">
                    <header className="flex items-center justify-between gap-3 border-b border-outline-soft px-5 py-4">
                        <div>
                            <div className="h-4 w-36 animate-pulse rounded-full bg-surface-muted" />
                            <div className="mt-2 h-3 w-52 animate-pulse rounded-full bg-surface-muted" />
                        </div>
                        <div className="h-control w-32 animate-pulse rounded-control bg-primary-soft" />
                    </header>
                    <div className="h-[520px] overflow-hidden bg-gradient-to-br from-surface via-surface to-primary-soft/35 p-8">
                        <div className="mx-auto mt-24 h-9 w-28 animate-pulse rounded-control border border-primary/25 bg-surface-low shadow-panel" />
                        <div className="mx-auto mt-8 h-px w-[72%] bg-outline-soft" />
                        <div className="mt-10 grid grid-cols-3 gap-8">
                            {TASK_DETAIL_SKELETON_CHILD_NODES.map((nodeIndex) => (
                                <div
                                    className="h-11 animate-pulse rounded-control border border-outline-soft bg-surface-low"
                                    key={nodeIndex}
                                />
                            ))}
                        </div>
                    </div>
                </section>
                <aside className="overflow-hidden rounded-card border border-outline-soft bg-surface-low">
                    <header className="border-b border-outline-soft px-5 py-4">
                        <div className="h-4 w-16 animate-pulse rounded-full bg-surface-muted" />
                    </header>
                    <div className="grid gap-3 p-3">
                        {TASK_DETAIL_SKELETON_EVENT_ROWS.map((rowIndex) => (
                            <div
                                className="h-24 animate-pulse rounded-card border border-outline-soft bg-surface"
                                key={rowIndex}
                            />
                        ))}
                    </div>
                </aside>
            </div>
        </div>
    );
}

function TaskDetailLoadedState({ controller }: { readonly controller: TaskDetailController }) {
    const { view } = controller;
    const detailReturnFocusRef = useRef<HTMLElement | null>(null);

    useEffect(() => {
        if (controller.detailOpen) {
            return;
        }

        const returnFocusTarget = detailReturnFocusRef.current;
        detailReturnFocusRef.current = null;
        if (returnFocusTarget?.isConnected === true) {
            returnFocusTarget.focus({ preventScroll: true });
        }
    }, [controller.detailOpen]);

    if (view === null) {
        return null;
    }

    const handleOpenDetail = () => {
        const activeElement = document.activeElement;
        detailReturnFocusRef.current =
            activeElement instanceof HTMLElement && activeElement !== document.body
                ? activeElement
                : null;
        controller.openDetail();
    };

    const handleCloseDetail = () => {
        controller.closeDetail();
    };

    return (
        <PageFrame
            actions={
                <TaskActionControls
                    actionError={controller.actionError}
                    actionPending={controller.actionPending}
                    onAction={controller.taskAction}
                    view={view}
                />
            }
            description={view.task.summary}
            eyebrow={<TaskDetailEyebrow view={view} />}
            headerClassName="!px-5 !py-3.5 sm:!px-6 lg:!px-7"
            headerContent={<TaskSummaryHeader view={view} />}
            headerContentPlacement="title-inline"
            title={view.task.title}
        >
            <div className="space-y-4">
                {controller.actionError === null ? null : (
                    <StatePanel
                        summary={controller.actionError.summary}
                        title={
                            isStaleActionError(controller.actionError.code)
                                ? "Stale action"
                                : "Action failed"
                        }
                        tone={isStaleActionError(controller.actionError.code) ? "stale" : "error"}
                    />
                )}
                {controller.streamError === null ? null : (
                    <StatePanel
                        summary={controller.streamError.summary}
                        title="Live event stream stopped"
                        tone="error"
                    />
                )}
                {controller.streamStatus === "reset" ||
                controller.streamResetStaleCursor !== null ? (
                    <StatePanel
                        summary={streamResetSummary(controller.streamResetStaleCursor)}
                        title="Stream cursor reset"
                        tone="stale"
                    />
                ) : null}
                <div className="grid min-w-0 items-start gap-3 lg:grid-cols-[minmax(0,1fr)_348px] xl:grid-cols-[minmax(0,1fr)_392px]">
                    <TaskGraph
                        edges={view.graphEdges}
                        nodes={view.graphNodes}
                        onOpenDetail={handleOpenDetail}
                        onSelectNode={controller.selectNode}
                        selectedNodeKey={controller.selectedNodeKey}
                    />
                    <div className="grid min-w-0 gap-4">
                        <TaskEventLane
                            events={view.eventRows}
                            onOpenDetail={handleOpenDetail}
                            onSelectEvent={controller.selectEvent}
                            selectedEventId={controller.selectedEventId}
                        />
                    </div>
                </div>
            </div>
            {controller.detailOpen && controller.selectedContext !== null ? (
                <TaskDetailModal
                    context={controller.selectedContext}
                    onClose={handleCloseDetail}
                    onTabChange={controller.setDetailTab}
                    tab={controller.tab}
                    taskId={view.task.taskId}
                    view={view}
                />
            ) : null}
        </PageFrame>
    );
}

function useTaskDetailModalEscape(controller: TaskDetailController) {
    useEffect(() => {
        if (!controller.detailOpen) {
            return;
        }

        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") {
                controller.closeDetail();
            }
        };

        document.body.classList.add("overflow-hidden");
        document.addEventListener("keydown", handleKeyDown);
        return () => {
            document.body.classList.remove("overflow-hidden");
            document.removeEventListener("keydown", handleKeyDown);
        };
    }, [controller]);
}

function isAuthError(
    error: { readonly code: string; readonly status: number | null } | null,
): boolean {
    return (
        error?.status === 401 ||
        error?.status === 403 ||
        error?.code === "illegal_caller" ||
        error?.code === "capability_rejected" ||
        error?.code === "auth_required" ||
        error?.code === "permission_denied"
    );
}

function isStaleActionError(code: string): boolean {
    return code.startsWith("stale_") || code === "illegal_state";
}

function streamResetSummary(staleCursor: string | null): string {
    const cursorText = staleCursor === null ? "the stale cursor" : `stale cursor ${staleCursor}`;
    return `The event stream rejected ${cursorText}; current task truth was reread and the live stream reconnected without that cursor.`;
}
