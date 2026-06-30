import { ExternalLink, RefreshCw, Send } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { PageFrame } from "../../components/layout";
import {
    Button,
    IdRefText,
    PropertyGrid,
    StatePanel,
    StatusChip,
    Surface,
    TimestampText,
    type StatusTone,
} from "../../components/ui";
import type { components } from "../../api/generated/openapi";
import { classNames } from "../../lib/classNames";
import {
    isAuthError,
    useHumanRequestsController,
    type HumanRequestsController,
} from "./human-request-controller";
import { isRequestEditable, labelFromKind, mapHumanRequestQueueItem } from "./human-request-model";
import { TerminalReadback } from "./human-request-terminal-readback";
import { FocusedRequestWorkbench } from "./human-request-workbench";

type HumanRequestRead = components["schemas"]["HumanRequestRead"];
type HumanRequestStatus = components["schemas"]["HumanRequestStatus"];

export function HumanRequestsPage() {
    const { taskId } = useParams();
    const controller = useHumanRequestsController(taskId ?? null);

    return (
        <PageFrame
            actions={
                <Button
                    disabled={controller.isLoading || controller.isRefreshing}
                    icon={<RefreshCw className={controller.isRefreshing ? "animate-spin" : ""} />}
                    onClick={controller.refresh}
                >
                    Refresh
                </Button>
            }
            description="Resolve typed pending human requests for this selected task."
            eyebrow={controller.taskId ?? "Runtime"}
            title="Human Requests"
        >
            <HumanRequestsState controller={controller} />
        </PageFrame>
    );
}

function HumanRequestsState({ controller }: { readonly controller: HumanRequestsController }) {
    if (controller.isLoading) {
        return (
            <StatePanel
                summary="Reading task-scoped pending and terminal human requests."
                title="Loading Human Requests"
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
                        ? "Access to Human Requests failed"
                        : "Human Requests could not load"
                }
                tone={isAuthError(controller.error) ? "auth" : "error"}
            />
        );
    }

    if (controller.requestReads.length === 0) {
        return (
            <StatePanel
                action={<OpenTaskDetailLink taskId={controller.taskId} />}
                summary="The controller did not return any human request records for this task."
                title="No human requests"
                tone="empty"
            />
        );
    }

    return (
        <div className="grid min-w-0 gap-4 xl:grid-cols-[18rem_minmax(0,1fr)]">
            <HumanRequestQueue controller={controller} />
            <SelectedHumanRequest controller={controller} />
        </div>
    );
}

function HumanRequestQueue({ controller }: { readonly controller: HumanRequestsController }) {
    const openCount = controller.requestReads.filter(
        (read) => read.request.status === "open",
    ).length;
    const terminalCount = controller.requestReads.length - openCount;

    return (
        <Surface
            actions={
                <StatusChip tone="neutral">
                    {String(openCount)} open
                    {terminalCount > 0 ? ` / ${String(terminalCount)} terminal` : ""}
                </StatusChip>
            }
            className="min-w-0"
            label="Requests"
            title="Task queue"
        >
            <ol aria-label="Human request queue" className="space-y-2">
                {controller.requestReads.map((read) => (
                    <li key={read.request.request_id}>
                        <HumanRequestQueueButton controller={controller} read={read} />
                    </li>
                ))}
            </ol>
        </Surface>
    );
}

function HumanRequestQueueButton({
    controller,
    read,
}: {
    readonly controller: HumanRequestsController;
    readonly read: HumanRequestRead;
}) {
    const item = mapHumanRequestQueueItem(read);
    const isSelected = controller.selectedRequestId === item.requestId;

    return (
        <button
            aria-current={isSelected ? "true" : undefined}
            className={classNames(
                "w-full min-w-0 rounded-card border bg-surface-low p-3 text-left shadow-hairline transition-colors hover:border-primary/35 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                isSelected ? "border-primary/55 bg-primary-soft" : "border-outline-soft",
            )}
            onClick={() => {
                controller.selectRequest(item.requestId);
            }}
            type="button"
        >
            <div className="flex min-w-0 flex-wrap items-center gap-2">
                <StatusChip tone={kindTone(item.kind)}>{item.kind}</StatusChip>
                <StatusChip tone={statusTone(item.status)} withDot>
                    {item.status}
                </StatusChip>
            </div>
            <h2 className="mt-2 min-w-0 truncate font-display text-compact font-semibold text-foreground">
                {item.title}
            </h2>
            <div className="mt-2 flex min-w-0 flex-wrap gap-x-3 gap-y-1 font-mono text-label text-muted">
                <span>
                    {String(item.itemCount)} item{item.itemCount === 1 ? "" : "s"}
                </span>
                <span>
                    {item.dueAt === null ? "No due time" : "Due "}
                    <QueueTimestamp value={item.dueAt} />
                </span>
                <span className="truncate">{item.requesterNode}</span>
            </div>
        </button>
    );
}

function SelectedHumanRequest({ controller }: { readonly controller: HumanRequestsController }) {
    const read = controller.selectedRead;
    if (read === null) {
        return (
            <StatePanel
                summary="Select a request from the task queue."
                title="No selected request"
                tone="empty"
            />
        );
    }

    const editable = isRequestEditable(read);

    return (
        <div className="min-w-0 space-y-4">
            <Surface
                actions={
                    <div className="flex flex-wrap items-center gap-2">
                        <OpenTaskDetailLink taskId={controller.taskId} />
                        <Button
                            disabled={!editable || controller.isResolving}
                            icon={<Send />}
                            onClick={controller.resolveSelectedRequest}
                            variant="primary"
                        >
                            {controller.isResolving ? "Resolving" : "Resolve"}
                        </Button>
                    </div>
                }
                label={labelFromKind(read.request.kind)}
                title={read.request.title}
            >
                <div className="space-y-4">
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                        <StatusChip tone={kindTone(read.request.kind)}>
                            {read.request.kind}
                        </StatusChip>
                        <StatusChip tone={statusTone(read.request.status)} withDot>
                            {read.request.status}
                        </StatusChip>
                        <StatusChip tone="neutral">
                            {String(read.request.items.length)} item
                            {read.request.items.length === 1 ? "" : "s"}
                        </StatusChip>
                    </div>
                    <p className="max-w-4xl text-compact text-muted">{read.request.summary}</p>
                    <RequestMetadata read={read} />
                </div>
            </Surface>

            <Surface label="Instruction" title="Suggested human instruction">
                <p className="text-compact text-foreground">
                    {read.request.suggested_human_instruction}
                </p>
            </Surface>

            {read.resolution !== null || read.request.status !== "open" ? (
                <TerminalReadback read={read} />
            ) : (
                <FocusedRequestWorkbench controller={controller} />
            )}
        </div>
    );
}

function RequestMetadata({ read }: { readonly read: HumanRequestRead }) {
    return (
        <PropertyGrid
            items={[
                {
                    label: "Requester node",
                    value: <IdRefText value={read.request.requester_node} />,
                },
                {
                    label: "Opened",
                    value: <TimestampText value={read.request.opened_at} />,
                },
                {
                    label: "Due",
                    value:
                        read.request.timeout?.due_at === undefined ||
                        read.request.timeout.due_at === null ? (
                            "No due time"
                        ) : (
                            <TimestampText value={read.request.timeout.due_at} />
                        ),
                },
                {
                    label: "Timeout default",
                    value: read.request.timeout?.default_behavior ?? "No default behavior",
                },
            ]}
        />
    );
}

function OpenTaskDetailLink({ taskId }: { readonly taskId: string | null }) {
    return (
        <Link
            className={classNames(
                "inline-flex h-control items-center justify-center gap-2 rounded-control border border-outline bg-surface-low px-3 text-utility font-semibold text-foreground transition-colors hover:border-primary/45 hover:text-primary-foreground",
                taskId === null && "pointer-events-none opacity-55",
            )}
            to={taskId === null ? "/tasks" : `/tasks/${encodeURIComponent(taskId)}`}
        >
            <span>Open task detail</span>
            <ExternalLink aria-hidden="true" className="size-4 shrink-0" />
        </Link>
    );
}

function QueueTimestamp({ value }: { readonly value: string | null }) {
    if (value === null) {
        return null;
    }

    return <TimestampText value={value} />;
}

function kindTone(kind: components["schemas"]["HumanRequestKind"]): StatusTone {
    switch (kind) {
        case "direction":
            return "active";
        case "approval":
            return "warning";
        case "input":
            return "neutral";
        case "review":
            return "success";
    }
}

function statusTone(status: HumanRequestStatus): StatusTone {
    switch (status) {
        case "open":
            return "warning";
        case "resolved":
            return "success";
        case "cancelled":
        case "timed_out":
            return "danger";
    }
}
