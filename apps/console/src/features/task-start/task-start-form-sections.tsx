import { useEffect, useRef, type ReactNode } from "react";

import { X } from "lucide-react";

import { Button, FormField, IdRefText, StatePanel } from "../../components/ui";
import { classNames } from "../../lib/classNames";
import type { TaskStartController } from "./task-start-controller";
import { isAuthError } from "./task-start-data";
import {
    TASK_START_FIELD_PLACEHOLDERS,
    TASK_ROOT_MODE_OPTIONS,
    countTaskStartRequiredInputs,
    shouldShowHostPath,
    type TaskRootMode,
    type TaskStartPreview,
} from "./task-start-model";
import { controlClassName, textAreaClassName } from "./task-start-ui";

export function TaskIdentitySection({ controller }: { readonly controller: TaskStartController }) {
    const labelClassName =
        "font-display text-compact font-semibold tracking-normal !normal-case text-foreground";

    return (
        <div className="grid gap-4 lg:grid-cols-2">
            <FormField
                error={controller.formErrors.taskKey}
                id="task-start-key"
                label="Task key"
                labelClassName={labelClassName}
            >
                <input
                    className={controlClassName()}
                    onChange={(event) => {
                        controller.setField("taskKey", event.target.value);
                    }}
                    placeholder={TASK_START_FIELD_PLACEHOLDERS.taskKey}
                    value={controller.form.taskKey}
                />
            </FormField>
            <FormField
                error={controller.formErrors.title}
                id="task-start-title"
                label="Title"
                labelClassName={labelClassName}
            >
                <input
                    className={controlClassName()}
                    onChange={(event) => {
                        controller.setField("title", event.target.value);
                    }}
                    placeholder={TASK_START_FIELD_PLACEHOLDERS.title}
                    value={controller.form.title}
                />
            </FormField>
            <div className="lg:col-span-2">
                <FormField
                    error={controller.formErrors.summary}
                    id="task-start-summary"
                    label="Summary"
                    labelClassName={labelClassName}
                >
                    <textarea
                        className={textAreaClassName("min-h-19")}
                        onChange={(event) => {
                            controller.setField("summary", event.target.value);
                        }}
                        placeholder={TASK_START_FIELD_PLACEHOLDERS.summary}
                        rows={3}
                        value={controller.form.summary}
                    />
                </FormField>
            </div>
            <div className="lg:col-span-2">
                <FormField
                    id="task-start-instruction"
                    label="Instruction"
                    labelClassName={labelClassName}
                >
                    <textarea
                        className={textAreaClassName("min-h-21")}
                        onChange={(event) => {
                            controller.setField("instruction", event.target.value);
                        }}
                        placeholder={TASK_START_FIELD_PLACEHOLDERS.instruction}
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
                    controller.setWorkspaceMode(mode);
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
            className="grid gap-4 px-4 py-4 sm:px-5 sm:py-5 xl:grid-cols-[13rem_minmax(0,1fr)]"
        >
            <h2 className="font-mono text-label font-medium text-muted lg:pt-2" id={headingId}>
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
                <RootModeButtons
                    label={`${label} root mode`}
                    onChange={onModeChange}
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
                            placeholder={rootHostPathPlaceholder(mode)}
                            value={hostPath}
                        />
                    </FormField>
                </div>
            ) : null}
        </section>
    );
}

function RootModeButtons({
    label,
    onChange,
    value,
}: {
    readonly label: string;
    readonly onChange: (value: TaskRootMode) => void;
    readonly value: TaskRootMode;
}) {
    return (
        <div aria-label={label} className="inline-flex min-w-0 flex-wrap gap-2" role="group">
            {TASK_ROOT_MODE_OPTIONS.map((option) => {
                const isSelected = option.value === value;

                return (
                    <button
                        aria-pressed={isSelected}
                        className={classNames(
                            "inline-flex h-control items-center justify-center gap-2 rounded-control border px-4 text-utility font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-55",
                            isSelected
                                ? "border-primary/25 bg-primary-soft text-primary-foreground"
                                : "border-outline bg-surface-low text-foreground hover:border-primary/45 hover:text-primary-foreground",
                        )}
                        key={option.value}
                        onClick={() => {
                            onChange(option.value);
                        }}
                        type="button"
                    >
                        {isSelected ? (
                            <span
                                aria-hidden="true"
                                className="size-1.5 shrink-0 rounded-full bg-primary"
                            />
                        ) : null}
                        <span className="min-w-0 truncate">{option.label}</span>
                    </button>
                );
            })}
        </div>
    );
}

function rootHostPathPlaceholder(mode: TaskRootMode): string {
    return mode === "ensure_host_path" ? "/workspaces/new-task" : "/workspaces/existing-root";
}

export function TaskStartActions({ controller }: { readonly controller: TaskStartController }) {
    const requiredInputCount = countTaskStartRequiredInputs(
        controller.form,
        controller.selectedWorkflowKey,
    );
    const requiredInputLabel = String(requiredInputCount);
    const isStartDisabled = controller.submitState.isSubmitting || requiredInputCount > 0;

    return (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-compact text-muted">
                {requiredInputCount > 0
                    ? `${requiredInputLabel} required input${
                          requiredInputCount === 1 ? "" : "s"
                      } still need attention.`
                    : "Ready to start from the selected workflow."}
            </p>
            <div className="flex flex-wrap gap-2">
                <Button onClick={controller.showPreview}>Preview</Button>
                <Button
                    className="disabled:border-outline disabled:bg-outline disabled:text-white disabled:opacity-100"
                    disabled={isStartDisabled}
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
                        className="disabled:border-outline disabled:bg-outline disabled:text-white disabled:opacity-100"
                        disabled={startDisabled}
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
        />
    );
}

function TaskStartResult({ onClose }: { readonly onClose: () => void }) {
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
            <StatePanel
                summary="Initial runtime effects were accepted and the task is ready for the Tasks surface."
                title="Task start accepted"
                tone="success"
            />
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
