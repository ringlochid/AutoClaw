import type { ConsoleMockScenario, TaskEventStreamFixture } from "../../src/mocks/handlers";
import type { components } from "../../src/api/generated/openapi";

export const TEST_API_BASE_URL = "http://127.0.0.1:18125";
export const TEST_API_KEY = "autoclaw-console-test-key";
export const TEST_TASK_ID = "task-console-fixture";
export const TEST_UPDATED_AT = "2026-06-29T14:00:00Z";

export interface OperationFailureBody {
    readonly code: components["schemas"]["OperationFailureCode"];
    readonly field_path?: string | null;
    readonly is_retryable: boolean;
    readonly suggested_next_step?: string | null;
    readonly summary: string;
}

export interface BackendOperationFailureDetail {
    readonly code: components["schemas"]["OperationFailureCode"];
    readonly field_path: string | null;
    readonly ok: false;
    readonly retryable: boolean;
    readonly suggested_next_step?: string | null;
    readonly summary: string;
}

export interface BackendOperationFailureBody {
    readonly detail: BackendOperationFailureDetail;
}

export interface TaskEventStreamFixtureOptions {
    readonly chunks?: readonly string[];
    readonly chunksByCursor?: Readonly<Record<string, readonly string[]>>;
    readonly cursorResetCursors?: readonly string[];
    readonly events?: readonly components["schemas"]["TaskEventRecord"][];
}

export function createConsoleMockScenario(
    overrides: Partial<ConsoleMockScenario> = {},
): ConsoleMockScenario {
    const taskRead = createRuntimeFlowRead();
    const firstEvent = createTaskEventRecord({ event_id: "evt-001", event_seq: 1 });

    const scenario: ConsoleMockScenario = {
        apiKey: TEST_API_KEY,
        ...createCommandRunScenario(),
        ...createDefinitionScenario(),
        ...createDraftScenario(),
        ...createHumanRequestScenario(),
        ...createTaskScenario(taskRead, firstEvent),
    };
    return {
        ...scenario,
        ...overrides,
    };
}

function createTaskScenario(
    taskRead: components["schemas"]["RuntimeFlowRead"],
    firstEvent: components["schemas"]["TaskEventRecord"],
): Pick<
    ConsoleMockScenario,
    "snapshot" | "taskEvents" | "taskEventStream" | "taskList" | "taskRead" | "taskStart" | "trace"
> {
    return {
        snapshot: {
            current_paths: [],
            flow: taskRead,
            stream_head_event_id: firstEvent.event_id,
            top_actionable_items: [],
        },
        taskEvents: {
            items: [firstEvent],
            next_cursor: null,
            task_id: TEST_TASK_ID,
            through_event_id: firstEvent.event_id,
        },
        taskEventStream: createTaskEventStreamFixture({ events: [firstEvent] }),
        taskList: {
            items: [createRuntimeFlowSummary()],
            next_cursor: "cursor-next",
        },
        taskRead,
        taskStart: createTaskStartResponse(),
        trace: {
            boundary_history: [],
            checkpoint_history: [],
            current_paths: [],
            dispatch_history: [],
            next_cursor: null,
            scope: "current",
            task_id: TEST_TASK_ID,
        },
    };
}

export function createRuntimeFlowSummaryList(
    items: readonly components["schemas"]["RuntimeFlowSummary"][] = [createRuntimeFlowSummary()],
    nextCursor: string | null = null,
): components["schemas"]["RuntimeFlowSummaryListResponse"] {
    return {
        items: [...items],
        next_cursor: nextCursor,
    };
}

export function createMixedRuntimeTaskRows(): readonly components["schemas"]["RuntimeFlowSummary"][] {
    return [
        createRuntimeFlowSummary({
            current_node_key: "implement_frontend_scope",
            status: "running",
            task_id: "task-runtime-copy-refresh",
            task_summary: "Update the current task-control labels.",
            task_title: "Refresh runtime route copy",
            updated_at: "2026-06-29T13:54:00Z",
            workflow_key: "runtime_copy_refresh",
        }),
        createRuntimeFlowSummary({
            active_attempt_id: "attempt-definition-001",
            current_node_key: "review_frontend_scope",
            status: "pending",
            task_id: "task-definition-boundaries",
            task_summary: "Confirm draft-set apply and Task Start stay separate.",
            task_title: "Check Definition Editor boundaries",
            updated_at: "2026-06-29T13:31:00Z",
            workflow_key: "definition_authoring_suite",
        }),
        createRuntimeFlowSummary({
            active_attempt_id: "attempt-blocked-001",
            current_node_key: "implementation_delivery",
            status: "blocked",
            task_id: "task-stale-navigation-labels",
            task_summary: "Replace retired runtime names.",
            task_title: "Fix stale navigation labels",
            updated_at: "2026-06-29T12:58:00Z",
            workflow_key: "shape_navigation_contract",
        }),
        createRuntimeFlowSummary({
            active_attempt_id: "attempt-paused-001",
            current_node_key: "review_frontend_scope",
            status: "paused",
            task_id: "task-command-run-overflow",
            task_summary: "Check long rows on narrow widths.",
            task_title: "Verify command-run overflow",
            updated_at: "2026-06-29T11:42:00Z",
            workflow_key: "command_runs_overflow",
        }),
        createRuntimeFlowSummary({
            active_attempt_id: "attempt-succeeded-001",
            current_node_key: "release_closure",
            status: "succeeded",
            task_id: "task-release-note",
            task_summary: "Archive accepted evidence.",
            task_title: "Close frontend planning note",
            updated_at: "2026-06-29T10:15:00Z",
            workflow_key: "frontend_console_continuation",
        }),
        createRuntimeFlowSummary({
            active_attempt_id: "attempt-cancelled-001",
            current_node_key: "root",
            status: "cancelled",
            task_id: "task-old-compose-refresh",
            task_summary: "Cancelled stale draft refresh after continuation superseded it.",
            task_title: "Retire old compose refresh",
            updated_at: "2026-06-29T09:45:00Z",
            workflow_key: "frontend_console_continuation",
        }),
    ];
}

export function createLongRuntimeTaskRow(): components["schemas"]["RuntimeFlowSummary"] {
    return createRuntimeFlowSummary({
        active_attempt_id: "attempt-with-a-long-but-real-controller-identifier-001",
        current_node_key: "verify_extremely_long_console_task_row_without_horizontal_overflow",
        status: "running",
        task_id: "task-long-row-runtime-list-validation",
        task_summary:
            "Validate a long but controller-backed summary that should wrap inside the scan-first task list without hiding the status, updated time, or open target.",
        task_title:
            "Validate long task title wrapping inside the scan-first Tasks route implementation",
        updated_at: "2026-06-29T08:30:00Z",
        workflow_key: "frontend_console_runtime_task_list_visual_validation",
    });
}

function createHumanRequestScenario(): Pick<
    ConsoleMockScenario,
    "humanRequestList" | "humanRequestResolve"
> {
    const humanRequest = createHumanRequestRead();
    return {
        humanRequestList: {
            items: [
                humanRequest,
                createHumanRequestRead({ kind: "approval", request_id: "hr-approval" }),
                createHumanRequestRead({ kind: "input", request_id: "hr-input" }),
                createHumanRequestRead({ kind: "review", request_id: "hr-review" }),
            ],
            task_id: TEST_TASK_ID,
        },
        humanRequestResolve: {
            resolution: {
                item_responses: [
                    {
                        extra_notes: "Operator approved.",
                        item_id: "request-item-1",
                        selected_option: "approve",
                    },
                ],
                request_id: humanRequest.request.request_id,
                resolution_kind: "answered",
                resolved_at: TEST_UPDATED_AT,
                resolved_by_actor_ref: "operator:test",
                task_id: TEST_TASK_ID,
            },
            task_id: TEST_TASK_ID,
        },
    };
}

function createCommandRunScenario(): Pick<
    ConsoleMockScenario,
    "commandRun" | "commandRunCancel" | "commandRunList" | "commandRunLog"
> {
    return {
        commandRun: createCommandRunRecord(),
        commandRunCancel: {
            run: createCommandRunListItem({ state: "cancellation_requested" }),
            task_id: TEST_TASK_ID,
        },
        commandRunList: {
            items: [
                createCommandRunListItem({ state: "pending_start" }),
                createCommandRunListItem({ run_id: "run-running", state: "running" }),
                createCommandRunListItem({ run_id: "run-cancel", state: "cancellation_requested" }),
                createCommandRunListItem({ run_id: "run-succeeded", state: "succeeded" }),
                createCommandRunListItem({ run_id: "run-failed", state: "failed" }),
                createCommandRunListItem({ run_id: "run-timeout", state: "timed_out" }),
                createCommandRunListItem({ run_id: "run-cancelled", state: "cancelled" }),
            ],
            next_cursor: null,
            task_id: TEST_TASK_ID,
        },
        commandRunLog: {
            content: "command output",
            log_ref: "tmp/command-runs/run-001.log",
            run_id: "run-001",
            task_id: TEST_TASK_ID,
        },
    };
}

function createDefinitionScenario(): Pick<
    ConsoleMockScenario,
    "definitionDetail" | "definitionLists" | "definitionVersions"
> {
    return {
        definitionDetail: createDefinitionRevisionDetail("role"),
        definitionLists: {
            policies: createDefinitionList("policy"),
            roles: createDefinitionList("role"),
            workflows: createDefinitionList("workflow"),
        },
        definitionVersions: createDefinitionVersions(),
    };
}

function createDraftScenario(): Pick<
    ConsoleMockScenario,
    "draftApply" | "draftDetail" | "draftList" | "draftPreview" | "draftValidation"
> {
    const draftDetail = createDraftSetDetail();
    const draftValidation = createDraftValidation();
    return {
        draftApply: {
            draft_set_id: "draft-set-001",
            published_revisions: [
                {
                    content_hash: "sha256:published",
                    key: "frontend_engineer",
                    kind: "role",
                    revision_no: 3,
                },
            ],
            started_task_id: null,
            status: "applied",
            task_start_failure: null,
            task_start_status: "not_requested",
            validation: draftValidation,
        },
        draftDetail: {
            draft_set: draftDetail,
        },
        draftList: {
            items: [createDraftSetSummary()],
            next_cursor: null,
        },
        draftPreview: {
            status: "valid",
            validation: draftValidation,
        },
        draftValidation,
    };
}

export function createRuntimeFlowSummary(
    overrides: Partial<components["schemas"]["RuntimeFlowSummary"]> = {},
): components["schemas"]["RuntimeFlowSummary"] {
    return {
        active_attempt_id: "attempt-001",
        active_flow_revision_id: "flow-revision-001",
        current_node_key: "implement_frontend_scope",
        status: "running",
        task_id: TEST_TASK_ID,
        task_summary: "Implement the console frontend foundation.",
        task_title: "Console Frontend Foundation",
        updated_at: TEST_UPDATED_AT,
        workflow_key: "frontend-console-continuation-delivery",
        workflow_manifest_ref: createWorkflowManifestRef(),
        ...overrides,
    };
}

export function createRuntimeFlowRead(
    overrides: Partial<components["schemas"]["RuntimeFlowRead"]> = {},
): components["schemas"]["RuntimeFlowRead"] {
    return {
        ...createRuntimeFlowSummary(),
        ...overrides,
    };
}

export function createWorkflowManifestRef(): components["schemas"]["WorkflowManifestRef"] {
    return {
        description: "Workflow manifest",
        path: "_runtime/workflow-manifest.md",
    };
}

export function createTaskEventRecord(
    overrides: Partial<components["schemas"]["TaskEventRecord"]> = {},
): components["schemas"]["TaskEventRecord"] {
    const eventId = overrides.event_id ?? "evt-001";
    return {
        actor_ref: "controller",
        attempt_id: "attempt-001",
        dispatch_id: "dispatch-001",
        event_hash: `hash-${eventId}`,
        event_id: eventId,
        event_seq: overrides.event_seq ?? 1,
        event_source: "controller",
        event_type: "task_started",
        flow_revision_id: "flow-revision-001",
        node_key: "root",
        occurred_at: TEST_UPDATED_AT,
        payload: { summary: "Task started." },
        prev_event_hash: null,
        task_id: TEST_TASK_ID,
        ...overrides,
    };
}

export function createTaskEventStreamFixture(
    options: TaskEventStreamFixtureOptions = {},
): TaskEventStreamFixture {
    const events = options.events ?? [createTaskEventRecord()];
    return {
        chunks: options.chunks ?? createTaskEventStreamChunks(events),
        chunksByCursor: options.chunksByCursor ?? {},
        cursorResetCursors: options.cursorResetCursors ?? [],
    };
}

export function createTaskEventStreamChunks(
    events: readonly components["schemas"]["TaskEventRecord"][],
    options: { readonly splitFirstFrameAt?: number } = {},
): readonly string[] {
    const frames = events.map((event) => createTaskEventStreamFrame(event));
    const splitFirstFrameAt = options.splitFirstFrameAt;
    if (
        splitFirstFrameAt === undefined ||
        frames.length === 0 ||
        splitFirstFrameAt <= 0 ||
        splitFirstFrameAt >= frames[0].length
    ) {
        return frames;
    }

    const [firstFrame, ...remainingFrames] = frames;
    return [
        firstFrame.slice(0, splitFirstFrameAt),
        firstFrame.slice(splitFirstFrameAt),
        ...remainingFrames,
    ];
}

export function createTaskEventStreamFrame(
    event: components["schemas"]["TaskEventRecord"],
): string {
    return `id: ${event.event_id}\ndata: ${JSON.stringify(event)}\n\n`;
}

export function createHumanRequestRead(
    overrides: Partial<components["schemas"]["PendingHumanRequest"]> = {},
): components["schemas"]["HumanRequestRead"] {
    const kind = overrides.kind ?? "direction";
    return {
        request: {
            items: [
                {
                    input_payload_schema: kind === "input" ? { type: "object" } : null,
                    item_id: "request-item-1",
                    options:
                        kind === "approval"
                            ? [
                                  {
                                      description: "Approve the action.",
                                      id: "approve",
                                      title: "Approve",
                                  },
                                  {
                                      description: "Decline the action.",
                                      id: "decline",
                                      title: "Decline",
                                  },
                              ]
                            : [],
                    prompt: "Choose the next operator action.",
                    recommended_option: kind === "approval" ? "approve" : null,
                },
            ],
            kind,
            opened_at: TEST_UPDATED_AT,
            request_id: "human-request-001",
            requester_node: "implement_frontend_scope",
            status: "open",
            suggested_human_instruction: "Review the request and answer the current item.",
            summary: "Operator input is needed.",
            task_id: TEST_TASK_ID,
            timeout: {
                default_behavior: "block",
                due_at: "2026-06-29T16:00:00Z",
            },
            title: "Review requested",
            ...overrides,
        },
        resolution: null,
    };
}

export function createCommandRunListItem(
    overrides: Partial<components["schemas"]["CommandRunListItem"]> = {},
): components["schemas"]["CommandRunListItem"] {
    return {
        command: "make console-test-integration",
        created_at: TEST_UPDATED_AT,
        description: "Run console integration tests.",
        ended_at: null,
        exit_code: null,
        log_ref: "tmp/command-runs/run-001.log",
        run_id: "run-001",
        signal: null,
        started_at: TEST_UPDATED_AT,
        state: "running",
        summary: "Integration tests are running.",
        timeout_seconds: 120,
        workdir: "/home/ubuntu/leo/projects/autoclaw",
        ...overrides,
    };
}

export function createCommandRunRecord(
    overrides: Partial<components["schemas"]["CommandRunRecord"]> = {},
): components["schemas"]["CommandRunRecord"] {
    return {
        attempt_id: "attempt-001",
        cancellation_requested_at: null,
        cancellation_requested_by_actor_ref: null,
        command: "make console-test-integration",
        created_at: TEST_UPDATED_AT,
        description: "Run console integration tests.",
        dispatch_id: "dispatch-001",
        ended_at: null,
        latest_log_ref: "tmp/command-runs/run-001.log",
        latest_update: "Started integration lane.",
        run_id: "run-001",
        started_at: TEST_UPDATED_AT,
        state: "running",
        task_id: TEST_TASK_ID,
        terminal_actor_ref: null,
        terminal_event_source: null,
        terminal_result: null,
        timeout_seconds: 120,
        workdir: "/home/ubuntu/leo/projects/autoclaw",
        ...overrides,
    };
}

export function createDefinitionList(
    kind: components["schemas"]["DefinitionKind"],
): components["schemas"]["DefinitionSummaryListResponse"] {
    return {
        items: [
            {
                allowed_node_kinds: kind === "role" ? ["worker"] : null,
                applies_to: kind === "policy" ? ["worker"] : null,
                budget_spec: null,
                current_revision_no: 2,
                description: `${kind} definition`,
                key: `${kind}-fixture`,
                labels: ["console"],
                title: `${kind} fixture`,
                updated_at: TEST_UPDATED_AT,
            },
        ],
        kind,
        next_cursor: null,
    };
}

export function createDefinitionRevisionDetail(
    kind: components["schemas"]["DefinitionKind"],
): components["schemas"]["DefinitionRevisionDetailResponse"] {
    return {
        content: createDefinitionContent(kind),
        key: `${kind}-fixture`,
        recorded_by: null,
        revision_no: 2,
        updated_at: TEST_UPDATED_AT,
    };
}

export function createDefinitionVersions(): components["schemas"]["DefinitionRevisionHistoryResponse"] {
    return {
        current_revision_no: 2,
        items: [
            {
                recorded_by: null,
                revision_no: 2,
                updated_at: TEST_UPDATED_AT,
            },
        ],
        key: "role-fixture",
        kind: "role",
        next_cursor: null,
    };
}

export function createDraftSetSummary(): components["schemas"]["DefinitionDraftSetSummary"] {
    return {
        created_at: TEST_UPDATED_AT,
        draft_set_id: "draft-set-001",
        files: [createDraftFileSummary()],
        preview_task_compose_path: null,
        state: "open",
        title: "Console fixture draft set",
        updated_at: TEST_UPDATED_AT,
    };
}

export function createDraftSetDetail(): components["schemas"]["DefinitionDraftSetDetail"] {
    return {
        created_at: TEST_UPDATED_AT,
        draft_set_id: "draft-set-001",
        files: [createDraftFileDetail()],
        preview_task_compose_body: null,
        preview_task_compose_path: null,
        state: "open",
        title: "Console fixture draft set",
        updated_at: TEST_UPDATED_AT,
    };
}

export function createDraftValidation(): components["schemas"]["DefinitionDraftValidationResponse"] {
    return {
        draft_set_id: "draft-set-001",
        errors: [],
        status: "valid",
        warnings: [
            {
                code: "review_recommended",
                kind: "preview",
                message: "Review generated task-compose before launch.",
                path: "workflow.root",
            },
        ],
    };
}

export function createTaskStartRequest(): components["schemas"]["TaskStartRequest"] {
    return {
        roots: {
            context: {
                host_path: "/home/ubuntu/leo/projects/autoclaw/tmp",
                mode: "ensure_host_path",
            },
            workspace: {
                host_path: null,
                mode: "ensure_task_default",
            },
        },
        task: {
            instruction: "Run the console frontend continuation workflow.",
            key: "console-frontend-foundation",
            summary: "Implement API foundation.",
            title: "Console Frontend Foundation",
        },
        workflow: {
            key: "frontend-console-continuation-delivery",
        },
    };
}

export function createTaskStartResponse(): components["schemas"]["TaskStartResponse"] {
    return {
        active_flow_revision_id: "flow-revision-001",
        compiled_plan_id: "compiled-plan-001",
        flow_status: "running",
        task_id: TEST_TASK_ID,
        workflow_manifest_ref: createWorkflowManifestRef(),
    };
}

export function createOperationFailureBody(
    overrides: Partial<OperationFailureBody> = {},
): OperationFailureBody {
    return {
        code: "stale_flow_revision",
        is_retryable: true,
        suggested_next_step: "Reread current task state and retry.",
        summary: "The active flow revision is stale.",
        ...overrides,
    };
}

export function createBackendOperationFailureBody(
    overrides: Partial<BackendOperationFailureDetail> = {},
): BackendOperationFailureBody {
    return {
        detail: {
            code: "stale_flow_revision",
            field_path: null,
            ok: false,
            retryable: true,
            suggested_next_step: "Reread current task state and retry.",
            summary: "The active flow revision is stale.",
            ...overrides,
        },
    };
}

export function createValidationErrorBody(): components["schemas"]["HTTPValidationError"] {
    return {
        detail: [
            {
                ctx: {},
                input: "",
                loc: ["body", "task", "key"],
                msg: "String should have at least 1 character",
                type: "string_too_short",
            },
        ],
    };
}

function createDefinitionContent(
    kind: components["schemas"]["DefinitionKind"],
): components["schemas"]["DefinitionContent-Output"] {
    if (kind === "policy") {
        return {
            applies_to: ["worker"],
            capabilities: {
                command_run: "allow",
                human_request: {
                    allowed_kinds: ["approval"],
                    mode: "deny",
                },
            },
            description: "Policy fixture",
            id: "policy-fixture",
            instruction: "Follow policy.",
            labels: ["console"],
            title: "Policy Fixture",
        };
    }

    if (kind === "workflow") {
        return {
            description: "Workflow fixture",
            id: "workflow-fixture",
            root: {
                children: null,
                criteria: null,
                description: "Root node",
                id: "root",
                instruction: "Coordinate the work.",
                policy: "standard-parent",
                produces: null,
                provider_preference: null,
                role: "root_planning_lead",
                title: "Root",
            },
        };
    }

    return {
        allowed_node_kinds: ["worker"],
        description: "Role fixture",
        id: "role-fixture",
        instruction: "Implement the assigned scope.",
        labels: ["console"],
        title: "Role Fixture",
    };
}

function createDraftFileSummary(): components["schemas"]["DefinitionDraftFileSummary"] {
    return {
        based_on: {
            content_hash: "sha256:baseline",
            revision_no: 2,
            source_path: null,
        },
        body_format: "yaml",
        content_hash: "sha256:draft",
        draft_path: "drafts/roles/frontend_engineer.yaml",
        key: "frontend_engineer",
        kind: "role",
        normalized_path: "drafts/roles/frontend_engineer.json",
        status: "modified",
    };
}

function createDraftFileDetail(): components["schemas"]["DefinitionDraftFileDetail"] {
    return {
        ...createDraftFileSummary(),
        baseline_body: "id: frontend_engineer\n",
        baseline_normalized_content: null,
        body: "id: frontend_engineer\ndescription: Frontend engineer\n",
        normalized_content: null,
    };
}
