import { Eye, Rocket, X } from "lucide-react";

import {
    Button,
    FormField,
    IdRefText,
    PropertyGrid,
    SegmentedControl,
    StatePanel,
    StatusChip,
    Surface,
} from "../../components/ui";
import type { TaskStartController } from "./task-start-controller";
import { isAuthError } from "./task-start-data";
import {
    TASK_ROOT_MODE_OPTIONS,
    rootModeSummary,
    shouldShowHostPath,
    type TaskRootMode,
    type TaskStartPreview,
    type TaskStartResultView,
} from "./task-start-model";
import { controlClassName, textAreaClassName } from "./task-start-ui";

export function TaskIdentitySection({ controller }: { readonly controller: TaskStartController }) {
    return (
        <Surface label="Task" title="Task identity">
            <div className="grid gap-4 lg:grid-cols-2">
                <FormField
                    error={controller.formErrors.taskKey}
                    id="task-start-key"
                    label="Task key"
                >
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
        </Surface>
    );
}

export function RootsSection({ controller }: { readonly controller: TaskStartController }) {
    return (
        <Surface label="Roots" title="Workspace and context roots">
            <div className="grid gap-4 lg:grid-cols-2">
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
        </Surface>
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
        <section
            aria-label={`${label} root`}
            className="rounded-card border border-outline-soft bg-surface-low p-4 shadow-hairline"
        >
            <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                <div className="min-w-0">
                    <h2 className="font-display text-compact font-semibold text-foreground">
                        {label}
                    </h2>
                    <p className="mt-1 text-compact text-muted">{rootModeSummary(mode)}</p>
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
        <Surface variant="muted">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-compact text-muted">
                    {controller.selectedWorkflowKey === null
                        ? "Select a stored workflow before starting a task."
                        : "Ready to start from the selected stored workflow."}
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
        </Surface>
    );
}

export function PreviewPanel({
    onClose,
    preview,
}: {
    readonly onClose: () => void;
    readonly preview: TaskStartPreview;
}) {
    return (
        <Surface
            aria-label="Preview"
            actions={
                <Button icon={<X />} onClick={onClose} variant="ghost">
                    Close
                </Button>
            }
            label="Preview"
            title="Preview"
        >
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                <div className="rounded-card border border-outline-soft bg-surface-low p-4">
                    <p className="font-mono text-label font-medium uppercase text-muted">
                        Workflow
                    </p>
                    <h2 className="mt-2 break-words font-display text-compact font-semibold text-foreground">
                        {preview.workflowKey}
                    </h2>
                    <p className="mt-2 break-words text-compact text-muted">
                        {preview.workflowDescription}
                    </p>
                    <div className="mt-3">
                        <StatusChip tone="success">{preview.workflowRevisionLabel}</StatusChip>
                    </div>
                </div>
                <PropertyGrid
                    items={[
                        { label: "Task key", value: <IdRefText value={preview.taskKey} /> },
                        { label: "Title", value: preview.title },
                        { label: "Summary", value: preview.summary },
                        { label: "Instruction", value: preview.instructionSummary },
                        { label: "Workspace", value: preview.workspaceModeLabel },
                        { label: "Context", value: preview.contextModeLabel },
                    ]}
                />
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <StatePanel
                    summary={preview.workspaceSummary}
                    title="Workspace root"
                    tone="empty"
                />
                <StatePanel summary={preview.contextSummary} title="Context root" tone="empty" />
            </div>
        </Surface>
    );
}

export function ResultPanel({ controller }: { readonly controller: TaskStartController }) {
    if (controller.submitState.error !== null) {
        const error = controller.submitState.error;
        return (
            <StatePanel
                action={<Button onClick={controller.start}>Retry Start Task</Button>}
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
        );
    }

    if (controller.submitState.result === null) {
        return null;
    }

    return <TaskStartResult result={controller.submitState.result} />;
}

function TaskStartResult({ result }: { readonly result: TaskStartResultView }) {
    return (
        <Surface label="Result" title="Result">
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
        </Surface>
    );
}
