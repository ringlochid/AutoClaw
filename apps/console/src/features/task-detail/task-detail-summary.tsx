import type { ReactNode } from "react";

import { Ban, Pause, Play, RefreshCw } from "lucide-react";

import { Button, IconButton, IdRefText, StatusChip, TimestampText } from "../../components/ui";
import type { TaskControlAction } from "./task-detail-data";
import type { TaskDetailController } from "./task-detail-controller";
import { flowStatusTone, type TaskDetailView } from "./task-detail-model";

export function TaskSummaryHeader({
    controller,
    view,
}: {
    readonly controller: TaskDetailController;
    readonly view: TaskDetailView;
}) {
    return (
        <div className="flex min-w-0 flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
                <HeaderFact label="Status">
                    <StatusChip tone={flowStatusTone(view.task.status)} withDot>
                        {view.task.status}
                    </StatusChip>
                </HeaderFact>
                <HeaderFact label="Node">
                    {view.task.currentNodeKey === null ? (
                        "not exposed"
                    ) : (
                        <IdRefText value={view.task.currentNodeKey} />
                    )}
                </HeaderFact>
                <HeaderFact label="Updated">
                    <TimestampText value={view.task.updatedAt} />
                </HeaderFact>
                <HeaderFact label="Stream head">
                    {view.snapshot.streamHeadEventId ?? "live-only"}
                </HeaderFact>
            </div>
            <div className="flex shrink-0 items-center">
                <StatusChip tone={streamStatusTone(controller.streamStatus)} withDot>
                    {streamStatusLabel(controller.streamStatus)}
                </StatusChip>
            </div>
        </div>
    );
}

export function TaskActionControls({
    actionError,
    actionPending,
    onAction,
    onRefresh,
    view,
}: {
    readonly actionError: { readonly code: string } | null;
    readonly actionPending: TaskControlAction | null;
    readonly onAction: (action: TaskControlAction) => void;
    readonly onRefresh: () => void;
    readonly view: TaskDetailView;
}) {
    return (
        <div className="flex flex-wrap items-center gap-2">
            <Button
                disabled={!view.actionMode.canPause || actionPending !== null}
                icon={<Pause />}
                onClick={() => {
                    onAction("pause");
                }}
            >
                {actionPending === "pause" ? "Pausing" : "Pause"}
            </Button>
            <Button
                disabled={!view.actionMode.canContinue || actionPending !== null}
                icon={<Play />}
                onClick={() => {
                    onAction("continue");
                }}
            >
                {actionPending === "continue" ? "Continuing" : "Continue"}
            </Button>
            <Button
                disabled={!view.actionMode.canCancel || actionPending !== null}
                icon={<Ban />}
                onClick={() => {
                    onAction("cancel");
                }}
                variant="danger"
            >
                {actionPending === "cancel" ? "Cancelling" : "Cancel"}
            </Button>
            <IconButton
                icon={<RefreshCw />}
                label={actionError === null ? "Refresh Task Detail" : "Refresh after action error"}
                onClick={onRefresh}
            />
        </div>
    );
}

function HeaderFact({ children, label }: { readonly children: ReactNode; readonly label: string }) {
    return (
        <div className="inline-flex min-h-8 max-w-full items-center gap-2 rounded-control border border-outline-soft bg-surface-low px-3 py-1.5">
            <span className="shrink-0 font-mono text-label font-medium uppercase text-muted">
                {label}
            </span>
            <span className="min-w-0 text-utility text-foreground">{children}</span>
        </div>
    );
}

function streamStatusTone(status: TaskDetailController["streamStatus"]) {
    switch (status) {
        case "live":
            return "active";
        case "reset":
        case "reconnecting":
            return "warning";
        case "closed":
        case "connecting":
            return "neutral";
    }
}

function streamStatusLabel(status: TaskDetailController["streamStatus"]) {
    switch (status) {
        case "closed":
            return "Stream closed";
        case "connecting":
            return "Connecting stream";
        case "live":
            return "Live events";
        case "reconnecting":
            return "Reconnecting";
        case "reset":
            return "Stream reset";
    }
}
