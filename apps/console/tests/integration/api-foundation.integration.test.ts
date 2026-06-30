import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest";

import {
    AutoClawApiError,
    buildQueryParams,
    expectedFlowRevisionQuery,
    getNextCursor,
    isCursorResetError,
    requestJson,
} from "../../src/api/client";
import type { components } from "../../src/api/generated/openapi";
import {
    commandRunLogRoute,
    commandRunRoute,
    commandRunsRoute,
    cancelCommandRunRoute,
    controlTaskActionRoute,
    controlTaskEventsRoute,
    controlTaskRoute,
    controlTaskSnapshotRoute,
    controlTaskTraceRoute,
    definitionDraftFileRematerializeCurrentRoute,
    definitionDraftFileResetRoute,
    definitionDraftFileRoute,
    definitionDraftSetRoute,
    definitionDraftSetApplyRoute,
    definitionDraftSetMaterializeRoute,
    definitionDraftSetPreviewTaskComposeRoute,
    definitionDraftSetValidateRoute,
    definitionDraftSetsRoute,
    definitionRoute,
    definitionsRoute,
    definitionVersionsRoute,
    humanRequestsRoute,
    resolveHumanRequestRoute,
    runtimeTasksRoute,
    taskStartRoute,
} from "../../src/api/routes";
import {
    buildTaskEventStreamRequest,
    mergeTaskEvents,
    parseServerSentEventFrame,
    readTaskEventStream,
    reconnectTaskEventStream,
    taskEventStreamUrl,
} from "../../src/api/sse";
import {
    mapCommandRunRow,
    mapDefinitionSummary,
    mapDraftSetSummary,
    mapHumanRequestQueueItem,
    mapTaskEventItem,
    mapTaskRow,
    mapTaskStartResult,
} from "../../src/api/view-models";
import { createConsoleApiHandlers } from "../../src/mocks/handlers";
import {
    TEST_API_BASE_URL,
    TEST_API_KEY,
    TEST_TASK_ID,
    createBackendOperationFailureBody,
    createConsoleMockScenario,
    createOperationFailureBody,
    createRuntimeFlowSummary,
    createTaskEventRecord,
    createTaskEventStreamChunks,
    createTaskEventStreamFixture,
    createTaskStartRequest,
    createValidationErrorBody,
} from "../fixtures/console-api";

const config = {
    apiBaseUrl: TEST_API_BASE_URL,
    apiKey: TEST_API_KEY,
};
const scenario = createConsoleMockScenario();
const server = setupServer(...createConsoleApiHandlers(scenario));

beforeAll(() => {
    server.listen({ onUnhandledRequest: "error" });
});

afterEach(() => {
    server.resetHandlers();
});

afterAll(() => {
    server.close();
});

describe("console API client foundation", () => {
    it("forwards the API key and constructs typed query params", async () => {
        const seenRequests: Request[] = [];
        server.use(
            http.get("*/runtime/tasks", ({ request }) => {
                seenRequests.push(request);
                return HttpResponse.json({
                    items: [],
                    next_cursor: "next-cursor",
                } satisfies components["schemas"]["RuntimeFlowSummaryListResponse"]);
            }),
        );

        const route = runtimeTasksRoute({
            cursor: "cursor-1",
            limit: 25,
            q: "console",
            sort: "updated_at_desc",
            status: "running",
        });
        const response = await requestJson<components["schemas"]["RuntimeFlowSummaryListResponse"]>(
            {
                config,
                path: route.path,
                query: route.query,
            },
        );
        const requestUrl = new URL(seenRequests[0]?.url ?? "");

        expect(seenRequests[0]?.headers.get("X-AutoClaw-API-Key")).toBe(TEST_API_KEY);
        expect(requestUrl.searchParams.get("q")).toBe("console");
        expect(requestUrl.searchParams.get("limit")).toBe("25");
        expect(requestUrl.searchParams.get("status")).toBe("running");
        expect(getNextCursor(response)).toBe("next-cursor");
        expect(expectedFlowRevisionQuery("flow-1").toString()).toBe(
            "expected_active_flow_revision_id=flow-1",
        );
        expect(buildQueryParams({ empty: null, keep: false, multi: ["a", "b"] }).toString()).toBe(
            "keep=false&multi=a&multi=b",
        );
    });

    it("normalizes shared API error families into renderable errors", async () => {
        server.use(
            http.get("*/operation-failure", () =>
                HttpResponse.json(createOperationFailureBody(), { status: 409 }),
            ),
            http.get("*/backend-auth", () =>
                HttpResponse.json(
                    createBackendOperationFailureBody({
                        code: "illegal_caller",
                        retryable: false,
                        summary: "The AutoClaw API key is missing or invalid.",
                        suggested_next_step: "Provide a valid operator API key.",
                    }),
                    { status: 401 },
                ),
            ),
            http.get("*/backend-permission", () =>
                HttpResponse.json(
                    createBackendOperationFailureBody({
                        code: "capability_rejected",
                        retryable: false,
                        summary: "The current task capability does not allow this request.",
                        suggested_next_step: "Reread current task capabilities before retrying.",
                    }),
                    { status: 403 },
                ),
            ),
            http.get("*/backend-stale", () =>
                HttpResponse.json(
                    createBackendOperationFailureBody({
                        field_path: "expected_active_flow_revision_id",
                    }),
                    { status: 409 },
                ),
            ),
            http.get("*/backend-missing", () =>
                HttpResponse.json(
                    createBackendOperationFailureBody({
                        code: "missing_resource",
                        retryable: false,
                        summary: "The requested task does not exist.",
                        suggested_next_step: "Verify the task id and reread the task list.",
                    }),
                    { status: 404 },
                ),
            ),
            http.get("*/validation", () =>
                HttpResponse.json(createValidationErrorBody(), { status: 422 }),
            ),
            http.get("*/auth", () => new HttpResponse(null, { status: 401 })),
            http.get("*/permission", () => HttpResponse.text("Forbidden", { status: 403 })),
            http.get("*/missing", () => new HttpResponse(null, { status: 404 })),
            http.get("*/cursor-reset", () =>
                HttpResponse.json(
                    createOperationFailureBody({
                        code: "cursor_reset_required",
                        summary: "The supplied event cursor is stale.",
                    }),
                    { status: 410 },
                ),
            ),
            http.get("*/non-json", () => HttpResponse.text("not json", { status: 500 })),
            http.get("*/empty-error", () => new HttpResponse(null, { status: 502 })),
            http.get("*/network", () => HttpResponse.error()),
        );

        const operationFailure = await expectApiError("/operation-failure");
        expect(operationFailure.errorView.source).toBe("operation_failure");
        expect(operationFailure.errorView.code).toBe("stale_flow_revision");
        expect(operationFailure.errorView.isRetryable).toBe(true);

        const backendAuthFailure = await expectApiError("/backend-auth");
        expect(backendAuthFailure.errorView.source).toBe("operation_failure");
        expect(backendAuthFailure.errorView.code).toBe("illegal_caller");
        expect(backendAuthFailure.errorView.status).toBe(401);
        expect(backendAuthFailure.errorView.suggestedNextStep).toBe(
            "Provide a valid operator API key.",
        );

        const backendPermissionFailure = await expectApiError("/backend-permission");
        expect(backendPermissionFailure.errorView.code).toBe("capability_rejected");
        expect(backendPermissionFailure.errorView.status).toBe(403);

        const backendStaleFailure = await expectApiError("/backend-stale");
        expect(backendStaleFailure.errorView.code).toBe("stale_flow_revision");
        expect(backendStaleFailure.errorView.isRetryable).toBe(true);
        expect(backendStaleFailure.errorView.fieldErrors[0]?.path).toBe(
            "expected_active_flow_revision_id",
        );

        const backendMissingFailure = await expectApiError("/backend-missing");
        expect(backendMissingFailure.errorView.code).toBe("missing_resource");
        expect(backendMissingFailure.errorView.status).toBe(404);

        const validationFailure = await expectApiError("/validation");
        expect(validationFailure.errorView.source).toBe("validation");
        expect(validationFailure.errorView.fieldErrors[0]?.path).toBe("body.task.key");

        expect((await expectApiError("/auth")).errorView.code).toBe("auth_required");
        expect((await expectApiError("/permission")).errorView.code).toBe("permission_denied");
        expect((await expectApiError("/missing")).errorView.code).toBe("missing_resource");

        const cursorResetFailure = await expectApiError("/cursor-reset");
        expect(isCursorResetError(cursorResetFailure.errorView)).toBe(true);

        expect((await expectApiError("/non-json")).errorView.summary).toBe("not json");
        expect((await expectApiError("/empty-error")).errorView.code).toBe("http_502");
        expect((await expectApiError("/network")).errorView.source).toBe("network");

        const abortController = new AbortController();
        abortController.abort();
        const aborted = await expectApiError("/runtime/tasks", abortController.signal);
        expect(aborted.errorView.source).toBe("abort");
    });

    it("serves OpenAPI-shaped fixtures through MSW for every required route family", async () => {
        const taskListRoute = runtimeTasksRoute();
        const taskList = await requestJson<components["schemas"]["RuntimeFlowSummaryListResponse"]>(
            {
                config,
                path: taskListRoute.path,
                query: taskListRoute.query,
            },
        );
        const sharedHandlerAuthFailure = await expectApiError(taskListRoute.path, undefined, {
            ...config,
            apiKey: "wrong-key",
        });
        const taskReadRoute = controlTaskRoute(TEST_TASK_ID);
        const taskRead = await requestJson<components["schemas"]["RuntimeFlowRead"]>({
            config,
            path: taskReadRoute.path,
        });
        const snapshotRoute = controlTaskSnapshotRoute(TEST_TASK_ID);
        const snapshot = await requestJson<components["schemas"]["OperatorFlowSnapshotResponse"]>({
            config,
            path: snapshotRoute.path,
        });
        const traceRoute = controlTaskTraceRoute(TEST_TASK_ID);
        const trace = await requestJson<components["schemas"]["OperatorFlowTraceResponse"]>({
            config,
            path: traceRoute.path,
            query: traceRoute.query,
        });
        const pauseRoute = controlTaskActionRoute(
            TEST_TASK_ID,
            "pause",
            taskRead.active_flow_revision_id,
        );
        const pauseResponse = await requestJson<components["schemas"]["RuntimeFlowPauseResponse"]>({
            config,
            method: "POST",
            path: pauseRoute.path,
            query: pauseRoute.query,
        });
        const eventsRoute = controlTaskEventsRoute(TEST_TASK_ID, { through_event_id: "evt-001" });
        const events = await requestJson<components["schemas"]["TaskEventListResponse"]>({
            config,
            path: eventsRoute.path,
            query: eventsRoute.query,
        });
        const humanRoute = humanRequestsRoute(TEST_TASK_ID);
        const humanRequests = await requestJson<components["schemas"]["HumanRequestListResponse"]>({
            config,
            path: humanRoute.path,
        });
        const resolveRoute = resolveHumanRequestRoute(TEST_TASK_ID, "human-request-001");
        const resolved = await requestJson<components["schemas"]["HumanRequestResolveResponse"]>({
            body: { item_responses: [] },
            config,
            method: "POST",
            path: resolveRoute.path,
        });
        const commandRuns = await requestJson<components["schemas"]["CommandRunListResponse"]>({
            config,
            path: commandRunsRoute(TEST_TASK_ID).path,
        });
        const commandRun = await requestJson<components["schemas"]["CommandRunRecord"]>({
            config,
            path: commandRunRoute(TEST_TASK_ID, "run-001").path,
        });
        const commandCancel = await requestJson<components["schemas"]["CommandRunCancelResponse"]>({
            config,
            method: "POST",
            path: cancelCommandRunRoute(TEST_TASK_ID, "run-001").path,
        });
        const commandLog = await requestJson<components["schemas"]["CommandRunLogReadResponse"]>({
            config,
            path: commandRunLogRoute(TEST_TASK_ID, "run-001").path,
        });
        const definitions = await requestJson<
            components["schemas"]["DefinitionSummaryListResponse"]
        >({
            config,
            path: definitionsRoute("roles").path,
        });
        const definition = await requestJson<
            components["schemas"]["DefinitionRevisionDetailResponse"]
        >({
            config,
            path: definitionRoute("role", "role-fixture").path,
        });
        const versions = await requestJson<
            components["schemas"]["DefinitionRevisionHistoryResponse"]
        >({
            config,
            path: definitionVersionsRoute("role", "role-fixture").path,
        });
        const draftList = await requestJson<
            components["schemas"]["DefinitionDraftSetListResponse"]
        >({
            config,
            path: definitionDraftSetsRoute().path,
        });
        const draftDetail = await requestJson<
            components["schemas"]["DefinitionDraftSetDetailResponse"]
        >({
            config,
            path: definitionDraftSetRoute("draft-set-001").path,
        });
        const draftCreate = await requestJson<
            components["schemas"]["DefinitionDraftSetDetailResponse"]
        >({
            body: { materialize: [], preview_task_compose: null, title: "Created draft set" },
            config,
            method: "POST",
            path: definitionDraftSetsRoute().path,
        });
        const draftMaterialize = await requestJson<
            components["schemas"]["DefinitionDraftSetDetailResponse"]
        >({
            body: { definitions: [{ kind: "role", key: "frontend_engineer" }] },
            config,
            method: "POST",
            path: definitionDraftSetMaterializeRoute("draft-set-001").path,
        });
        const draftWrite = await requestJson<
            components["schemas"]["DefinitionDraftSetDetailResponse"]
        >({
            body: { body: "id: frontend_engineer\n", body_format: "yaml" },
            config,
            method: "PUT",
            path: definitionDraftFileRoute("draft-set-001", "role", "frontend_engineer").path,
        });
        const draftReset = await requestJson<
            components["schemas"]["DefinitionDraftSetDetailResponse"]
        >({
            body: { discard_local_changes: true },
            config,
            method: "POST",
            path: definitionDraftFileResetRoute("draft-set-001", "role", "frontend_engineer").path,
        });
        const draftRematerialize = await requestJson<
            components["schemas"]["DefinitionDraftSetDetailResponse"]
        >({
            body: { discard_local_changes: true },
            config,
            method: "POST",
            path: definitionDraftFileRematerializeCurrentRoute(
                "draft-set-001",
                "role",
                "frontend_engineer",
            ).path,
        });
        const draftValidation = await requestJson<
            components["schemas"]["DefinitionDraftValidationResponse"]
        >({
            config,
            method: "POST",
            path: definitionDraftSetValidateRoute("draft-set-001").path,
        });
        const draftPreview = await requestJson<
            components["schemas"]["DefinitionDraftTaskComposePreviewResponse"]
        >({
            body: { body: "tasks: []\n", body_format: "yaml" },
            config,
            method: "POST",
            path: definitionDraftSetPreviewTaskComposeRoute("draft-set-001").path,
        });
        const draftApply = await requestJson<components["schemas"]["DefinitionDraftApplyResponse"]>(
            {
                body: { should_start_task_after_apply: false },
                config,
                method: "POST",
                path: definitionDraftSetApplyRoute("draft-set-001").path,
            },
        );
        const draftDelete = await requestJson<undefined>({
            config,
            method: "DELETE",
            path: definitionDraftSetRoute("draft-set-001").path,
        });
        const taskStart = await requestJson<components["schemas"]["TaskStartResponse"]>({
            body: createTaskStartRequest(),
            config,
            method: "POST",
            path: taskStartRoute().path,
        });

        expect(mapTaskRow(taskList.items[0] ?? createRuntimeFlowSummary()).taskId).toBe(
            TEST_TASK_ID,
        );
        expect(sharedHandlerAuthFailure.errorView.code).toBe("illegal_caller");
        expect(sharedHandlerAuthFailure.errorView.source).toBe("operation_failure");
        expect(taskRead.active_flow_revision_id).toBe("flow-revision-001");
        expect(snapshot.stream_head_event_id).toBe("evt-001");
        expect(trace.task_id).toBe(TEST_TASK_ID);
        expect(pauseResponse.flow.task_id).toBe(TEST_TASK_ID);
        expect(mapTaskEventItem(events.items[0] ?? createTaskEventRecord()).eventId).toBe(
            "evt-001",
        );
        expect(
            mapHumanRequestQueueItem(humanRequests.items[0] ?? scenario.humanRequestList.items[0])
                .kind,
        ).toBe("direction");
        expect(resolved.resolution.resolution_kind).toBe("answered");
        expect(
            mapCommandRunRow(commandRuns.items[0] ?? scenario.commandRunList.items[0]).state,
        ).toBe("pending_start");
        expect(commandRun.task_id).toBe(TEST_TASK_ID);
        expect(commandCancel.run.state).toBe("cancellation_requested");
        expect(commandLog.content).toContain("command output");
        expect(
            mapDefinitionSummary(definitions.items[0] ?? scenario.definitionLists.roles.items[0])
                .key,
        ).toBe("role-fixture");
        expect(definition.revision_no).toBe(2);
        expect(versions.current_revision_no).toBe(2);
        expect(mapDraftSetSummary(draftList.items[0] ?? scenario.draftList.items[0]).state).toBe(
            "open",
        );
        expect(draftDetail.draft_set.files[0]?.status).toBe("modified");
        expect(draftCreate.draft_set.draft_set_id).toBe("draft-set-001");
        expect(draftMaterialize.draft_set.files[0]?.kind).toBe("role");
        expect(draftWrite.draft_set.files[0]?.body_format).toBe("yaml");
        expect(draftReset.draft_set.files[0]?.based_on.revision_no).toBe(2);
        expect(draftRematerialize.draft_set.files[0]?.based_on.content_hash).toBe(
            "sha256:baseline",
        );
        expect(draftValidation.status).toBe("valid");
        expect(draftPreview.validation.warnings[0]?.kind).toBe("preview");
        expect(draftApply.status).toBe("applied");
        expect(draftDelete).toBeUndefined();
        expect(mapTaskStartResult(taskStart).flowStatus).toBe("running");
    });
});

describe("fetch-based task event stream", () => {
    it("parses frames incrementally, resumes with cursor, dedupes, and preserves event order", async () => {
        const firstEvent = createTaskEventRecord({ event_id: "evt-001", event_seq: 1 });
        const duplicateFirstEvent = createTaskEventRecord({
            event_id: "evt-001",
            event_seq: 1,
            payload: { duplicate: true },
        });
        const secondEvent = createTaskEventRecord({ event_id: "evt-002", event_seq: 2 });
        const streamChunks = createTaskEventStreamChunks(
            [firstEvent, duplicateFirstEvent, secondEvent],
            { splitFirstFrameAt: 32 },
        );
        server.use(
            ...createConsoleApiHandlers(
                createConsoleMockScenario({
                    taskEventStream: createTaskEventStreamFixture({
                        chunks: [],
                        chunksByCursor: { "evt-000": streamChunks },
                    }),
                }),
            ),
        );

        const authFailure = await expectTaskEventStreamError({
            config: { ...config, apiKey: "wrong-key" },
            taskId: TEST_TASK_ID,
        });
        expect(authFailure.errorView.code).toBe("illegal_caller");
        expect(authFailure.errorView.source).toBe("operation_failure");

        const streamRequest = buildTaskEventStreamRequest(TEST_TASK_ID, {
            config,
            cursor: "evt-000",
        });
        expect(streamRequest.headers.get("X-AutoClaw-API-Key")).toBe(TEST_API_KEY);
        expect(streamRequest.headers.get("Accept")).toBe("text/event-stream");
        expect(streamRequest.url.searchParams.get("cursor")).toBe("evt-000");

        const result = await readTaskEventStream({
            config,
            cursor: "evt-000",
            taskId: TEST_TASK_ID,
        });

        expect(result.events.map((event) => event.event_id)).toEqual(["evt-001", "evt-002"]);
        expect(result.lastEventId).toBe("evt-002");
        expect(parseServerSentEventFrame("id: evt-a\nevent: task\ndata: {}\n\n")).toEqual({
            data: "{}",
            event: "task",
            id: "evt-a",
        });
        expect(mergeTaskEvents([secondEvent], [firstEvent, duplicateFirstEvent])).toEqual([
            duplicateFirstEvent,
            secondEvent,
        ]);
        expect(taskEventStreamUrl(TEST_TASK_ID, { config, cursor: "evt-002" })).toContain(
            "cursor=evt-002",
        );
    });

    it("supports abort from the event callback", async () => {
        const abortController = new AbortController();
        server.use(
            ...createConsoleApiHandlers(
                createConsoleMockScenario({
                    taskEventStream: createTaskEventStreamFixture({
                        events: [
                            createTaskEventRecord({ event_id: "evt-001", event_seq: 1 }),
                            createTaskEventRecord({ event_id: "evt-002", event_seq: 2 }),
                        ],
                    }),
                }),
            ),
        );

        const result = await readTaskEventStream({
            config,
            onEvent: () => {
                abortController.abort();
            },
            signal: abortController.signal,
            taskId: TEST_TASK_ID,
        });

        expect(result.events.map((event) => event.event_id)).toEqual(["evt-001"]);
    });

    it("signals cursor_reset_required and reconnects after the caller resets REST state", async () => {
        const resetEvent = createTaskEventRecord({ event_id: "evt-reset", event_seq: 10 });
        let resetWasCalled = false;

        server.use(
            ...createConsoleApiHandlers(
                createConsoleMockScenario({
                    taskEventStream: createTaskEventStreamFixture({
                        cursorResetCursors: ["stale-cursor"],
                        events: [resetEvent],
                    }),
                }),
            ),
        );

        const directResult = await readTaskEventStream({
            config,
            cursor: "stale-cursor",
            taskId: TEST_TASK_ID,
        });
        expect(directResult.cursorResetRequired).toBe(true);
        expect(directResult.error?.source).toBe("operation_failure");
        expect(directResult.error?.code).toBe("cursor_reset_required");
        expect(directResult.staleCursor).toBe("stale-cursor");

        const reconnectResult = await reconnectTaskEventStream({
            config,
            cursor: "stale-cursor",
            resetAfterCursorReset: () => {
                resetWasCalled = true;
            },
            taskId: TEST_TASK_ID,
        });

        expect(resetWasCalled).toBe(true);
        expect(reconnectResult.didResetCursor).toBe(true);
        expect(reconnectResult.events[0]?.event_id).toBe("evt-reset");
    });
});

async function expectApiError(
    path: string,
    signal?: AbortSignal,
    requestConfig: typeof config = config,
): Promise<AutoClawApiError> {
    try {
        await requestJson<unknown>({
            config: requestConfig,
            path,
            signal,
        });
    } catch (error) {
        if (error instanceof AutoClawApiError) {
            return error;
        }
        throw error;
    }

    throw new Error(`Expected ${path} to fail`);
}

async function expectTaskEventStreamError(
    options: Parameters<typeof readTaskEventStream>[0],
): Promise<AutoClawApiError> {
    try {
        await readTaskEventStream(options);
    } catch (error) {
        if (error instanceof AutoClawApiError) {
            return error;
        }
        throw error;
    }

    throw new Error("Expected task event stream request to fail");
}
