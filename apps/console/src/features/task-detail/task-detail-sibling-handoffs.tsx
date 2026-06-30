import type { ReactNode } from "react";

import { ExternalLink } from "lucide-react";
import { Link } from "react-router-dom";

import { IdRefText, StatusChip, Surface } from "../../components/ui";
import {
    commandRunTone,
    humanRequestTone,
    type CommandRunPreview,
    type HumanRequestPreview,
    type TaskDetailView,
} from "./task-detail-model";

export function SiblingHandoffs({
    taskId,
    view,
}: {
    readonly taskId: string;
    readonly view: TaskDetailView;
}) {
    return (
        <div className="grid gap-4">
            <SiblingPanel
                emptySummary="No controller-backed human request preview is available."
                items={view.humanRequests}
                renderItem={(item) => <HumanRequestPreviewItem item={item} />}
                title="Human Requests"
                to={`/tasks/${encodeURIComponent(taskId)}/human-requests`}
            />
            <SiblingPanel
                emptySummary="No controller-backed command run preview is available."
                items={view.commandRuns}
                renderItem={(item) => <CommandRunPreviewItem item={item} />}
                title="Command Runs"
                to={`/tasks/${encodeURIComponent(taskId)}/command-runs`}
            />
        </div>
    );
}

function SiblingPanel<T>({
    emptySummary,
    items,
    renderItem,
    title,
    to,
}: {
    readonly emptySummary: string;
    readonly items: readonly T[];
    readonly renderItem: (item: T) => ReactNode;
    readonly title: string;
    readonly to: string;
}) {
    return (
        <Surface
            actions={
                <Link
                    className="inline-flex h-control items-center gap-2 rounded-control border border-outline bg-surface-low px-3 text-utility font-semibold text-foreground transition-colors hover:border-primary/45 hover:text-primary-foreground"
                    to={to}
                >
                    Open {title}
                    <ExternalLink aria-hidden="true" className="size-4" />
                </Link>
            }
            label="Sibling handoff"
            title={title}
        >
            {items.length === 0 ? (
                <p className="text-compact text-muted">{emptySummary}</p>
            ) : (
                <div className="space-y-2">
                    {items.slice(0, 2).map((item, index) => (
                        <div key={index}>{renderItem(item)}</div>
                    ))}
                </div>
            )}
        </Surface>
    );
}

function HumanRequestPreviewItem({ item }: { readonly item: HumanRequestPreview }) {
    return (
        <article className="rounded-card border border-outline-soft bg-surface-low p-3">
            <div className="flex min-w-0 flex-wrap items-center gap-2">
                <StatusChip tone={humanRequestTone(item.status)} withDot>
                    {item.status}
                </StatusChip>
                <span className="font-mono text-label font-medium uppercase text-muted">
                    {item.kind}
                </span>
            </div>
            <h3 className="mt-2 truncate font-display text-compact font-semibold text-foreground">
                {item.title}
            </h3>
            <IdRefText className="mt-1 block" value={item.requestId} />
        </article>
    );
}

function CommandRunPreviewItem({ item }: { readonly item: CommandRunPreview }) {
    return (
        <article className="rounded-card border border-outline-soft bg-surface-low p-3">
            <StatusChip tone={commandRunTone(item.state)} withDot>
                {item.state}
            </StatusChip>
            <h3 className="mt-2 truncate font-display text-compact font-semibold text-foreground">
                {item.description ?? item.runId}
            </h3>
            <div className="mt-1 flex min-w-0 flex-wrap items-center gap-2">
                <IdRefText value={item.runId} />
                {item.hasLog ? (
                    <span className="font-mono text-label text-muted">log_ref</span>
                ) : null}
            </div>
        </article>
    );
}
