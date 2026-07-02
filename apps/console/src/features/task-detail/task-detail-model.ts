import type { components } from "../../api/generated/openapi";
import { mapCommandRunRow, mapHumanRequestQueueItem } from "../../api/view-models";
import type { TaskDetailBootstrap } from "./task-detail-data";
import { taskEventTone } from "./task-detail-tones";
import type {
    DetailRow,
    TaskActionMode,
    TaskDetailRef,
    TaskDetailView,
    TaskEventRow,
    TaskGraphEdge,
    TaskGraphNode,
    TaskSelectedContext,
} from "./task-detail-types";

export {
    commandRunTone,
    flowStatusTone,
    humanRequestTone,
    taskEventTone,
} from "./task-detail-tones";
export { TASK_DETAIL_TABS, TASK_EVENT_TYPES } from "./task-detail-types";
export type {
    CommandRunPreview,
    DetailRow,
    HumanRequestPreview,
    TaskActionMode,
    TaskDetailRef,
    TaskDetailTab,
    TaskDetailTabOption,
    TaskDetailView,
    TaskEventRow,
    TaskGraphEdge,
    TaskGraphNode,
    TaskHeaderView,
    TaskSelectedContext,
    TaskSnapshotSummary,
    TaskTraceSummary,
} from "./task-detail-types";

type BoundaryHistoryEntry = components["schemas"]["BoundaryHistoryEntry"];
type TaskGraphDependencyEntry = components["schemas"]["TaskGraphDependencyEntry"];
type TaskGraphNodeEntry = components["schemas"]["TaskGraphNodeEntry"];

export function buildTaskDetailView({
    bootstrap,
    events,
}: {
    readonly bootstrap: TaskDetailBootstrap;
    readonly events: readonly components["schemas"]["TaskEventRecord"][];
}): TaskDetailView {
    const eventRows = events.filter(isVisibleTaskEventRecord).map(mapTaskEventRow);
    const graphNodes = buildGraphNodes(bootstrap, eventRows);
    const graphEdges = buildGraphEdges(bootstrap, eventRows, graphNodes);

    return {
        actionMode: buildActionMode(bootstrap.task.status),
        artifactRefs: collectArtifactRefs(bootstrap, eventRows),
        commandRuns: bootstrap.commandRuns.items.map((run) => {
            const row = mapCommandRunRow(run);
            return {
                description: row.description,
                hasLog: row.hasLog,
                runId: row.runId,
                state: row.state,
                summary: row.summary,
            };
        }),
        eventRows,
        graphEdges,
        graphNodes,
        humanRequests: bootstrap.humanRequests.items.map((item) => {
            const row = mapHumanRequestQueueItem(item);
            return {
                kind: row.kind,
                requestId: row.requestId,
                status: row.status,
                summary: row.summary,
                title: row.title,
            };
        }),
        snapshot: {
            streamHeadEventId: bootstrap.snapshot.stream_head_event_id ?? null,
            topActionableItems: bootstrap.snapshot.top_actionable_items,
        },
        task: {
            activeAttemptId: bootstrap.task.active_attempt_id ?? null,
            activeFlowRevisionId: bootstrap.task.active_flow_revision_id,
            currentNodeKey: bootstrap.task.current_node_key ?? null,
            status: bootstrap.task.status,
            summary: bootstrap.task.task_summary,
            taskId: bootstrap.task.task_id,
            title: bootstrap.task.task_title,
            updatedAt: bootstrap.task.updated_at,
            workflowKey: bootstrap.task.workflow_key ?? null,
            workflowManifestRef: bootstrap.task.workflow_manifest_ref,
        },
        trace: {
            boundaries: bootstrap.trace.boundary_history,
            checkpoints: bootstrap.trace.checkpoint_history,
            dependencyEdges: readTraceDependencyEdges(bootstrap.trace),
            dispatches: bootstrap.trace.dispatch_history,
            graphNodes: readTraceGraphNodes(bootstrap.trace),
        },
    };
}

export function getDefaultNodeKey(view: TaskDetailView): string | null {
    if (view.task.currentNodeKey !== null) {
        return view.task.currentNodeKey;
    }

    return view.graphNodes[0]?.nodeKey ?? null;
}

export function getDefaultEventId(view: TaskDetailView, nodeKey: string | null): string | null {
    const dispatchEvent = view.eventRows.find(
        (event) =>
            event.eventType === "dispatch_opened" &&
            (nodeKey === null || event.nodeKey === nodeKey),
    );
    if (dispatchEvent !== undefined) {
        return dispatchEvent.eventId;
    }

    const matchingEvent = view.eventRows.find(
        (event) => nodeKey === null || event.nodeKey === nodeKey,
    );

    return matchingEvent?.eventId ?? view.eventRows.at(-1)?.eventId ?? null;
}

export function buildSelectedContext({
    eventId,
    nodeKey,
    view,
}: {
    readonly eventId: string | null;
    readonly nodeKey: string | null;
    readonly view: TaskDetailView;
}): TaskSelectedContext {
    const node = view.graphNodes.find((candidate) => candidate.nodeKey === nodeKey) ?? null;
    const event = view.eventRows.find((candidate) => candidate.eventId === eventId) ?? null;
    const payload = event?.record.payload;
    const selectedArtifactRefs =
        event === null ? view.artifactRefs : collectRefsFromPayload(payload, "event payload");

    return {
        assignmentRows: buildAssignmentRows(view, node, event),
        artifactRefs: selectedArtifactRefs.length === 0 ? view.artifactRefs : selectedArtifactRefs,
        boundaryRows: buildBoundaryRows(view, node, event),
        checkpointRows: buildCheckpointRows(view, event),
        event,
        node,
        overviewRows: buildOverviewRows(view, node, event),
        traceJson: event === null ? "{}" : JSON.stringify(event.record, null, 2),
    };
}

function isVisibleTaskEventRecord(event: components["schemas"]["TaskEventRecord"]): boolean {
    const eventType: string = event.event_type;
    return (
        eventType !== "provider_event_normalized" && eventType !== "provider_resolution_recorded"
    );
}

function mapTaskEventRow(event: components["schemas"]["TaskEventRecord"]): TaskEventRow {
    return {
        actorRef: event.actor_ref ?? null,
        attemptId: event.attempt_id ?? null,
        eventId: event.event_id,
        eventSeq: event.event_seq,
        eventSource: event.event_source,
        eventType: event.event_type,
        flowRevisionId: event.flow_revision_id ?? null,
        nodeKey: event.node_key ?? null,
        occurredAt: event.occurred_at,
        payloadSummary: summarizePayload(event.event_type, event.payload),
        record: event,
        tone: taskEventTone(event.event_type),
    };
}

function buildGraphNodes(
    bootstrap: TaskDetailBootstrap,
    eventRows: readonly TaskEventRow[],
): readonly TaskGraphNode[] {
    const nodeKeys = new Set<string>();
    const currentNodeKey = bootstrap.task.current_node_key ?? null;
    const graphNodeEntries = readTraceGraphNodes(bootstrap.trace);
    const traceGraphNodeByKey = new Map(
        graphNodeEntries.map((graphNode) => [graphNode.node_key, graphNode]),
    );

    if (graphNodeEntries.length > 0) {
        for (const graphNode of graphNodeEntries) {
            nodeKeys.add(graphNode.node_key);
        }
    } else {
        for (const dispatch of bootstrap.trace.dispatch_history) {
            nodeKeys.add(dispatch.node_key);
        }
        for (const event of eventRows) {
            if (event.nodeKey !== null) {
                nodeKeys.add(event.nodeKey);
            }
            collectPayloadNodeKeys(event.eventType, event.record.payload).forEach((nodeKey) =>
                nodeKeys.add(nodeKey),
            );
        }
    }
    if (currentNodeKey !== null) {
        nodeKeys.add(currentNodeKey);
    }
    if (nodeKeys.size === 0) {
        nodeKeys.add("task");
    }

    return [...nodeKeys].map((nodeKey, index) => {
        const dispatch = [...bootstrap.trace.dispatch_history]
            .reverse()
            .find((candidate) => candidate.node_key === nodeKey);
        const checkpoint = [...bootstrap.trace.checkpoint_history]
            .reverse()
            .find((candidate) => candidate.attempt_id === dispatch?.attempt_id);
        const eventsForNode = eventRows.filter((event) => event.nodeKey === nodeKey);
        const graphNode = traceGraphNodeByKey.get(nodeKey);
        const isCurrent = nodeKey === currentNodeKey;

        return {
            attemptId: dispatch?.attempt_id ?? eventsForNode.at(-1)?.attemptId ?? null,
            checkpointSummary: checkpoint?.summary ?? null,
            eventCount: eventsForNode.length,
            isActive:
                isCurrent ||
                dispatch?.delivery_status === "accepted" ||
                dispatch?.delivery_status === "provider_signal_seen",
            isCurrent,
            nodeKey,
            order: graphNode?.order_index ?? index + graphNodeEntries.length,
            status: resolveNodeStatus(isCurrent, dispatch, checkpoint),
            summary:
                checkpoint?.summary ??
                dispatch?.assignment_summary ??
                graphNode?.description ??
                dispatch?.delivery_status ??
                eventsForNode.at(-1)?.payloadSummary ??
                "Controller-backed task context.",
        };
    });
}

function buildGraphEdges(
    bootstrap: TaskDetailBootstrap,
    eventRows: readonly TaskEventRow[],
    nodes: readonly TaskGraphNode[],
): readonly TaskGraphEdge[] {
    const nodeKeys = new Set(nodes.map((node) => node.nodeKey));
    const edgeKeys = new Set<string>();
    const edges: TaskGraphEdge[] = [];
    const graphNodeEntries = readTraceGraphNodes(bootstrap.trace);

    const addEdge = (
        fromNodeKey: string | null,
        toNodeKey: string | null,
        kind: TaskGraphEdge["kind"],
    ) => {
        if (fromNodeKey === null || toNodeKey === null || fromNodeKey === toNodeKey) {
            return;
        }
        if (!nodeKeys.has(fromNodeKey) || !nodeKeys.has(toNodeKey)) {
            return;
        }
        const edgeKey = `${fromNodeKey}\u0000${toNodeKey}\u0000${kind}`;
        if (edgeKeys.has(edgeKey)) {
            return;
        }
        edgeKeys.add(edgeKey);
        edges.push({ fromNodeKey, kind, toNodeKey });
    };

    if (graphNodeEntries.length > 0) {
        for (const graphNode of graphNodeEntries) {
            addEdge(graphNode.parent_node_key ?? null, graphNode.node_key, "structural");
        }
        return edges;
    }

    for (const event of eventRows) {
        const payload = event.record.payload;
        if (
            event.eventType === "child_assignment_committed" ||
            event.eventType === "child_assignment_staged"
        ) {
            addEdge(
                readString(payload, "parent_node_key"),
                readString(payload, "target_node_key"),
                "staged",
            );
        }
    }

    for (const node of nodes) {
        addEdge(
            inferParentNodeKey(node.nodeKey, nodeKeys),
            node.nodeKey,
            inferredEdgeKind(node.nodeKey),
        );
    }

    return edges;
}

function readTraceGraphNodes(
    trace: components["schemas"]["OperatorFlowTraceResponse"],
): readonly TaskGraphNodeEntry[] {
    return Array.isArray(trace.graph_nodes) ? trace.graph_nodes : [];
}

function readTraceDependencyEdges(
    trace: components["schemas"]["OperatorFlowTraceResponse"],
): readonly TaskGraphDependencyEntry[] {
    return Array.isArray(trace.dependency_edges) ? trace.dependency_edges : [];
}

function inferParentNodeKey(nodeKey: string, nodeKeys: ReadonlySet<string>): string | null {
    if (nodeKey === "source_contract" && nodeKeys.has("root")) {
        return "root";
    }
    if (nodeKey === "task_control_suite" && nodeKeys.has("root")) {
        return "root";
    }
    if (
        (nodeKey === "tasks_page" ||
            nodeKey === "task_detail_page" ||
            nodeKey === "human_request_page" ||
            nodeKey === "command_runs_page") &&
        nodeKeys.has("task_control_suite")
    ) {
        return "task_control_suite";
    }
    if (
        (nodeKey === "task_detail_source_contract" ||
            nodeKey === "task_detail_build" ||
            nodeKey === "task_detail_review") &&
        nodeKeys.has("task_detail_page")
    ) {
        return "task_detail_page";
    }
    return null;
}

function inferredEdgeKind(nodeKey: string): TaskGraphEdge["kind"] {
    return nodeKey === "task_detail_review" ? "staged" : "structural";
}

function collectArtifactRefs(
    bootstrap: TaskDetailBootstrap,
    eventRows: readonly TaskEventRow[],
): readonly TaskDetailRef[] {
    const refs = [
        refFromWorkflowManifest(bootstrap.task.workflow_manifest_ref),
        ...bootstrap.snapshot.current_paths.map(refFromSupportSurface),
        ...bootstrap.trace.current_paths.map(refFromSupportSurface),
        ...eventRows.flatMap((event) =>
            collectRefsFromPayload(event.record.payload, event.eventType),
        ),
    ];
    return dedupeRefs(refs);
}

function collectRefsFromPayload(payload: unknown, fallbackLabel: string): readonly TaskDetailRef[] {
    if (!isRecord(payload)) {
        return [];
    }

    const refs: TaskDetailRef[] = [];
    const checkpointRef = readRecord(payload, "checkpoint_ref");
    const latestCheckpointRef = readRecord(payload, "latest_checkpoint_ref");
    const workflowManifestRef = readRecord(payload, "workflow_manifest_ref");

    if (checkpointRef !== null) {
        refs.push(refFromUnknownRecord(checkpointRef, "checkpoint_ref", fallbackLabel));
    }
    if (latestCheckpointRef !== null) {
        refs.push(
            refFromUnknownRecord(latestCheckpointRef, "latest_checkpoint_ref", fallbackLabel),
        );
    }
    if (workflowManifestRef !== null) {
        refs.push(
            refFromUnknownRecord(workflowManifestRef, "workflow_manifest_ref", fallbackLabel),
        );
    }

    refs.push(
        ...readRecordArray(payload, "produced_artifacts").map((ref, index) =>
            refFromUnknownRecord(ref, `artifact ${String(index + 1)}`, fallbackLabel),
        ),
    );
    refs.push(
        ...readRecordArray(payload, "transient_refs").map((ref, index) =>
            refFromUnknownRecord(ref, `transient ref ${String(index + 1)}`, fallbackLabel),
        ),
    );
    return refs;
}

function buildOverviewRows(
    view: TaskDetailView,
    node: TaskGraphNode | null,
    event: TaskEventRow | null,
): readonly DetailRow[] {
    return compactRows([
        { label: "Task", value: view.task.title },
        { label: "Status", value: view.task.status },
        { label: "Workflow", value: view.task.workflowKey ?? "not exposed" },
        { label: "Current node", value: view.task.currentNodeKey ?? "not exposed" },
        { label: "Selected node", value: node?.nodeKey ?? "none selected" },
        { label: "Selected event", value: event?.eventType ?? "none selected" },
        { label: "Stream head", value: view.snapshot.streamHeadEventId ?? "live-only" },
    ]);
}

function buildCheckpointRows(
    view: TaskDetailView,
    event: TaskEventRow | null,
): readonly DetailRow[] {
    const payload = event?.record.payload;
    const checkpointId = readString(payload, "checkpoint_id");
    const checkpointKind = readString(payload, "checkpoint_kind");
    const outcome = readString(payload, "outcome");
    const summary = readString(payload, "summary");
    const nextStep = readString(payload, "next_step");
    const latestCheckpoint = view.trace.checkpoints.at(-1);

    return compactRows([
        {
            label: "Checkpoint id",
            value: checkpointId ?? latestCheckpoint?.checkpoint_id ?? "not exposed",
        },
        {
            label: "Kind",
            value: checkpointKind ?? latestCheckpoint?.checkpoint_kind ?? "not exposed",
        },
        { label: "Outcome", value: outcome ?? latestCheckpoint?.outcome ?? "none" },
        { label: "Summary", value: summary ?? latestCheckpoint?.summary ?? "not exposed" },
        { label: "Next step", value: nextStep ?? "not exposed" },
    ]);
}

function buildAssignmentRows(
    view: TaskDetailView,
    node: TaskGraphNode | null,
    event: TaskEventRow | null,
): readonly DetailRow[] {
    const payload = event?.record.payload;
    const selectedNodeKey = node?.nodeKey ?? event?.nodeKey ?? null;
    const dispatch = [...view.trace.dispatches]
        .reverse()
        .find((candidate) => candidate.node_key === selectedNodeKey);

    return compactRows([
        { label: "Node", value: node?.nodeKey ?? event?.nodeKey ?? "not exposed" },
        {
            label: "Assignment key",
            value:
                readString(payload, "assignment_key") ?? dispatch?.assignment_key ?? "not exposed",
        },
        { label: "Attempt", value: dispatch?.attempt_id ?? event?.attemptId ?? "not exposed" },
        { label: "Delivery status", value: dispatch?.delivery_status ?? "not exposed" },
        {
            label: "Assignment summary",
            value:
                readString(payload, "assignment_summary") ??
                dispatch?.assignment_summary ??
                "not exposed",
        },
    ]);
}

function buildBoundaryRows(
    view: TaskDetailView,
    node: TaskGraphNode | null,
    event: TaskEventRow | null,
): readonly DetailRow[] {
    const payload = event?.record.payload;
    const boundary = findBoundaryEntry(view.trace.boundaries, node, event);

    return compactRows([
        {
            label: "Boundary",
            value: readString(payload, "boundary") ?? boundary?.boundary ?? "not exposed",
        },
        {
            label: "Previous node",
            value:
                readString(payload, "previous_node_key") ??
                boundary?.previous_node_key ??
                boundary?.node_key ??
                "not exposed",
        },
        {
            label: "Next node",
            value: readString(payload, "next_node_key") ?? boundary?.next_node_key ?? "not exposed",
        },
        {
            label: "Resulting status",
            value:
                readString(payload, "resulting_flow_status") ??
                boundary?.resulting_flow_status ??
                "not exposed",
        },
        { label: "Occurred", value: boundary?.occurred_at ?? event?.occurredAt ?? "not exposed" },
    ]);
}

function findBoundaryEntry(
    boundaries: readonly BoundaryHistoryEntry[],
    node: TaskGraphNode | null,
    event: TaskEventRow | null,
): BoundaryHistoryEntry | undefined {
    const payload = event?.record.payload;
    const payloadBoundary = readString(payload, "boundary");
    const payloadPrevious = readString(payload, "previous_node_key");
    const payloadNext = readString(payload, "next_node_key");

    if (payloadBoundary !== null || payloadPrevious !== null || payloadNext !== null) {
        const payloadMatch = [...boundaries].reverse().find((boundary) => {
            return (
                (payloadBoundary === null || boundary.boundary === payloadBoundary) &&
                (payloadPrevious === null || boundary.previous_node_key === payloadPrevious) &&
                (payloadNext === null || boundary.next_node_key === payloadNext)
            );
        });
        if (payloadMatch !== undefined) {
            return payloadMatch;
        }
    }

    if (node !== null) {
        const nodeMatch = [...boundaries].reverse().find((boundary) => {
            return (
                boundary.node_key === node.nodeKey ||
                boundary.previous_node_key === node.nodeKey ||
                boundary.next_node_key === node.nodeKey
            );
        });
        if (nodeMatch !== undefined) {
            return nodeMatch;
        }
    }

    return boundaries.at(-1);
}

function buildActionMode(status: components["schemas"]["FlowStatus"]): TaskActionMode {
    if (status === "succeeded" || status === "cancelled") {
        return {
            canCancel: false,
            canContinue: false,
            canPause: false,
            note: "Terminal tasks do not expose task-level controls.",
        };
    }

    if (status === "paused") {
        return {
            canCancel: true,
            canContinue: true,
            canPause: false,
            note: "Continue is pause-resume only and uses current task revision truth.",
        };
    }

    return {
        canCancel: true,
        canContinue: false,
        canPause: true,
        note: "Pause and cancel use current task revision truth.",
    };
}

function resolveNodeStatus(
    isCurrent: boolean,
    dispatch: components["schemas"]["DispatchHistoryEntry"] | undefined,
    checkpoint: components["schemas"]["CheckpointHistoryEntry"] | undefined,
): TaskGraphNode["status"] {
    if (isCurrent) {
        return "active";
    }
    if (checkpoint?.outcome === "green" || checkpoint?.checkpoint_kind === "terminal") {
        return "done";
    }
    if (dispatch?.delivery_status === "prepared") {
        return "staged";
    }
    return "quiet";
}

function summarizePayload(
    eventType: components["schemas"]["TaskEventType"],
    payload: unknown,
): string {
    if (!isRecord(payload)) {
        return eventType;
    }

    return (
        readString(payload, "summary") ??
        readString(payload, "task_title") ??
        readString(payload, "assignment_summary") ??
        readString(payload, "description") ??
        readString(payload, "state") ??
        readString(payload, "status") ??
        readString(payload, "outcome") ??
        eventType
    );
}

function collectPayloadNodeKeys(
    eventType: components["schemas"]["TaskEventType"],
    payload: unknown,
): readonly string[] {
    if (!isRecord(payload)) {
        return [];
    }

    const nodeKeys = [
        readString(payload, "initial_node_key"),
        readString(payload, "node_key"),
        readString(payload, "parent_node_key"),
    ].filter((value): value is string => value !== null);

    if (
        eventType === "child_assignment_committed" ||
        eventType === "child_assignment_staged" ||
        eventType === "structural_revision_adopted"
    ) {
        const targetNodeKey = readString(payload, "target_node_key");
        if (targetNodeKey !== null) {
            nodeKeys.push(targetNodeKey);
        }
    }

    nodeKeys.push(...readStringArray(payload, "affected_node_keys"));
    return nodeKeys;
}

function refFromWorkflowManifest(ref: components["schemas"]["WorkflowManifestRef"]): TaskDetailRef {
    return {
        description: ref.description,
        kind: "manifest",
        label: "workflow_manifest_ref",
        path: ref.path,
        slot: null,
    };
}

function refFromSupportSurface(
    ref: components["schemas"]["OperatorSupportSurfaceRef"],
): TaskDetailRef {
    return {
        description: ref.description,
        kind: ref.kind,
        label: ref.slot ?? ref.kind,
        path: ref.path,
        slot: ref.slot ?? null,
    };
}

function refFromUnknownRecord(
    ref: Record<string, unknown>,
    label: string,
    descriptionFallback: string,
): TaskDetailRef {
    const slot = readString(ref, "slot");
    const kind = readString(ref, "kind") ?? readString(ref, "artifact") ?? label;
    return {
        description: readString(ref, "description") ?? descriptionFallback,
        kind,
        label: slot ?? readString(ref, "label") ?? label,
        path: readString(ref, "path"),
        slot,
    };
}

function dedupeRefs(refs: readonly TaskDetailRef[]): readonly TaskDetailRef[] {
    const byKey = new Map<string, TaskDetailRef>();
    for (const ref of refs) {
        byKey.set(`${ref.kind}\u0000${ref.label}\u0000${ref.path ?? ""}`, ref);
    }
    return [...byKey.values()];
}

function compactRows(rows: readonly DetailRow[]): readonly DetailRow[] {
    return rows.filter((row) => row.value.trim().length > 0);
}

function readString(value: unknown, key: string): string | null {
    if (!isRecord(value)) {
        return null;
    }

    const item = value[key];
    if (typeof item === "string" && item.trim().length > 0) {
        return item;
    }
    if (typeof item === "number" || typeof item === "boolean") {
        return String(item);
    }
    return null;
}

function readRecord(value: unknown, key: string): Record<string, unknown> | null {
    if (!isRecord(value)) {
        return null;
    }

    const item = value[key];
    return isRecord(item) ? item : null;
}

function readRecordArray(value: unknown, key: string): readonly Record<string, unknown>[] {
    if (!isRecord(value) || !Array.isArray(value[key])) {
        return [];
    }

    return value[key].filter((item): item is Record<string, unknown> => isRecord(item));
}

function readStringArray(value: unknown, key: string): readonly string[] {
    if (!isRecord(value) || !Array.isArray(value[key])) {
        return [];
    }

    return value[key].filter((item): item is string => typeof item === "string");
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}
