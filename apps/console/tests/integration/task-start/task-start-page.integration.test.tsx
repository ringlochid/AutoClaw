import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "../../../src/api/generated/openapi";
import { TaskStartPage } from "../../../src/features/task-start/TaskStartPage";
import {
    createBackendOperationFailureBody,
    createTaskStartResponse,
    createValidationErrorBody,
    TEST_API_BASE_URL,
    TEST_API_KEY,
    TEST_TASK_ID,
} from "../../fixtures/console-api";
import {
    SECOND_TASK_START_WORKFLOW_KEY,
    TASK_START_WORKFLOW_KEY,
    createTaskStartWorkflowDetail,
    createTaskStartWorkflowRows,
    createTaskStartWorkflowVersions,
} from "../../fixtures/task-start";
import { createDefinitionSummaryList } from "../../fixtures/definitions";

const server = setupServer();

beforeAll(() => {
    server.listen({ onUnhandledRequest: "error" });
});

beforeEach(() => {
    vi.stubEnv("VITE_AUTOCLAW_API_BASE_URL", TEST_API_BASE_URL);
    vi.stubEnv("VITE_AUTOCLAW_API_KEY", TEST_API_KEY);
});

afterEach(() => {
    cleanup();
    server.resetHandlers();
    vi.unstubAllEnvs();
});

afterAll(() => {
    server.close();
});

describe("TaskStartPage", () => {
    it("searches stored workflows, previews locally, and starts with omitted default roots", async () => {
        const user = userEvent.setup();
        const seenRequests: URL[] = [];
        let startBody: components["schemas"]["TaskStartRequest"] | null = null;
        installTaskStartHandlers({
            onRequest: (requestUrl) => {
                seenRequests.push(requestUrl);
            },
            onStart: async (request) => {
                startBody = (await request.json()) as components["schemas"]["TaskStartRequest"];
            },
        });

        renderTaskStartPage();

        expect(await screen.findByRole("heading", { name: "Task Start" })).toBeVisible();
        expect((await screen.findAllByText(TASK_START_WORKFLOW_KEY)).length).toBeGreaterThan(0);
        expect(screen.getByText("Ready to start from the selected stored workflow.")).toBeVisible();
        expect(seenRequests[0]?.pathname).toBe("/definitions/workflows");
        expect(seenRequests[0]?.searchParams.get("limit")).toBe("8");
        expect(seenRequests[0]?.searchParams.get("sort")).toBe("updated_at_desc");

        await user.click(screen.getByRole("button", { name: "Preview" }));
        const preview = within(screen.getByRole("region", { name: "Preview" }));
        expect(preview.getByText("Workflow")).toBeVisible();
        expect(preview.getAllByText("Task default")).toHaveLength(2);
        expect(startBody).toBeNull();

        await user.click(screen.getByRole("button", { name: "Start Task" }));
        expect(await screen.findByText("Task start accepted")).toBeVisible();
        expect(screen.getByText("Running")).toBeVisible();
        expect(screen.queryByText(TEST_TASK_ID)).not.toBeInTheDocument();
        expect(screen.queryByText("compiled-plan-001")).not.toBeInTheDocument();
        expect(screen.queryByText("flow-revision-001")).not.toBeInTheDocument();
        expect(screen.queryByText("_runtime/workflow-manifest.md")).not.toBeInTheDocument();
        expect(startBody).toEqual({
            task: {
                instruction:
                    "Keep the work scoped to the current assignment and publish focused verification.",
                key: "implement-task-start-launch-form",
                summary: "Launch one bounded task from stored workflow truth.",
                title: "Implement Task Start launch form",
            },
            workflow: {
                key: TASK_START_WORKFLOW_KEY,
            },
        });
    });

    it("validates required fields and explicit workspace/context host modes before start", async () => {
        const user = userEvent.setup();
        let startBody: components["schemas"]["TaskStartRequest"] | null = null;
        installTaskStartHandlers({
            onStart: async (request) => {
                startBody = (await request.json()) as components["schemas"]["TaskStartRequest"];
            },
        });

        renderTaskStartPage();
        expect((await screen.findAllByText(TASK_START_WORKFLOW_KEY)).length).toBeGreaterThan(0);

        await user.clear(screen.getByLabelText("Task key"));
        await user.click(
            within(screen.getByRole("region", { name: "Workspace root" })).getByRole("button", {
                name: "Create host path",
            }),
        );
        await user.click(
            within(screen.getByRole("region", { name: "Context root" })).getByRole("button", {
                name: "Use existing host",
            }),
        );
        await user.click(screen.getByRole("button", { name: "Start Task" }));

        expect(await screen.findByText("Task key is required.")).toBeVisible();
        expect(screen.getByText("Workspace host path is required.")).toBeVisible();
        expect(screen.getByText("Context host path is required.")).toBeVisible();
        expect(startBody).toBeNull();

        await user.type(screen.getByLabelText("Task key"), "task-start-with-host-roots");
        const workspaceRoot = within(screen.getByRole("region", { name: "Workspace root" }));
        const contextRoot = within(screen.getByRole("region", { name: "Context root" }));
        await user.type(workspaceRoot.getByLabelText("Host path"), "/tmp/autoclaw-workspace");
        await user.type(contextRoot.getByLabelText("Host path"), "/tmp/autoclaw-context");
        await user.click(screen.getByRole("button", { name: "Start Task" }));

        await waitFor(() => {
            expect(startBody?.roots).toEqual({
                context: {
                    host_path: "/tmp/autoclaw-context",
                    mode: "use_existing_host",
                },
                workspace: {
                    host_path: "/tmp/autoclaw-workspace",
                    mode: "ensure_host_path",
                },
            });
        });
    });

    it("renders workflow empty, workflow-missing, auth, and validation failures without clearing inputs", async () => {
        const user = userEvent.setup();
        server.use(
            http.get("*/definitions/workflows", ({ request }) => {
                const requestUrl = new URL(request.url);
                if (requestUrl.searchParams.get("q") === "missing") {
                    return HttpResponse.json(createDefinitionSummaryList("workflow", [], null));
                }
                return HttpResponse.json(
                    createDefinitionSummaryList("workflow", createTaskStartWorkflowRows(), null),
                );
            }),
            http.get("*/definitions/workflow/:key", ({ params }) => {
                if (params.key === SECOND_TASK_START_WORKFLOW_KEY) {
                    return HttpResponse.json(
                        createBackendOperationFailureBody({
                            code: "missing_resource",
                            retryable: false,
                            summary: "The selected workflow no longer exists.",
                        }),
                        { status: 404 },
                    );
                }
                return HttpResponse.json(createTaskStartWorkflowDetail(String(params.key)));
            }),
            http.get("*/definitions/workflow/:key/versions", ({ params }) =>
                HttpResponse.json(createTaskStartWorkflowVersions(String(params.key))),
            ),
            http.post("*/tasks/start", () =>
                HttpResponse.json(createValidationErrorBody(), { status: 422 }),
            ),
        );

        renderTaskStartPage();
        expect((await screen.findAllByText(TASK_START_WORKFLOW_KEY)).length).toBeGreaterThan(0);
        await user.type(screen.getByLabelText("Search workflow"), "missing");
        expect(await screen.findByText("No matching workflows")).toBeVisible();

        await user.clear(screen.getByLabelText("Search workflow"));
        await user.click(
            await screen.findByRole("button", { name: new RegExp(SECOND_TASK_START_WORKFLOW_KEY) }),
        );
        expect(await screen.findByText("Selected workflow could not load")).toBeVisible();

        await user.click(screen.getByRole("button", { name: "Start Task" }));
        expect(
            await screen.findByText(
                "Selected workflow could not be confirmed from stored registry truth.",
            ),
        ).toBeVisible();
        expect(screen.getByLabelText("Task key")).toHaveValue("implement-task-start-launch-form");

        cleanup();
        server.resetHandlers();
        server.use(
            http.get("*/definitions/workflows", () =>
                HttpResponse.json(
                    createBackendOperationFailureBody({
                        code: "illegal_caller",
                        retryable: false,
                        summary: "The AutoClaw API key is missing or invalid.",
                    }),
                    { status: 401 },
                ),
            ),
        );

        renderTaskStartPage();
        expect(await screen.findByText("Access to workflows failed")).toBeVisible();

        cleanup();
        server.resetHandlers();
        installTaskStartHandlers({
            startResponse: HttpResponse.json(createValidationErrorBody(), { status: 422 }),
        });
        renderTaskStartPage();
        expect((await screen.findAllByText(TASK_START_WORKFLOW_KEY)).length).toBeGreaterThan(0);
        await user.click(screen.getByRole("button", { name: "Start Task" }));
        expect(await screen.findByText("Task Start validation failed")).toBeVisible();
        expect(screen.getByLabelText("Task key")).toHaveValue("implement-task-start-launch-form");
    });

    it("preserves inputs when invalid host path, occupied workspace, or permission failures return from start", async () => {
        const user = userEvent.setup();
        installTaskStartHandlers({
            startResponse: HttpResponse.json(
                createBackendOperationFailureBody({
                    code: "invalid_request_shape",
                    field_path: "roots.workspace.host_path",
                    retryable: false,
                    summary: "Workspace host path does not exist.",
                }),
                { status: 400 },
            ),
        });

        renderTaskStartPage();
        expect((await screen.findAllByText(TASK_START_WORKFLOW_KEY)).length).toBeGreaterThan(0);
        await user.click(
            within(screen.getByRole("region", { name: "Workspace root" })).getByRole("button", {
                name: "Use existing host",
            }),
        );
        await user.type(
            within(screen.getByRole("region", { name: "Workspace root" })).getByLabelText(
                "Host path",
            ),
            "/missing/workspace",
        );
        await user.click(screen.getByRole("button", { name: "Start Task" }));
        expect(await screen.findByText("Workspace host path does not exist.")).toBeVisible();
        expect(screen.getByLabelText("Task key")).toHaveValue("implement-task-start-launch-form");

        cleanup();
        server.resetHandlers();
        installTaskStartHandlers({
            startResponse: HttpResponse.json(
                createBackendOperationFailureBody({
                    code: "conflicting_continuation",
                    retryable: false,
                    summary: "The selected workspace is already held by a live task.",
                }),
                { status: 409 },
            ),
        });
        renderTaskStartPage();
        expect((await screen.findAllByText(TASK_START_WORKFLOW_KEY)).length).toBeGreaterThan(0);
        await user.click(screen.getByRole("button", { name: "Start Task" }));
        expect(
            await screen.findByText("The selected workspace is already held by a live task."),
        ).toBeVisible();

        cleanup();
        server.resetHandlers();
        installTaskStartHandlers({
            startResponse: HttpResponse.json(
                createBackendOperationFailureBody({
                    code: "illegal_caller",
                    retryable: false,
                    summary: "Starting tasks requires an operator API key.",
                }),
                { status: 403 },
            ),
        });
        renderTaskStartPage();
        expect((await screen.findAllByText(TASK_START_WORKFLOW_KEY)).length).toBeGreaterThan(0);
        await user.click(screen.getByRole("button", { name: "Start Task" }));
        expect(await screen.findByText("Access to Task Start failed")).toBeVisible();
        expect(screen.getByText("Starting tasks requires an operator API key.")).toBeVisible();
    });
});

function renderTaskStartPage() {
    return render(
        <MemoryRouter initialEntries={["/task-start"]}>
            <Routes>
                <Route element={<TaskStartPage />} path="/task-start" />
            </Routes>
        </MemoryRouter>,
    );
}

function installTaskStartHandlers({
    onRequest,
    onStart,
    startResponse,
}: {
    readonly onRequest?: (requestUrl: URL) => void;
    readonly onStart?: (request: Request) => Promise<void>;
    readonly startResponse?: Response;
} = {}): void {
    server.use(
        http.get("*/definitions/workflows", ({ request }) => {
            const requestUrl = new URL(request.url);
            onRequest?.(requestUrl);
            return HttpResponse.json(
                createDefinitionSummaryList("workflow", createTaskStartWorkflowRows(), null),
            );
        }),
        http.get("*/definitions/workflow/:key", ({ params }) =>
            HttpResponse.json(createTaskStartWorkflowDetail(String(params.key))),
        ),
        http.get("*/definitions/workflow/:key/versions", ({ params }) =>
            HttpResponse.json(createTaskStartWorkflowVersions(String(params.key))),
        ),
        http.post("*/tasks/start", async ({ request }) => {
            await onStart?.(request);
            return startResponse ?? HttpResponse.json(createTaskStartResponse());
        }),
    );
}
