import type { ConsoleMockScenario } from "../../src/mocks/handlers";
import type { components } from "../../src/api/generated/openapi";
import { TASK_EVENT_TYPES } from "../../src/features/task-detail/task-detail-model";
import {
    createCommandRunListItem,
    createConsoleMockScenario,
    createHumanRequestRead,
    createRuntimeFlowRead,
    createTaskEventRecord,
    createTaskEventStreamFixture,
    createWorkflowManifestRef,
} from "./console-api";

export const TASK_DETAIL_TASK_ID = "task-runtime-route-copy";
export const TASK_DETAIL_STREAM_HEAD = "evt-006-structural-revision-adopted";
export const TASK_DETAIL_EVENT_BASE_AT = "2026-06-21T15:03:00Z";
export const TASK_DETAIL_UPDATED_AT = "2026-06-21T15:24:00Z";

const TASK_DETAIL_VISUAL_EVENT_TIMES: Partial<
    Record<components["schemas"]["TaskEventType"], string>
> = {
    boundary_accepted: "2026-06-21T15:10:00Z",
    checkpoint_recorded: "2026-06-21T15:09:00Z",
    child_assignment_committed: "2026-06-21T15:12:00Z",
    child_assignment_staged: "2026-06-21T15:11:00Z",
    dispatch_opened: "2026-06-21T15:08:00Z",
    structural_revision_adopted: "2026-06-21T15:13:00Z",
    task_started: "2026-06-21T15:03:00Z",
};

const TASK_DETAIL_VISUAL_EVENT_TYPES: readonly components["schemas"]["TaskEventType"][] = [
    "task_started",
    "dispatch_opened",
    "checkpoint_recorded",
    "boundary_accepted",
    "child_assignment_staged",
    "structural_revision_adopted",
];

const TASK_DETAIL_EVENT_TYPES = [
    ...TASK_DETAIL_VISUAL_EVENT_TYPES,
    ...TASK_EVENT_TYPES.filter((eventType) => !TASK_DETAIL_VISUAL_EVENT_TYPES.includes(eventType)),
];

export interface TaskDetailScenarioOptions {
    readonly cursorResetCursors?: readonly string[];
    readonly events?: readonly components["schemas"]["TaskEventRecord"][];
    readonly status?: components["schemas"]["FlowStatus"];
    readonly streamEvents?: readonly components["schemas"]["TaskEventRecord"][];
    readonly streamHeadEventId?: string | null;
}

export function createTaskDetailMockScenario(
    options: TaskDetailScenarioOptions = {},
): ConsoleMockScenario {
    const events = options.events ?? createTaskDetailEventRecords();
    const streamHeadEventId =
        options.streamHeadEventId === undefined
            ? TASK_DETAIL_STREAM_HEAD
            : options.streamHeadEventId;
    const streamHeadIndex =
        streamHeadEventId === null
            ? -1
            : events.findIndex((event) => event.event_id === streamHeadEventId);
    const backfillEvents =
        streamHeadIndex === -1
            ? []
            : events.filter((event) => event.event_seq <= streamHeadIndex + 1);
    const streamEvents =
        options.streamEvents ?? (streamHeadIndex === -1 ? events : events.slice(streamHeadIndex));
    const taskRead = createRuntimeFlowRead({
        active_attempt_id: "attempt-task-detail-build",
        active_flow_revision_id: "flow-revision-task-detail-1",
        current_node_key: "task_detail_build",
        status: options.status ?? "running",
        task_id: TASK_DETAIL_TASK_ID,
        task_summary: "Replace retired runtime labels without widening the task hub.",
        task_title: "Refresh runtime route copy",
        updated_at: TASK_DETAIL_UPDATED_AT,
        workflow_key: "frontend-console-continuation-delivery",
        workflow_manifest_ref: createWorkflowManifestRef(),
    });

    return createConsoleMockScenario({
        commandRunList: {
            items: [
                createCommandRunListItem({
                    description: "Verify command-run runner behavior.",
                    run_id: "run-task-detail-check",
                    state: "running",
                    summary: "Focused integration proof is running.",
                }),
            ],
            next_cursor: null,
            task_id: TASK_DETAIL_TASK_ID,
        },
        humanRequestList: {
            items: [
                createHumanRequestRead({
                    kind: "approval",
                    request_id: "hr-task-detail-approval",
                    summary: "Approval is needed for the last copy trim.",
                    title: "Approve the last copy trim",
                }),
            ],
            task_id: TASK_DETAIL_TASK_ID,
        },
        snapshot: {
            current_paths: [
                {
                    description: "Current assignment for Task Detail build.",
                    kind: "assignment",
                    path: "_runtime/attempts/task-detail/assignment.md",
                    slot: null,
                    version: null,
                },
            ],
            flow: taskRead,
            stream_head_event_id: streamHeadEventId,
            top_actionable_items: [
                {
                    current_paths: [],
                    node_key: "task_detail_build",
                    suggested_action: "Implement only Task Detail.",
                    summary: "Task Detail implementation is active.",
                },
            ],
        },
        taskEvents: {
            items: backfillEvents,
            next_cursor: null,
            task_id: TASK_DETAIL_TASK_ID,
            through_event_id: streamHeadEventId,
        },
        taskEventStream: createTaskEventStreamFixture({
            chunksByCursor:
                streamHeadEventId === null
                    ? {}
                    : {
                          [streamHeadEventId]: streamEvents.map(createTaskEventStreamFrame),
                      },
            cursorResetCursors: options.cursorResetCursors ?? [],
            events: streamEvents,
        }),
        taskRead,
        trace: createTaskDetailTrace(),
    });
}

export function createTaskDetailEventRecords(
    options: {
        readonly taskId?: string;
        readonly nodeKeys?: readonly string[];
    } = {},
): readonly components["schemas"]["TaskEventRecord"][] {
    const taskId = options.taskId ?? TASK_DETAIL_TASK_ID;
    const nodeKeys = options.nodeKeys ?? [
        "root",
        "source_contract",
        "task_control_suite",
        "tasks_page",
        "task_detail_page",
        "human_request_page",
        "command_runs_page",
        "task_detail_source_contract",
        "task_detail_build",
        "task_detail_review",
    ];

    return TASK_DETAIL_EVENT_TYPES.map((eventType, index) => {
        const eventSeq = index + 1;
        const eventId = `evt-${String(eventSeq).padStart(3, "0")}-${eventType.replace(/_/g, "-")}`;
        const nodeKey = nodeKeyForEvent(eventType, index, nodeKeys);
        return createTaskEventRecord({
            attempt_id: `attempt-${nodeKey}`,
            dispatch_id: `dispatch-${nodeKey}`,
            event_id: eventId,
            event_seq: eventSeq,
            event_source: eventSourceForType(eventType),
            event_type: eventType,
            flow_revision_id: "flow-revision-task-detail-1",
            node_key: nodeKey,
            occurred_at: occurredAtForEvent(eventType, index),
            payload: payloadForEvent(eventType, nodeKey),
            task_id: taskId,
        });
    });
}

function nodeKeyForEvent(
    eventType: components["schemas"]["TaskEventType"],
    index: number,
    nodeKeys: readonly string[],
): string {
    const nodeByEventType: Partial<Record<components["schemas"]["TaskEventType"], string>> = {
        boundary_accepted: "task_detail_build",
        checkpoint_recorded: "task_detail_source_contract",
        child_assignment_staged: "task_detail_review",
        command_run_cancel_requested: "task_detail_build",
        command_run_cancelled: "task_detail_build",
        command_run_failed: "task_detail_build",
        command_run_progressed: "task_detail_build",
        command_run_started: "task_detail_build",
        command_run_succeeded: "task_detail_build",
        command_run_timed_out: "task_detail_build",
        dispatch_opened: "task_detail_build",
        human_request_cancelled: "task_detail_build",
        human_request_opened: "task_detail_build",
        human_request_resolved: "task_detail_build",
        human_request_timed_out: "task_detail_build",
        structural_revision_adopted: "task_detail_page",
        task_started: "root",
    };
    return (
        nodeByEventType[eventType] ??
        nodeKeys[Math.min(index % nodeKeys.length, nodeKeys.length - 1)]
    );
}

export function createLongTaskDetailEventRecords(): readonly components["schemas"]["TaskEventRecord"][] {
    const nodeKeys = Array.from({ length: 18 }, (_item, index) =>
        index === 0 ? "root" : `worker_node_${String(index).padStart(2, "0")}`,
    );
    const baseEvents = createTaskDetailEventRecords({ nodeKeys });
    const extraEvents = nodeKeys.slice(6).map((nodeKey, index) =>
        createTaskEventRecord({
            attempt_id: `attempt-${nodeKey}`,
            dispatch_id: `dispatch-${nodeKey}`,
            event_id: `evt-extra-${String(index + 1).padStart(2, "0")}`,
            event_seq: baseEvents.length + index + 1,
            event_source: "controller",
            event_type: "dispatch_opened",
            flow_revision_id: "flow-revision-task-detail-1",
            node_key: nodeKey,
            occurred_at: new Date(
                Date.parse(TASK_DETAIL_EVENT_BASE_AT) + (baseEvents.length + index) * 60_000,
            ).toISOString(),
            payload: {
                assignment_key: `assignment-${nodeKey}`,
                control_state: "live",
                delivery_status: "accepted",
                node_key: nodeKey,
                previous_node_key: nodeKeys[index] ?? "root",
                summary: `Opened ${nodeKey}.`,
            },
            task_id: TASK_DETAIL_TASK_ID,
        }),
    );
    return [...baseEvents, ...extraEvents];
}

function createTaskDetailTrace(): components["schemas"]["OperatorFlowTraceResponse"] {
    return {
        boundary_history: [
            {
                boundary: "green",
                next_attempt_id: "attempt-task_detail_page",
                next_node_key: "task_detail_page",
                node_key: "task_detail_source_contract",
                occurred_at: "2026-06-29T13:45:00Z",
                previous_node_key: "task_detail_source_contract",
                requires_reopen_after_inactivity: true,
                resulting_flow_status: "running",
            },
            {
                boundary: "yield",
                next_attempt_id: "attempt-task_detail_build",
                next_node_key: "task_detail_build",
                node_key: "task_detail",
                occurred_at: "2026-06-29T13:55:00Z",
                previous_node_key: "task_detail",
                requires_reopen_after_inactivity: true,
                resulting_flow_status: "running",
            },
        ],
        checkpoint_history: [
            {
                attempt_id: "attempt-task_detail_source_contract",
                checkpoint_id: "checkpoint-contract",
                checkpoint_kind: "terminal",
                outcome: "green",
                recorded_at: "2026-06-29T13:45:00Z",
                summary: "Runtime page contract is ready.",
            },
            {
                attempt_id: "attempt-task_detail_build",
                checkpoint_id: "checkpoint-build-progress",
                checkpoint_kind: "progress",
                outcome: null,
                recorded_at: "2026-06-29T14:00:00Z",
                summary: "Task Detail build is in progress.",
            },
        ],
        current_paths: [
            {
                description: "Latest checkpoint for the active build node.",
                kind: "checkpoint",
                path: "_runtime/attempts/task-detail/latest-checkpoint.md",
                slot: null,
                version: null,
            },
        ],
        dependency_edges: [
            {
                consumer_node_key: "task_detail_build",
                description: "The build consumes the Task Detail source contract.",
                kind: "artifact",
                order_index: 0,
                provider_node_key: "task_detail_source_contract",
                slot: "task_detail_contract",
            },
            {
                consumer_node_key: "task_detail_review",
                description: "The review consumes the Task Detail implementation.",
                kind: "artifact",
                order_index: 1,
                provider_node_key: "task_detail_build",
                slot: "task_detail_patch",
            },
        ],
        dispatch_history: [
            {
                assignment_key: "assignment-root",
                assignment_summary: "Start the Task Detail runtime route refresh.",
                attempt_id: "attempt-root",
                delivery_status: "accepted",
                node_key: "root",
                rendered_at: "2026-06-29T13:30:00Z",
            },
            {
                assignment_key: "assignment-source-contract",
                assignment_summary: "Capture the runtime route source contract.",
                attempt_id: "attempt-source_contract",
                delivery_status: "provider_completed",
                node_key: "source_contract",
                rendered_at: "2026-06-29T13:32:00Z",
            },
            {
                assignment_key: "assignment-task-control-suite",
                assignment_summary: "Build the task control suite surface.",
                attempt_id: "attempt-task_control_suite",
                delivery_status: "accepted",
                node_key: "task_control_suite",
                rendered_at: "2026-06-29T13:35:00Z",
            },
            {
                assignment_key: "assignment-tasks-page",
                assignment_summary: "Refresh the runtime task list page.",
                attempt_id: "attempt-tasks_page",
                delivery_status: "provider_completed",
                node_key: "tasks_page",
                rendered_at: "2026-06-29T13:38:00Z",
            },
            {
                assignment_key: "assignment-task-detail-page",
                assignment_summary: "Coordinate the Task Detail page work.",
                attempt_id: "attempt-task_detail_page",
                delivery_status: "accepted",
                node_key: "task_detail_page",
                rendered_at: "2026-06-29T13:40:00Z",
            },
            {
                assignment_key: "assignment-human-request-page",
                assignment_summary: "Prepare the human request page route.",
                attempt_id: "attempt-human_request_page",
                delivery_status: "prepared",
                node_key: "human_request_page",
                rendered_at: "2026-06-29T13:41:00Z",
            },
            {
                assignment_key: "assignment-command-runs-page",
                assignment_summary: "Prepare the command runs page route.",
                attempt_id: "attempt-command_runs_page",
                delivery_status: "prepared",
                node_key: "command_runs_page",
                rendered_at: "2026-06-29T13:42:00Z",
            },
            {
                assignment_key: "assignment-task-detail-source-contract",
                assignment_summary: "Confirm Task Detail contract boundaries.",
                attempt_id: "attempt-task_detail_source_contract",
                delivery_status: "provider_completed",
                node_key: "task_detail_source_contract",
                rendered_at: "2026-06-29T13:43:00Z",
            },
            {
                assignment_key: "assignment-task-detail-build",
                assignment_summary: "Implement the Task Detail page.",
                attempt_id: "attempt-task_detail_build",
                delivery_status: "accepted",
                node_key: "task_detail_build",
                rendered_at: "2026-06-29T13:58:00Z",
            },
            {
                assignment_key: "assignment-task-detail-review",
                assignment_summary: "Review the Task Detail implementation.",
                attempt_id: "attempt-task_detail_review",
                delivery_status: "prepared",
                node_key: "task_detail_review",
                rendered_at: "2026-06-29T14:05:00Z",
            },
        ],
        graph_nodes: [
            {
                child_node_keys: ["source_contract", "task_control_suite"],
                depended_on_by_node_keys: [],
                depends_on_node_keys: [],
                description: "Coordinate the runtime route refresh.",
                node_key: "root",
                node_kind: "root",
                order_index: 0,
                parent_node_key: null,
                policy: null,
                role: "planning_lead",
            },
            {
                child_node_keys: [],
                depended_on_by_node_keys: [],
                depends_on_node_keys: [],
                description: "Capture the runtime route source contract.",
                node_key: "source_contract",
                node_kind: "worker",
                order_index: 1,
                parent_node_key: "root",
                policy: "browser_first_review",
                role: "source_reviewer",
            },
            {
                child_node_keys: [
                    "tasks_page",
                    "task_detail_page",
                    "human_request_page",
                    "command_runs_page",
                ],
                depended_on_by_node_keys: [],
                depends_on_node_keys: [],
                description: "Build the task control suite surface.",
                node_key: "task_control_suite",
                node_kind: "parent",
                order_index: 2,
                parent_node_key: "root",
                policy: "browser_first_worker",
                role: "ui_delivery_lead",
            },
            {
                child_node_keys: [],
                depended_on_by_node_keys: [],
                depends_on_node_keys: [],
                description: "Refresh the runtime task list page.",
                node_key: "tasks_page",
                node_kind: "worker",
                order_index: 3,
                parent_node_key: "task_control_suite",
                policy: "browser_first_worker",
                role: "ui_engineer",
            },
            {
                child_node_keys: [
                    "task_detail_source_contract",
                    "task_detail_build",
                    "task_detail_review",
                ],
                depended_on_by_node_keys: [],
                depends_on_node_keys: [],
                description: "Coordinate the Task Detail page work.",
                node_key: "task_detail_page",
                node_kind: "parent",
                order_index: 4,
                parent_node_key: "task_control_suite",
                policy: "browser_first_worker",
                role: "ui_delivery_lead",
            },
            {
                child_node_keys: [],
                depended_on_by_node_keys: [],
                depends_on_node_keys: [],
                description: "Prepare the human request page route.",
                node_key: "human_request_page",
                node_kind: "worker",
                order_index: 5,
                parent_node_key: "task_control_suite",
                policy: "browser_first_worker",
                role: "ui_engineer",
            },
            {
                child_node_keys: [],
                depended_on_by_node_keys: [],
                depends_on_node_keys: [],
                description: "Prepare the command runs page route.",
                node_key: "command_runs_page",
                node_kind: "worker",
                order_index: 6,
                parent_node_key: "task_control_suite",
                policy: "browser_first_worker",
                role: "ui_engineer",
            },
            {
                child_node_keys: [],
                depended_on_by_node_keys: ["task_detail_build"],
                depends_on_node_keys: [],
                description: "Confirm Task Detail contract boundaries.",
                node_key: "task_detail_source_contract",
                node_kind: "worker",
                order_index: 7,
                parent_node_key: "task_detail_page",
                policy: "browser_first_review",
                role: "source_reviewer",
            },
            {
                child_node_keys: [],
                depended_on_by_node_keys: ["task_detail_review"],
                depends_on_node_keys: ["task_detail_source_contract"],
                description: "Implement the Task Detail page.",
                node_key: "task_detail_build",
                node_kind: "worker",
                order_index: 8,
                parent_node_key: "task_detail_page",
                policy: "browser_first_worker",
                role: "ui_engineer",
            },
            {
                child_node_keys: [],
                depended_on_by_node_keys: [],
                depends_on_node_keys: ["task_detail_build"],
                description: "Review the Task Detail implementation.",
                node_key: "task_detail_review",
                node_kind: "worker",
                order_index: 9,
                parent_node_key: "task_detail_page",
                policy: "browser_first_review",
                role: "delivery_reviewer",
            },
        ],
        next_cursor: null,
        scope: "whole",
        task_id: TASK_DETAIL_TASK_ID,
    };
}

function payloadForEvent(
    eventType: components["schemas"]["TaskEventType"],
    nodeKey: string,
): Record<string, unknown> {
    switch (eventType) {
        case "task_started":
            return {
                initial_node_key: "root",
                summary: "Task lineage started.",
                task_title: "Refresh runtime route copy",
                workflow_key: "frontend-console-continuation-delivery",
                workflow_manifest_ref: createWorkflowManifestRef(),
            };
        case "dispatch_opened":
            return {
                assignment_key: `assignment-${nodeKey}`,
                attempt_id: `attempt-${nodeKey}`,
                control_state: "live",
                delivery_status: "accepted",
                node_key: nodeKey,
                previous_dispatch_id: null,
                summary: "Dispatch opened.",
            };
        case "checkpoint_recorded":
            return {
                checkpoint_id: "checkpoint-build-progress",
                checkpoint_kind: "progress",
                latest_checkpoint_ref: {
                    description: "Latest checkpoint.",
                    kind: "checkpoint",
                    path: "_runtime/attempts/task-detail/latest-checkpoint.md",
                },
                next_step: "Continue Task Detail implementation.",
                outcome: null,
                produced_artifacts: [
                    {
                        description: "Task Detail implementation evidence.",
                        kind: "artifact",
                        path: "tmp/autoclaw-frontend/continuation-implementation/07-task-detail/report.md",
                        slot: "frontend_scope_patch",
                    },
                ],
                summary: "Checkpoint recorded.",
            };
        case "boundary_accepted":
            return {
                boundary: "green",
                latest_checkpoint_ref: {
                    description: "Terminal checkpoint.",
                    kind: "checkpoint",
                    path: "_runtime/attempts/task-detail/latest-checkpoint.md",
                },
                next_node_key: "task_detail_page",
                previous_node_key: "task_detail_source_contract",
                resulting_flow_status: "running",
                summary: "Boundary accepted.",
            };
        case "child_assignment_staged":
            return {
                assignment_summary: "Review the Task Detail implementation.",
                child_assignment_ref: {
                    description: "Child assignment.",
                    kind: "assignment",
                    path: "_runtime/attempts/task-detail-review/assignment.md",
                },
                parent_node_key: "task_detail_page",
                summary: "Child assignment staged.",
                target_assignment_key: "assignment-task-detail-review",
                target_node_key: "task_detail_review",
            };
        case "child_assignment_committed":
            return {
                boundary: "yield",
                parent_node_key: "task_detail_page",
                source_dispatch_id: "dispatch-task_detail-page",
                summary: "Child assignment committed.",
                target_assignment_key: "assignment-task-detail-build",
                target_node_key: "task_detail_build",
            };
        case "structural_revision_adopted":
            return {
                active_flow_revision_id: "flow-revision-task-detail-1",
                affected_node_keys: ["task_detail_build", "task_detail_review"],
                operation: "add_child",
                previous_flow_revision_id: "flow-revision-task-detail-0",
                summary: "Structural revision adopted.",
                target_node_key: "task_detail_review",
            };
        case "human_request_opened":
        case "human_request_resolved":
        case "human_request_timed_out":
        case "human_request_cancelled":
            return {
                kind: "approval",
                request_id: "hr-task-detail-approval",
                status: eventType.replace("human_request_", ""),
                summary: "Human request state changed.",
            };
        case "command_run_started":
        case "command_run_progressed":
        case "command_run_cancel_requested":
        case "command_run_succeeded":
        case "command_run_failed":
        case "command_run_timed_out":
        case "command_run_cancelled":
            return {
                log_ref: "tmp/command-runs/run-task-detail-check.log",
                run_id: "run-task-detail-check",
                state: eventType.replace("command_run_", ""),
                summary: "Command run state changed.",
            };
        case "task_paused":
        case "task_resumed":
        case "task_cancelled":
            return {
                active_flow_revision_id: "flow-revision-task-detail-1",
                status: eventType.replace("task_", ""),
                summary: "Task control state changed.",
            };
    }
}

function occurredAtForEvent(
    eventType: components["schemas"]["TaskEventType"],
    index: number,
): string {
    const visualTime = TASK_DETAIL_VISUAL_EVENT_TIMES[eventType];
    if (visualTime !== undefined) {
        return visualTime;
    }
    return new Date(Date.parse(TASK_DETAIL_EVENT_BASE_AT) + (index + 6) * 60_000).toISOString();
}

function eventSourceForType(
    eventType: components["schemas"]["TaskEventType"],
): components["schemas"]["TaskEventSource"] {
    if (eventType === "task_started") {
        return "controller";
    }
    if (eventType.startsWith("task_") || eventType.startsWith("human_request_")) {
        return "control_api";
    }
    return "controller";
}

function createTaskEventStreamFrame(event: components["schemas"]["TaskEventRecord"]): string {
    return `id: ${event.event_id}\ndata: ${JSON.stringify(event)}\n\n`;
}
