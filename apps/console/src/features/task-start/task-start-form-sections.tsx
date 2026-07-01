import { useEffect, useRef, type ReactNode } from "react";

import { Eye, Rocket, X } from "lucide-react";

import {
    Button,
    FormField,
    IdRefText,
    PropertyGrid,
    SegmentedControl,
    StatePanel,
    StatusChip,
} from "../../components/ui";
import type { TaskStartController } from "./task-start-controller";
import { isAuthError } from "./task-start-data";
import {
    TASK_ROOT_MODE_OPTIONS,
    shouldShowHostPath,
    type TaskRootMode,
    type TaskStartPreview,
    type TaskStartResultView,
} from "./task-start-model";
import { controlClassName, textAreaClassName } from "./task-start-ui";

export function TaskIdentitySection({ controller }: { readonly controller: TaskStartController }) {
    return (
        <div className="grid gap-4 lg:grid-cols-2">
            <FormField error={controller.formErrors.taskKey} id="task-start-key" label="Task key">
                <input
                    className={controlClassName()}
                    onChange={(event) => {
                        controller.setField("taskKey", event.target.value);
                    }}
                    value={controller.form.taskKey}
                />
            </FormField>
            <FormField error={controller.formErrors.title} id="task-start-title" label="Title">
                <input
                    className={controlClassName()}
                    onChange={(event) => {
                        controller.setField("title", event.target.value);
                    }}
                    value={controller.form.title}
                />
            </FormField>
            <div className="lg:col-span-2">
                <FormField
                    error={controller.formErrors.summary}
                    id="task-start-summary"
                    label="Summary"
                >
                    <textarea
                        className={textAreaClassName()}
                        onChange={(event) => {
                            controller.setField("summary", event.target.value);
                        }}
                        rows={3}
                        value={controller.form.summary}
                    />
                </FormField>
            </div>
            <div className="lg:col-span-2">
                <FormField id="task-start-instruction" label="Instruction">
                    <textarea
                        className={textAreaClassName()}
                        onChange={(event) => {
                            controller.setField("instruction", event.target.value);
                        }}
                        rows={3}
                        value={controller.form.instruction}
                    />
                </FormField>
            </div>
        </div>
    );
}

export function RootsSection({ controller }: { readonly controller: TaskStartController }) {
    return (
        <div className="divide-y divide-outline-soft rounded-card border border-outline-soft bg-surface-low shadow-hairline">
            <RootBindingControl
                error={controller.formErrors.workspaceHostPath}
                hostPath={controller.form.workspaceHostPath}
                label="Workspace"
                mode={controller.form.workspaceMode}
                onHostPathChange={(value) => {
                    controller.setField("workspaceHostPath", value);
                }}
                onModeChange={(mode) => {
                    controller.setRootMode("workspace", mode);
                }}
            />
            <RootBindingControl
                error={controller.formErrors.contextHostPath}
                hostPath={controller.form.contextHostPath}
                label="Context"
                mode={controller.form.contextMode}
                onHostPathChange={(value) => {
                    controller.setField("contextHostPath", value);
                }}
                onModeChange={(mode) => {
                    controller.setRootMode("context", mode);
                }}
            />
        </div>
    );
}

export function TaskStartSection({
    children,
    label,
}: {
    readonly children: ReactNode;
    readonly label: string;
}) {
    const headingId = `task-start-section-${label.toLowerCase()}`;

    return (
        <section
            aria-labelledby={headingId}
            className="grid gap-4 py-5 lg:grid-cols-[8.5rem_minmax(0,1fr)]"
        >
            <h2
                className="font-mono text-label font-medium uppercase text-muted lg:pt-2"
                id={headingId}
            >
                {label}
            </h2>
            <div className="min-w-0">{children}</div>
        </section>
    );
}

function RootBindingControl({
    error,
    hostPath,
    label,
    mode,
    onHostPathChange,
    onModeChange,
}: {
    readonly error: string | undefined;
    readonly hostPath: string;
    readonly label: string;
    readonly mode: TaskRootMode;
    readonly onHostPathChange: (value: string) => void;
    readonly onModeChange: (mode: TaskRootMode) => void;
}) {
    const hostPathId = `task-start-${label.toLowerCase()}-host-path`;

    return (
        <section aria-label={`${label} root`} className="p-4">
            <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                <div className="min-w-0">
                    <h2 className="font-display text-compact font-semibold text-foreground">
                        {label}
                    </h2>
                </div>
                <SegmentedControl
                    label={`${label} root mode`}
                    onChange={onModeChange}
                    options={TASK_ROOT_MODE_OPTIONS}
                    value={mode}
                />
            </div>
            {shouldShowHostPath(mode) ? (
                <div className="mt-4">
                    <FormField error={error} id={hostPathId} label="Host path">
                        <input
                            className={controlClassName()}
                            onChange={(event) => {
                                onHostPathChange(event.target.value);
                            }}
                            placeholder={
                                mode === "ensure_host_path"
                                    ? "/home/ubuntu/workspace/new-task-root"
                                    : "/home/ubuntu/workspace/existing-root"
                            }
                            value={hostPath}
                        />
                    </FormField>
                </div>
            ) : null}
        </section>
    );
}

export function TaskStartActions({ controller }: { readonly controller: TaskStartController }) {
    return (
        <div className="flex flex-col gap-3 rounded-card border border-outline-soft bg-surface-low p-4 shadow-hairline sm:flex-row sm:items-center sm:justify-between">
            <p className="text-compact text-muted">
                {controller.selectedWorkflowKey === null
                    ? "Select a stored workflow before starting a task."
                    : "Ready to start from the selected workflow."}
            </p>
            <div className="flex flex-wrap gap-2">
                <Button icon={<Eye />} onClick={controller.showPreview}>
                    Preview
                </Button>
                <Button
                    disabled={controller.submitState.isSubmitting}
                    icon={<Rocket />}
                    onClick={controller.start}
                    variant="primary"
                >
                    {controller.submitState.isSubmitting ? "Starting" : "Start Task"}
                </Button>
            </div>
        </div>
    );
}

export function PreviewPanel({
    onClose,
    onStart,
    preview,
    startDisabled,
}: {
    readonly onClose: () => void;
    readonly onStart: () => void;
    readonly preview: TaskStartPreview;
    readonly startDisabled: boolean;
}) {
    return (
        <TaskStartDialog
            footer={
                <>
                    <Button data-dialog-initial-focus onClick={onClose}>
                        Back to edit
                    </Button>
                    <Button
                        disabled={startDisabled}
                        icon={<Rocket />}
                        onClick={onStart}
                        variant="primary"
                    >
                        {startDisabled ? "Starting" : "Start Task"}
                    </Button>
                </>
            }
            label="Preview"
            onClose={onClose}
            title="Preview"
        >
            <dl className="overflow-hidden rounded-card border border-outline-soft bg-surface-low">
                <PreviewReadbackRow label="Workflow">
                    <p className="break-all font-mono text-compact font-semibold text-foreground">
                        {preview.workflowKey}
                    </p>
                    <p className="mt-1 break-words text-compact text-muted">
                        {preview.workflowDescription}
                    </p>
                </PreviewReadbackRow>
                <PreviewReadbackRow label="Task">
                    <p className="break-words font-display text-compact font-semibold text-foreground">
                        {preview.title}
                    </p>
                    <IdRefText className="mt-1 break-all" value={preview.taskKey} />
                </PreviewReadbackRow>
                <PreviewReadbackRow label="Summary">{preview.summary}</PreviewReadbackRow>
                <PreviewReadbackRow label="Instruction">
                    {preview.instructionSummary}
                </PreviewReadbackRow>
                <PreviewReadbackRow label="Workspace">
                    <p className="font-display text-compact font-semibold text-foreground">
                        {preview.workspaceModeLabel}
                    </p>
                    <p className="mt-1 text-compact text-muted">{preview.workspaceSummary}</p>
                </PreviewReadbackRow>
                <PreviewReadbackRow label="Context">
                    <p className="font-display text-compact font-semibold text-foreground">
                        {preview.contextModeLabel}
                    </p>
                    <p className="mt-1 text-compact text-muted">{preview.contextSummary}</p>
                </PreviewReadbackRow>
            </dl>
        </TaskStartDialog>
    );
}

function PreviewReadbackRow({
    children,
    label,
}: {
    readonly children: ReactNode;
    readonly label: string;
}) {
    return (
        <div className="grid gap-3 border-b border-outline-soft px-4 py-3 last:border-b-0 sm:grid-cols-[8.5rem_minmax(0,1fr)]">
            <dt className="font-mono text-label font-medium uppercase text-muted">{label}</dt>
            <dd className="min-w-0 text-compact text-foreground">{children}</dd>
        </div>
    );
}

export function ResultPanel({ controller }: { readonly controller: TaskStartController }) {
    if (!controller.resultOpen) {
        return null;
    }

    if (controller.submitState.error !== null) {
        const error = controller.submitState.error;
        return (
            <TaskStartDialog
                footer={
                    <>
                        <Button
                            data-dialog-initial-focus
                            onClick={() => {
                                controller.setResultOpen(false);
                            }}
                        >
                            Back to edit
                        </Button>
                        <Button onClick={controller.start} variant="primary">
                            Retry Start Task
                        </Button>
                    </>
                }
                label="Result"
                onClose={() => {
                    controller.setResultOpen(false);
                }}
                title={
                    isAuthError(error)
                        ? "Access to Task Start failed"
                        : error.source === "validation"
                          ? "Task Start validation failed"
                          : "Task could not start"
                }
            >
                <StatePanel
                    summary={error.summary}
                    title={
                        isAuthError(error)
                            ? "Access to Task Start failed"
                            : error.source === "validation"
                              ? "Task Start validation failed"
                              : "Task could not start"
                    }
                    tone={isAuthError(error) ? "auth" : "error"}
                />
            </TaskStartDialog>
        );
    }

    if (controller.submitState.result === null) {
        return null;
    }

    return (
        <TaskStartResult
            onClose={() => {
                controller.setResultOpen(false);
            }}
            result={controller.submitState.result}
        />
    );
}

function TaskStartResult({
    onClose,
    result,
}: {
    readonly onClose: () => void;
    readonly result: TaskStartResultView;
}) {
    return (
        <TaskStartDialog
            footer={
                <Button data-dialog-initial-focus onClick={onClose}>
                    Back to edit
                </Button>
            }
            label="Result"
            onClose={onClose}
            title="Result"
        >
            <div className="grid gap-4 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
                <StatePanel
                    summary="Initial runtime effects were accepted and the task handoff is ready for the Tasks surface."
                    title="Task start accepted"
                    tone="success"
                />
                <PropertyGrid
                    items={[
                        {
                            label: "Flow status",
                            value: (
                                <StatusChip tone={result.flowStatusTone} withDot>
                                    {result.flowStatusLabel}
                                </StatusChip>
                            ),
                        },
                        { label: "Handoff", value: "Open Tasks to inspect runtime detail." },
                        { label: "Manifest", value: result.manifestDescription },
                    ]}
                />
            </div>
        </TaskStartDialog>
    );
}

function TaskStartDialog({
    children,
    footer,
    label,
    onClose,
    title,
}: {
    readonly children: ReactNode;
    readonly footer: ReactNode;
    readonly label: string;
    readonly onClose: () => void;
    readonly title: string;
}) {
    const dialogRef = useRef<HTMLElement | null>(null);
    const onCloseRef = useRef(onClose);
    const previousFocusRef = useRef<HTMLElement | null>(null);

    useEffect(() => {
        onCloseRef.current = onClose;
    }, [onClose]);

    useEffect(() => {
        const activeElement = document.activeElement;
        previousFocusRef.current =
            activeElement instanceof HTMLElement && activeElement !== document.body
                ? activeElement
                : null;
        const dialog = dialogRef.current;
        const initialFocusTarget = dialog?.querySelector<HTMLElement>(
            "[data-dialog-initial-focus]",
        );
        const focusableElements = getDialogFocusableElements(dialog);
        const focusTarget =
            initialFocusTarget ?? (focusableElements.length > 0 ? focusableElements[0] : dialog);
        focusTarget?.focus({ preventScroll: true });

        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") {
                event.preventDefault();
                event.stopPropagation();
                onCloseRef.current();
                return;
            }

            if (event.key !== "Tab") {
                return;
            }

            const currentDialog = dialogRef.current;
            const focusableElements = getDialogFocusableElements(currentDialog);
            if (currentDialog === null || focusableElements.length === 0) {
                event.preventDefault();
                currentDialog?.focus({ preventScroll: true });
                return;
            }

            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];
            const activeDialogElement = document.activeElement;

            if (
                event.shiftKey &&
                (activeDialogElement === firstElement ||
                    !(activeDialogElement instanceof HTMLElement) ||
                    !currentDialog.contains(activeDialogElement))
            ) {
                event.preventDefault();
                lastElement.focus({ preventScroll: true });
                return;
            }

            if (!event.shiftKey && activeDialogElement === lastElement) {
                event.preventDefault();
                firstElement.focus({ preventScroll: true });
                return;
            }

            if (
                activeDialogElement instanceof HTMLElement &&
                !currentDialog.contains(activeDialogElement)
            ) {
                event.preventDefault();
                firstElement.focus({ preventScroll: true });
            }
        };

        document.body.classList.add("overflow-hidden");
        document.addEventListener("keydown", handleKeyDown, true);
        return () => {
            document.body.classList.remove("overflow-hidden");
            document.removeEventListener("keydown", handleKeyDown, true);
            const previousFocus = previousFocusRef.current;
            if (previousFocus?.isConnected === true) {
                previousFocus.focus({ preventScroll: true });
            }
        };
    }, []);

    return (
        <div
            className="fixed inset-0 z-50 grid place-items-center bg-foreground/35 p-4 backdrop-blur-[2px]"
            role="presentation"
        >
            <section
                aria-labelledby="task-start-dialog-title"
                aria-modal="true"
                className="max-h-[calc(100vh-4rem)] w-full max-w-2xl overflow-hidden rounded-shell border border-outline-soft bg-surface shadow-popover"
                ref={dialogRef}
                role="dialog"
                tabIndex={-1}
            >
                <header className="flex items-start justify-between gap-4 border-b border-outline-soft px-5 py-4">
                    <div className="min-w-0">
                        <p className="font-mono text-label font-medium uppercase text-muted">
                            {label}
                        </p>
                        <h2
                            className="mt-1 font-display text-compact font-semibold text-foreground"
                            id="task-start-dialog-title"
                        >
                            {title}
                        </h2>
                    </div>
                    <button
                        aria-label={`Close ${label.toLowerCase()}`}
                        className="inline-flex size-icon-control shrink-0 items-center justify-center rounded-control border border-outline bg-surface-low text-muted transition-colors hover:border-primary/45 hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                        onClick={onClose}
                        type="button"
                    >
                        <X aria-hidden="true" className="size-4" />
                    </button>
                </header>
                <div
                    className="max-h-[calc(100vh-14rem)] overflow-y-auto px-5 py-5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-primary"
                    tabIndex={0}
                >
                    {children}
                </div>
                <footer className="flex flex-col gap-2 border-t border-outline-soft px-5 py-4 sm:flex-row sm:justify-end">
                    {footer}
                </footer>
            </section>
        </div>
    );
}

function getDialogFocusableElements(dialog: HTMLElement | null): HTMLElement[] {
    if (dialog === null) {
        return [];
    }

    return Array.from(
        dialog.querySelectorAll<HTMLElement>(
            [
                "a[href]",
                "button:not([disabled])",
                "input:not([disabled])",
                "select:not([disabled])",
                "textarea:not([disabled])",
                "[tabindex]:not([tabindex='-1'])",
            ].join(", "),
        ),
    ).filter(
        (element) =>
            element.tabIndex >= 0 &&
            !element.hasAttribute("hidden") &&
            element.getAttribute("aria-hidden") !== "true",
    );
}
