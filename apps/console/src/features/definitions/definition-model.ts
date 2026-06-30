import type { components } from "../../api/generated/openapi";
import { mapDefinitionSummary, type DefinitionSummary } from "../../api/view-models";

export type DefinitionKind = components["schemas"]["DefinitionKind"];
export type DefinitionListKind = "policies" | "roles" | "workflows";
export type DefinitionListSort = components["schemas"]["DefinitionListSort"];
export type NodeKind = components["schemas"]["NodeKind"];
export type DefinitionSummaryRead = components["schemas"]["DefinitionSummaryRead"];
export type DefinitionRevisionDetailResponse =
    components["schemas"]["DefinitionRevisionDetailResponse"];
export type DefinitionRevisionHistoryEntry =
    components["schemas"]["DefinitionRevisionHistoryEntry"];
export type BudgetSpec = components["schemas"]["BudgetSpec"];
export type WorkflowRootDefinition = components["schemas"]["RootNodeDefinition-Output"];
export type WorkflowNodeDefinition = components["schemas"]["NodeDefinitionInput-Output"];

type RoleContent = components["schemas"]["RoleDefinitionInput"];
type PolicyContent = components["schemas"]["PolicyDefinitionInput-Output"];
type WorkflowContent = components["schemas"]["WorkflowDefinitionInput-Output"];

export interface DefinitionKindOption {
    readonly label: string;
    readonly listKind: DefinitionListKind;
    readonly singularKind: DefinitionKind;
}

export interface DefinitionRow extends DefinitionSummary {
    readonly compatibilityLabels: readonly string[];
    readonly kind: DefinitionKind;
}

export interface DefinitionVersionRow {
    readonly recordedBy: string | null;
    readonly revisionNo: number;
    readonly updatedAt: string;
}

export interface WorkflowNodeSummary {
    readonly childCount: number;
    readonly description: string;
    readonly depth: number;
    readonly id: string;
    readonly policy: string | null;
    readonly role: string;
    readonly title: string | null;
}

export interface DefinitionDetailBase {
    readonly description: string;
    readonly key: string;
    readonly kind: DefinitionKind;
    readonly recordedBy: string | null;
    readonly revisionNo: number;
    readonly updatedAt: string;
}

export interface RoleDefinitionDetail extends DefinitionDetailBase {
    readonly allowedNodeKinds: readonly NodeKind[];
    readonly instruction: string | null;
    readonly kind: "role";
}

export interface PolicyDefinitionDetail extends DefinitionDetailBase {
    readonly appliesTo: readonly NodeKind[];
    readonly budgetSpec: BudgetSpec | null;
    readonly instruction: string | null;
    readonly kind: "policy";
}

export interface WorkflowDefinitionDetail extends DefinitionDetailBase {
    readonly kind: "workflow";
    readonly nodeCount: number;
    readonly root: WorkflowNodeSummary;
    readonly visibleNodes: readonly WorkflowNodeSummary[];
}

export type DefinitionDetailView =
    PolicyDefinitionDetail | RoleDefinitionDetail | WorkflowDefinitionDetail;

export const DEFINITION_KIND_OPTIONS: readonly DefinitionKindOption[] = [
    { label: "Roles", listKind: "roles", singularKind: "role" },
    { label: "Policies", listKind: "policies", singularKind: "policy" },
    { label: "Workflows", listKind: "workflows", singularKind: "workflow" },
];

export const DEFINITION_SORT_OPTIONS: readonly {
    readonly label: string;
    readonly value: DefinitionListSort;
}[] = [
    { label: "Updated newest", value: "updated_at_desc" },
    { label: "Updated oldest", value: "updated_at_asc" },
    { label: "Key A-Z", value: "key_asc" },
    { label: "Key Z-A", value: "key_desc" },
];

export const NODE_KIND_FILTERS: readonly { readonly label: string; readonly value: NodeKind }[] = [
    { label: "Root", value: "root" },
    { label: "Parent", value: "parent" },
    { label: "Worker", value: "worker" },
];

export function singularKindForListKind(kind: DefinitionListKind): DefinitionKind {
    switch (kind) {
        case "policies":
            return "policy";
        case "roles":
            return "role";
        case "workflows":
            return "workflow";
    }
}

export function listLabelForKind(kind: DefinitionListKind): string {
    switch (kind) {
        case "policies":
            return "policies";
        case "roles":
            return "roles";
        case "workflows":
            return "workflows";
    }
}

export function kindLabel(kind: DefinitionKind): string {
    switch (kind) {
        case "policy":
            return "Policy";
        case "role":
            return "Role";
        case "workflow":
            return "Workflow";
    }
}

export function formatNodeKind(kind: NodeKind): string {
    switch (kind) {
        case "parent":
            return "Parent";
        case "root":
            return "Root";
        case "worker":
            return "Worker";
    }
}

export function mapDefinitionRow(
    definition: DefinitionSummaryRead,
    kind: DefinitionKind,
): DefinitionRow {
    const summary = mapDefinitionSummary(definition);
    return {
        ...summary,
        compatibilityLabels: compatibilityLabelsForSummary(summary, kind),
        kind,
    };
}

export function mapDefinitionDetail(
    kind: DefinitionKind,
    detail: DefinitionRevisionDetailResponse,
): DefinitionDetailView {
    if (kind === "policy") {
        const content = detail.content as PolicyContent;
        return {
            appliesTo: content.applies_to,
            budgetSpec: content.budget_spec ?? null,
            description: content.description,
            instruction: content.instruction ?? null,
            key: detail.key,
            kind,
            recordedBy: detail.recorded_by ?? null,
            revisionNo: detail.revision_no,
            updatedAt: detail.updated_at,
        };
    }

    if (kind === "workflow") {
        const content = detail.content as WorkflowContent;
        const visibleNodes = summarizeWorkflowNodes(content.root);
        return {
            description: content.description,
            key: detail.key,
            kind,
            nodeCount: countWorkflowNodes(content.root),
            recordedBy: detail.recorded_by ?? null,
            revisionNo: detail.revision_no,
            root: visibleNodes[0] ?? summarizeWorkflowNode(content.root, 0),
            updatedAt: detail.updated_at,
            visibleNodes,
        };
    }

    const content = detail.content as RoleContent;
    return {
        allowedNodeKinds: content.allowed_node_kinds,
        description: content.description,
        instruction: content.instruction ?? null,
        key: detail.key,
        kind,
        recordedBy: detail.recorded_by ?? null,
        revisionNo: detail.revision_no,
        updatedAt: detail.updated_at,
    };
}

export function mapDefinitionVersionRow(
    version: DefinitionRevisionHistoryEntry,
): DefinitionVersionRow {
    return {
        recordedBy: version.recorded_by ?? null,
        revisionNo: version.revision_no,
        updatedAt: version.updated_at,
    };
}

export function formatBudgetSpec(budgetSpec: BudgetSpec | null): string {
    if (budgetSpec === null) {
        return "Not configured";
    }

    const childAssignmentLimit =
        budgetSpec.child_assignment_limit === null ||
        budgetSpec.child_assignment_limit === undefined
            ? "child assignment limit not reported"
            : `${String(budgetSpec.child_assignment_limit)} child assignments`;
    const retryLimit =
        budgetSpec.retry_limit === null || budgetSpec.retry_limit === undefined
            ? "retry limit not reported"
            : `${String(budgetSpec.retry_limit)} retries`;

    return `${childAssignmentLimit}; ${retryLimit}`;
}

export function formatOptionalInstruction(instruction: string | null): string {
    if (instruction === null || instruction.trim().length === 0) {
        return "No instruction reported by the current definition.";
    }

    return instruction;
}

function compatibilityLabelsForSummary(
    summary: DefinitionSummary,
    kind: DefinitionKind,
): readonly string[] {
    if (kind === "role") {
        return summary.allowedNodeKinds.map(formatNodeKind);
    }
    if (kind === "policy") {
        return summary.appliesTo.map(formatNodeKind);
    }
    return [];
}

function summarizeWorkflowNodes(root: WorkflowRootDefinition): readonly WorkflowNodeSummary[] {
    const nodes: WorkflowNodeSummary[] = [];
    visitWorkflowNode(root, 0, nodes);
    return nodes.slice(0, 6);
}

function visitWorkflowNode(
    node: WorkflowRootDefinition | WorkflowNodeDefinition,
    depth: number,
    nodes: WorkflowNodeSummary[],
): void {
    nodes.push(summarizeWorkflowNode(node, depth));
    for (const child of node.children ?? []) {
        visitWorkflowNode(child, depth + 1, nodes);
    }
}

function summarizeWorkflowNode(
    node: WorkflowRootDefinition | WorkflowNodeDefinition,
    depth: number,
): WorkflowNodeSummary {
    return {
        childCount: node.children?.length ?? 0,
        description: node.description,
        depth,
        id: node.id,
        policy: node.policy ?? null,
        role: node.role,
        title: node.title ?? null,
    };
}

function countWorkflowNodes(root: WorkflowRootDefinition): number {
    return 1 + (root.children ?? []).reduce((count, child) => count + countWorkflowChild(child), 0);
}

function countWorkflowChild(node: WorkflowNodeDefinition): number {
    return 1 + (node.children ?? []).reduce((count, child) => count + countWorkflowChild(child), 0);
}
