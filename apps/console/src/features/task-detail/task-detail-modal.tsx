import { type KeyboardEvent, useEffect, useRef } from "react";

import { X } from "lucide-react";

import {
    CodeBlock,
    IdRefText,
    PropertyGrid,
    StatePanel,
    StatusChip,
    Tabs,
    type PropertyGridItem,
} from "../../components/ui";
import type { TaskDetailController } from "./task-detail-controller";
import {
    TASK_DETAIL_TABS,
    type DetailRow,
    type TaskDetailRef,
    type TaskDetailTab,
} from "./task-detail-model";

export function TaskDetailModal({
    context,
    onClose,
    onTabChange,
    tab,
    taskId,
}: {
    readonly context: NonNullable<TaskDetailController["selectedContext"]>;
    readonly onClose: () => void;
    readonly onTabChange: (tab: TaskDetailTab) => void;
    readonly tab: TaskDetailTab;
    readonly taskId: string;
}) {
    const closeButtonRef = useRef<HTMLButtonElement>(null);
    const dialogRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        closeButtonRef.current?.focus({ preventScroll: true });
    }, []);

    const handleDialogKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
        if (event.key !== "Tab") {
            return;
        }

        const dialogElement = dialogRef.current;
        if (dialogElement === null) {
            return;
        }

        const focusableElements = getFocusableElements(dialogElement);
        if (focusableElements.length === 0) {
            event.preventDefault();
            return;
        }
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (event.shiftKey && document.activeElement === firstElement) {
            event.preventDefault();
            lastElement.focus();
            return;
        }

        if (!event.shiftKey && document.activeElement === lastElement) {
            event.preventDefault();
            firstElement.focus();
        }
    };

    return (
        <div
            aria-labelledby="task-detail-modal-title"
            aria-modal="true"
            className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/30 px-4 py-6 backdrop-blur-sm"
            onKeyDown={handleDialogKeyDown}
            ref={dialogRef}
            role="dialog"
        >
            <section className="max-h-[calc(100vh-3rem)] w-full max-w-4xl overflow-hidden rounded-shell border border-outline-soft bg-surface shadow-popover">
                <header className="flex items-start justify-between gap-4 border-b border-outline-soft px-5 py-4">
                    <div className="min-w-0">
                        <p className="font-mono text-label font-medium uppercase text-muted">
                            Node detail
                        </p>
                        <h2
                            className="mt-1 truncate font-display text-compact font-semibold text-foreground"
                            id="task-detail-modal-title"
                        >
                            {context.node?.nodeKey ?? taskId}
                        </h2>
                    </div>
                    <button
                        aria-label="Close node detail"
                        className="inline-flex size-icon-control items-center justify-center rounded-control border border-outline bg-surface-low px-0 text-utility font-semibold text-foreground transition-colors hover:border-primary/45 hover:text-primary-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                        onClick={onClose}
                        ref={closeButtonRef}
                        title="Close node detail"
                        type="button"
                    >
                        <span
                            aria-hidden="true"
                            className="inline-flex size-4 items-center justify-center"
                        >
                            <X />
                        </span>
                    </button>
                </header>
                <div className="max-h-[calc(100vh-9rem)] overflow-y-auto px-5 py-4">
                    <Tabs
                        label="Selected detail views"
                        onChange={onTabChange}
                        tabs={TASK_DETAIL_TABS.map((tabOption) => ({
                            label: tabOption.label,
                            panelId: `task-detail-${tabOption.value}`,
                            value: tabOption.value,
                        }))}
                        value={tab}
                    />
                    <div className="mt-4" id={`task-detail-${tab}`} role="tabpanel">
                        <TaskDetailTabPanel context={context} tab={tab} taskId={taskId} />
                    </div>
                </div>
            </section>
        </div>
    );
}

function getFocusableElements(root: HTMLElement): readonly HTMLElement[] {
    return Array.from(
        root.querySelectorAll<HTMLElement>(
            'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
    ).filter(
        (element) =>
            element.tabIndex >= 0 &&
            !element.hasAttribute("hidden") &&
            element.getAttribute("aria-hidden") !== "true",
    );
}

function TaskDetailTabPanel({
    context,
    tab,
    taskId,
}: {
    readonly context: NonNullable<TaskDetailController["selectedContext"]>;
    readonly tab: TaskDetailTab;
    readonly taskId: string;
}) {
    switch (tab) {
        case "overview":
            return <DetailRows rows={context.overviewRows} />;
        case "checkpoint":
            return <DetailRows rows={context.checkpointRows} />;
        case "assignment":
            return <DetailRows rows={context.assignmentRows} />;
        case "boundary":
            return <DetailRows rows={context.boundaryRows} />;
        case "artifacts":
            return <ArtifactRefs refs={context.artifactRefs} />;
        case "trace":
            return (
                <CodeBlock title="Trace">
                    {context.traceJson === "{}"
                        ? `No selected task event for ${taskId}.`
                        : context.traceJson}
                </CodeBlock>
            );
    }
}

function DetailRows({ rows }: { readonly rows: readonly DetailRow[] }) {
    const items: readonly PropertyGridItem[] = rows.map((row) => ({
        label: row.label,
        value: row.value,
    }));

    return <PropertyGrid items={items} />;
}

function ArtifactRefs({ refs }: { readonly refs: readonly TaskDetailRef[] }) {
    if (refs.length === 0) {
        return (
            <StatePanel
                summary="No controller-backed refs were exposed for the selected context."
                title="No artifact refs"
                tone="empty"
            />
        );
    }

    return (
        <div className="space-y-2">
            {refs.map((ref) => (
                <article
                    className="rounded-card border border-outline-soft bg-surface-low p-3"
                    key={`${ref.kind}-${ref.label}-${ref.path ?? ""}`}
                >
                    <div className="flex min-w-0 flex-wrap items-center gap-2">
                        <StatusChip>{ref.kind}</StatusChip>
                        <span className="font-display text-compact font-semibold text-foreground">
                            {ref.label}
                        </span>
                    </div>
                    {ref.description === null ? null : (
                        <p className="mt-2 text-compact text-muted">{ref.description}</p>
                    )}
                    {ref.path === null ? null : (
                        <IdRefText className="mt-1 block" value={ref.path} />
                    )}
                </article>
            ))}
        </div>
    );
}
