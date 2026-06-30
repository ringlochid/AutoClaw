import { ExternalLink, RefreshCw, Send } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { PageFrame, useShellTaskTitle } from "../../components/layout";
import {
    Button,
    IdRefText,
    PropertyGrid,
    StatePanel,
    StatusChip,
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
import { isRequestEditable, mapHumanRequestQueueItem } from "./human-request-model";
import { TerminalReadback } from "./human-request-terminal-readback";
import { FocusedRequestWorkbench } from "./human-request-workbench";

type HumanRequestRead = components["schemas"]["HumanRequestRead"];
type HumanRequestStatus = components["schemas"]["HumanRequestStatus"];

export function HumanRequestsPage() {
    const { taskId } = useParams();
    const controller = useHumanRequestsController(taskId ?? null);
    const pageTitle = controller.taskTitle ?? controller.taskId ?? "Selected task";
    useShellTaskTitle(controller.taskId, controller.taskTitle);

    return (
        <PageFrame
            actions={<HumanRequestsHeaderActions controller={controller} />}
            eyebrow="Human Requests"
            title={pageTitle}
        >
            <HumanRequestsState controller={controller} />
        </PageFrame>
    );
}

function HumanRequestsHeaderActions({
    controller,
}: {
    readonly controller: HumanRequestsController;
}) {
    const { openCount, terminalCount } = useMemo(
        () => getRequestCounts(controller.requestReads),
        [controller.requestReads],
    );

    return (
        <>
            {controller.requestReads.length === 0 ? (
                <StatusChip tone="neutral">{controller.statusSummary}</StatusChip>
            ) : (
                <>
                    <StatusChip tone="neutral">{String(openCount)} pending</StatusChip>
                    <StatusChip tone="neutral">{String(terminalCount)} terminal</StatusChip>
                </>
            )}
            <Button
                disabled={controller.isLoading || controller.isRefreshing}
                icon={<RefreshCw className={controller.isRefreshing ? "animate-spin" : ""} />}
                onClick={controller.refresh}
            >
                Refresh
            </Button>
        </>
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
        <div className="grid min-w-0 overflow-hidden rounded-card border border-outline-soft bg-surface-low xl:grid-cols-[19rem_minmax(0,1fr)]">
            <HumanRequestQueue controller={controller} />
            <SelectedHumanRequest controller={controller} />
        </div>
    );
}

function HumanRequestQueue({ controller }: { readonly controller: HumanRequestsController }) {
    const { openCount, terminalCount } = getRequestCounts(controller.requestReads);

    return (
        <aside
            className="hidden min-w-0 border-b border-outline-soft bg-surface-low p-4 xl:block xl:border-b-0 xl:border-r"
            aria-label="Task-scoped human request queue"
        >
            <div className="mb-4 flex min-w-0 items-center justify-between gap-3">
                <div className="min-w-0">
                    <p className="font-mono text-label font-medium uppercase text-muted">
                        Requests
                    </p>
                    <h2 className="mt-1 font-display text-compact font-semibold text-foreground">
                        Task queue
                    </h2>
                </div>
                <StatusChip tone="neutral">{String(openCount)} open</StatusChip>
            </div>
            {openCount === 0 ? (
                <StatePanel
                    className="mb-3"
                    summary="Closed requests remain available as terminal readback."
                    title="No pending requests"
                    tone="empty"
                />
            ) : null}
            <ol aria-label="Human request queue" className="space-y-2">
                {controller.requestReads.map((read) => (
                    <li key={read.request.request_id}>
                        <HumanRequestQueueButton controller={controller} read={read} />
                    </li>
                ))}
            </ol>
            {terminalCount > 0 ? (
                <p className="mt-3 font-mono text-label text-muted">
                    {String(terminalCount)} terminal request
                    {terminalCount === 1 ? "" : "s"}
                </p>
            ) : null}
        </aside>
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
                "w-full min-w-0 rounded-card border bg-surface p-3 text-left transition-colors hover:border-primary/35 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                isSelected
                    ? "border-primary/55 bg-primary-soft shadow-panel"
                    : "border-outline-soft shadow-hairline",
            )}
            onClick={() => {
                controller.selectRequest(item.requestId);
            }}
            type="button"
        >
            <div className="flex min-w-0 flex-wrap items-start justify-between gap-x-3 gap-y-1">
                <StatusChip tone={kindTone(item.kind)}>{item.kind}</StatusChip>
                <span className="min-w-0 break-all font-mono text-label text-muted">
                    {queueStatusLabel(read)}
                </span>
            </div>
            <h2
                className={classNames(
                    "mt-2 min-w-0 font-display text-compact font-semibold text-foreground",
                    isSelected && "text-primary-foreground",
                )}
            >
                {item.title}
            </h2>
            <div className="mt-2 flex min-w-0 flex-wrap gap-x-3 gap-y-1 font-mono text-label text-muted">
                <span>
                    {String(item.itemCount)} item{item.itemCount === 1 ? "" : "s"}
                </span>
                <span className="truncate">{item.requesterNode}</span>
            </div>
        </button>
    );
}

function SelectedHumanRequest({ controller }: { readonly controller: HumanRequestsController }) {
    const read = controller.selectedRead;
    const headingRef = useRef<HTMLHeadingElement>(null);
    const previousRequestIdRef = useRef<string | null>(null);

    useEffect(() => {
        const requestId = read?.request.request_id ?? null;
        if (previousRequestIdRef.current !== null && previousRequestIdRef.current !== requestId) {
            headingRef.current?.focus();
        }
        previousRequestIdRef.current = requestId;
    }, [read]);

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
        <section className="min-w-0 space-y-4 bg-surface p-4 sm:p-5">
            <div className="border-b border-outline-soft pb-4">
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
                    <div className="flex min-w-0 flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                        <div className="min-w-0 max-w-4xl">
                            <h2
                                className="font-display text-display font-semibold text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                                ref={headingRef}
                                tabIndex={-1}
                            >
                                {read.request.title}
                            </h2>
                            <p className="mt-2 text-body text-muted">{read.request.summary}</p>
                        </div>
                        <SelectedRequestActions
                            className="hidden shrink-0 flex-wrap items-center gap-2 lg:flex"
                            controller={controller}
                            editable={editable}
                        />
                    </div>
                    <RequestMetadata read={read} />
                </div>
            </div>

            {read.resolution !== null || read.request.status !== "open" ? (
                <TerminalReadback read={read} />
            ) : (
                <FocusedRequestWorkbench controller={controller} />
            )}
            <SelectedRequestActions
                className="flex flex-col gap-3 sm:flex-row lg:hidden"
                controlClassName="w-full sm:w-auto"
                controller={controller}
                editable={editable}
            />
            <MobileRequestQueueSummary controller={controller} />
        </section>
    );
}

function SelectedRequestActions({
    className,
    controlClassName,
    controller,
    editable,
}: {
    readonly className?: string;
    readonly controlClassName?: string;
    readonly controller: HumanRequestsController;
    readonly editable: boolean;
}) {
    return (
        <div className={className}>
            <OpenTaskDetailLink className={controlClassName} taskId={controller.taskId} />
            <Button
                className={controlClassName}
                disabled={!editable || controller.isResolving}
                icon={<Send />}
                onClick={controller.resolveSelectedRequest}
                variant="primary"
            >
                {controller.isResolving ? "Resolving" : "Resolve"}
            </Button>
        </div>
    );
}

function MobileRequestQueueSummary({
    controller,
}: {
    readonly controller: HumanRequestsController;
}) {
    const [isOpen, setIsOpen] = useState(false);
    const otherReads = controller.requestReads.filter(
        (read) => read.request.request_id !== controller.selectedRequestId,
    );
    const otherOpenCount = otherReads.filter((read) => read.request.status === "open").length;
    const otherTerminalCount = otherReads.length - otherOpenCount;

    return (
        <details
            className="rounded-card border border-outline-soft bg-surface-low px-3 py-2 shadow-hairline xl:hidden"
            onToggle={(event) => {
                setIsOpen(event.currentTarget.open);
            }}
        >
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 font-display text-compact font-semibold text-foreground marker:hidden">
                <span>Other requests</span>
                <span className="font-mono text-label font-medium text-muted">
                    {String(otherOpenCount)} open / {String(otherTerminalCount)} closed
                </span>
            </summary>
            {!isOpen ? null : otherReads.length === 0 ? (
                <p className="mt-3 text-compact text-muted">No other request records.</p>
            ) : (
                <ol aria-label="Other human requests" className="mt-3 space-y-2">
                    {otherReads.map((read) => (
                        <li key={read.request.request_id}>
                            <HumanRequestQueueButton controller={controller} read={read} />
                        </li>
                    ))}
                </ol>
            )}
        </details>
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
            ]}
        />
    );
}

function OpenTaskDetailLink({
    className,
    taskId,
}: {
    readonly className?: string;
    readonly taskId: string | null;
}) {
    return (
        <Link
            className={classNames(
                "inline-flex h-control items-center justify-center gap-2 rounded-control border border-outline bg-surface-low px-3 text-utility font-semibold text-foreground transition-colors hover:border-primary/45 hover:text-primary-foreground",
                className,
                taskId === null && "pointer-events-none opacity-55",
            )}
            to={taskId === null ? "/tasks" : `/tasks/${encodeURIComponent(taskId)}`}
        >
            <span>Open task detail</span>
            <ExternalLink aria-hidden="true" className="size-4 shrink-0" />
        </Link>
    );
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

function getRequestCounts(reads: readonly HumanRequestRead[]): {
    readonly openCount: number;
    readonly terminalCount: number;
} {
    const openCount = reads.filter((read) => read.request.status === "open").length;
    return {
        openCount,
        terminalCount: reads.length - openCount,
    };
}

function queueStatusLabel(read: HumanRequestRead): string {
    if (read.request.status === "open") {
        if (read.request.timeout?.due_at === undefined || read.request.timeout.due_at === null) {
            return "No due time";
        }

        return `Due ${formatShortTimestamp(read.request.timeout.due_at)}`;
    }

    if (read.resolution?.resolved_at !== undefined) {
        return formatShortTimestamp(read.resolution.resolved_at);
    }

    return read.request.status;
}

function formatShortTimestamp(value: string): string {
    return new Intl.DateTimeFormat(undefined, {
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
        month: "short",
    }).format(new Date(value));
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
