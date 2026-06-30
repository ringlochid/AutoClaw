import { useEffect, useRef } from "react";

import { RefreshCw } from "lucide-react";
import { useParams } from "react-router-dom";

import { PageFrame } from "../../components/layout";
import { Button, StatePanel } from "../../components/ui";
import { useTaskDetailController, type TaskDetailController } from "./task-detail-controller";
import { TaskEventLane } from "./task-detail-event-lane";
import { TaskGraph } from "./task-detail-graph";
import { TaskDetailModal } from "./task-detail-modal";
import { SiblingHandoffs } from "./task-detail-sibling-handoffs";
import { TaskActionControls, TaskSummaryHeader } from "./task-detail-summary";

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
            description="Read current task state, event history, and task controls."
            eyebrow={taskId ?? "Runtime"}
            title="Task Detail"
        >
            {controller.isLoading ? (
                <StatePanel
                    summary="Reading task, snapshot, trace, event history, and sibling handoffs."
                    title="Loading Task Detail"
                    tone="loading"
                />
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
                    onRefresh={controller.refresh}
                    view={view}
                />
            }
            description={view.task.summary}
            eyebrow="Task Detail"
            title={view.task.title}
        >
            <div className="space-y-4">
                <TaskSummaryHeader controller={controller} view={view} />
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
                <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1fr)_24rem]">
                    <TaskGraph
                        edges={view.graphEdges}
                        nodes={view.graphNodes}
                        onOpenDetail={handleOpenDetail}
                        onReset={controller.resetGraph}
                        onSelectNode={controller.selectNode}
                        onZoomIn={controller.zoomIn}
                        onZoomOut={controller.zoomOut}
                        selectedNodeKey={controller.selectedNodeKey}
                        zoomPercent={controller.zoomPercent}
                    />
                    <div className="grid min-w-0 gap-4">
                        <TaskEventLane
                            events={view.eventRows}
                            onOpenDetail={handleOpenDetail}
                            onSelectEvent={controller.selectEvent}
                            selectedEventId={controller.selectedEventId}
                        />
                        <SiblingHandoffs taskId={view.task.taskId} view={view} />
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
