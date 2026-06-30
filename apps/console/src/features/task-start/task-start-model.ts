import type { components } from "../../api/generated/openapi";
import { mapDefinitionSummary, type DefinitionSummary } from "../../api/view-models";
import type { StatusTone } from "../../components/ui";

export type TaskRootMode = components["schemas"]["TaskRootMode"];
export type TaskStartRequest = components["schemas"]["TaskStartRequest"];
export type TaskStartResponse = components["schemas"]["TaskStartResponse"];
export type DefinitionSummaryRead = components["schemas"]["DefinitionSummaryRead"];
export type DefinitionRevisionDetailResponse =
    components["schemas"]["DefinitionRevisionDetailResponse"];
export type DefinitionRevisionHistoryEntry =
    components["schemas"]["DefinitionRevisionHistoryEntry"];
export type WorkflowDefinitionContent = components["schemas"]["WorkflowDefinitionInput-Output"];
export type WorkflowRootDefinition = components["schemas"]["RootNodeDefinition-Output"];
export type WorkflowNodeDefinition = components["schemas"]["NodeDefinitionInput-Output"];

export interface TaskStartFormState {
    readonly contextHostPath: string;
    readonly contextMode: TaskRootMode;
    readonly instruction: string;
    readonly summary: string;
    readonly taskKey: string;
    readonly title: string;
    readonly workspaceHostPath: string;
    readonly workspaceMode: TaskRootMode;
}

export interface TaskStartFormErrors {
    readonly contextHostPath?: string;
    readonly summary?: string;
    readonly taskKey?: string;
    readonly title?: string;
    readonly workflow?: string;
    readonly workspaceHostPath?: string;
}

export interface TaskStartWorkflowChoice extends DefinitionSummary {
    readonly displayName: string;
    readonly revisionLabel: string;
}

export interface TaskStartWorkflowDetail {
    readonly description: string;
    readonly key: string;
    readonly nodeCount: number;
    readonly recordedBy: string | null;
    readonly revisionNo: number;
    readonly rootPolicy: string | null;
    readonly rootRole: string;
    readonly updatedAt: string;
    readonly workflowId: string;
}

export interface TaskStartVersionRow {
    readonly recordedBy: string | null;
    readonly revisionNo: number;
    readonly updatedAt: string;
}

export interface TaskStartPreview {
    readonly contextModeLabel: string;
    readonly contextSummary: string;
    readonly instructionSummary: string;
    readonly summary: string;
    readonly taskKey: string;
    readonly title: string;
    readonly workflowDescription: string;
    readonly workflowKey: string;
    readonly workflowRevisionLabel: string;
    readonly workspaceModeLabel: string;
    readonly workspaceSummary: string;
}

export interface TaskStartResultView {
    readonly activeFlowRevisionId: string;
    readonly compiledPlanId: string;
    readonly flowStatus: components["schemas"]["FlowStatus"];
    readonly flowStatusLabel: string;
    readonly flowStatusTone: StatusTone;
    readonly manifestDescription: string;
    readonly taskId: string;
}

export const TASK_START_INITIAL_FORM: TaskStartFormState = {
    contextHostPath: "",
    contextMode: "ensure_task_default",
    instruction: "Keep the work scoped to the current assignment and publish focused verification.",
    summary: "Launch one bounded task from stored workflow truth.",
    taskKey: "implement-task-start-launch-form",
    title: "Implement Task Start launch form",
    workspaceHostPath: "",
    workspaceMode: "ensure_task_default",
};

export const TASK_ROOT_MODE_OPTIONS: readonly {
    readonly label: string;
    readonly value: TaskRootMode;
}[] = [
    { label: "Task default", value: "ensure_task_default" },
    { label: "Create host path", value: "ensure_host_path" },
    { label: "Use existing host", value: "use_existing_host" },
];

export function mapTaskStartWorkflowChoice(
    definition: DefinitionSummaryRead,
): TaskStartWorkflowChoice {
    const summary = mapDefinitionSummary(definition);
    return {
        ...summary,
        displayName: summary.title ?? summary.key,
        revisionLabel: `Revision ${String(summary.currentRevisionNo)}`,
    };
}

export function mapTaskStartWorkflowDetail(
    detail: DefinitionRevisionDetailResponse,
): TaskStartWorkflowDetail {
    const content = detail.content as WorkflowDefinitionContent;
    return {
        description: content.description,
        key: detail.key,
        nodeCount: countWorkflowNodes(content.root),
        recordedBy: detail.recorded_by ?? null,
        revisionNo: detail.revision_no,
        rootPolicy: content.root.policy ?? null,
        rootRole: content.root.role,
        updatedAt: detail.updated_at,
        workflowId: content.id,
    };
}

export function mapTaskStartVersionRow(
    version: DefinitionRevisionHistoryEntry,
): TaskStartVersionRow {
    return {
        recordedBy: version.recorded_by ?? null,
        revisionNo: version.revision_no,
        updatedAt: version.updated_at,
    };
}

export function validateTaskStartForm(
    form: TaskStartFormState,
    selectedWorkflowKey: string | null,
): TaskStartFormErrors {
    return {
        workflow: selectedWorkflowKey === null ? "Workflow selection is required." : undefined,
        taskKey: form.taskKey.trim().length === 0 ? "Task key is required." : undefined,
        title: form.title.trim().length === 0 ? "Title is required." : undefined,
        summary: form.summary.trim().length === 0 ? "Summary is required." : undefined,
        workspaceHostPath:
            form.workspaceMode === "ensure_task_default" || form.workspaceHostPath.trim().length > 0
                ? undefined
                : "Workspace host path is required.",
        contextHostPath:
            form.contextMode === "ensure_task_default" || form.contextHostPath.trim().length > 0
                ? undefined
                : "Context host path is required.",
    };
}

export function hasTaskStartFormErrors(errors: TaskStartFormErrors): boolean {
    return Object.values(errors).some((value) => value !== undefined);
}

export function buildTaskStartRequest(
    form: TaskStartFormState,
    workflowKey: string,
): TaskStartRequest {
    const workspace = buildRootBinding(form.workspaceMode, form.workspaceHostPath);
    const context = buildRootBinding(form.contextMode, form.contextHostPath);
    const roots =
        workspace === null && context === null
            ? undefined
            : {
                  ...(workspace === null ? {} : { workspace }),
                  ...(context === null ? {} : { context }),
              };
    const instruction = form.instruction.trim();

    return {
        ...(roots === undefined ? {} : { roots }),
        task: {
            ...(instruction.length === 0 ? {} : { instruction }),
            key: form.taskKey.trim(),
            summary: form.summary.trim(),
            title: form.title.trim(),
        },
        workflow: {
            key: workflowKey,
        },
    };
}

export function buildTaskStartPreview({
    detail,
    form,
    workflow,
}: {
    readonly detail: TaskStartWorkflowDetail | null;
    readonly form: TaskStartFormState;
    readonly workflow: TaskStartWorkflowChoice;
}): TaskStartPreview {
    return {
        contextModeLabel: rootModeLabel(form.contextMode),
        contextSummary: rootModeSummary(form.contextMode),
        instructionSummary:
            form.instruction.trim().length === 0
                ? "No additional instruction provided."
                : form.instruction.trim(),
        summary: form.summary.trim(),
        taskKey: form.taskKey.trim(),
        title: form.title.trim(),
        workflowDescription:
            detail?.description ?? workflow.description ?? "No workflow description reported.",
        workflowKey: workflow.key,
        workflowRevisionLabel: `Revision ${String(detail?.revisionNo ?? workflow.currentRevisionNo)}`,
        workspaceModeLabel: rootModeLabel(form.workspaceMode),
        workspaceSummary: rootModeSummary(form.workspaceMode),
    };
}

export function mapTaskStartResult(response: TaskStartResponse): TaskStartResultView {
    return {
        activeFlowRevisionId: response.active_flow_revision_id,
        compiledPlanId: response.compiled_plan_id,
        flowStatus: response.flow_status,
        flowStatusLabel: flowStatusLabel(response.flow_status),
        flowStatusTone: flowStatusTone(response.flow_status),
        manifestDescription: response.workflow_manifest_ref.description,
        taskId: response.task_id,
    };
}

export function rootModeLabel(mode: TaskRootMode): string {
    switch (mode) {
        case "ensure_task_default":
            return "Task default";
        case "ensure_host_path":
            return "Create host path";
        case "use_existing_host":
            return "Use existing host";
    }
}

export function rootModeSummary(mode: TaskRootMode): string {
    switch (mode) {
        case "ensure_task_default":
            return "Controller will assign the task-owned default root.";
        case "ensure_host_path":
            return "Controller will create or reuse the provided host placement.";
        case "use_existing_host":
            return "Controller will use the provided existing host placement.";
    }
}

export function shouldShowHostPath(mode: TaskRootMode): boolean {
    return mode !== "ensure_task_default";
}

function buildRootBinding(
    mode: TaskRootMode,
    hostPath: string,
): components["schemas"]["TaskRootBindingInput"] | null {
    if (mode === "ensure_task_default") {
        return null;
    }

    return {
        host_path: hostPath.trim(),
        mode,
    };
}

function flowStatusLabel(status: components["schemas"]["FlowStatus"]): string {
    switch (status) {
        case "blocked":
            return "Blocked";
        case "cancelled":
            return "Cancelled";
        case "paused":
            return "Paused";
        case "pending":
            return "Pending";
        case "running":
            return "Running";
        case "succeeded":
            return "Succeeded";
    }
}

function flowStatusTone(status: components["schemas"]["FlowStatus"]): StatusTone {
    switch (status) {
        case "running":
            return "active";
        case "succeeded":
            return "success";
        case "blocked":
        case "paused":
            return "warning";
        case "cancelled":
            return "danger";
        case "pending":
            return "neutral";
    }
}

function countWorkflowNodes(root: WorkflowRootDefinition): number {
    return 1 + (root.children ?? []).reduce((count, child) => count + countWorkflowNode(child), 0);
}

function countWorkflowNode(node: WorkflowNodeDefinition): number {
    return 1 + (node.children ?? []).reduce((count, child) => count + countWorkflowNode(child), 0);
}
