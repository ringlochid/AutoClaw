import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "../../../src/api/generated/openapi";
import { DefinitionsPage } from "../../../src/features/definitions/DefinitionsPage";
import {
    createBackendOperationFailureBody,
    TEST_API_BASE_URL,
    TEST_API_KEY,
} from "../../fixtures/console-api";
import {
    POLICY_KEY,
    ROLE_KEY,
    WORKFLOW_KEY,
    createDefinitionDetailMap,
    createDefinitionSummaryList,
    createDefinitionVersions,
    createDefinitionVersionsMap,
    createPolicyDefinitionRows,
    createRoleDefinitionRows,
    createWorkflowDefinitionRows,
} from "../../fixtures/definitions";

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

describe("DefinitionsPage", () => {
    it("uses kind-scoped routes, filters, cursor loading, detail, and compact versions", async () => {
        const user = userEvent.setup();
        const seenRequests: URL[] = [];
        installDefinitionsHandlers(seenRequests);

        renderDefinitionsPage();

        expect((await screen.findAllByText("planning_lead")).length).toBeGreaterThan(0);
        expect(
            screen.getAllByText("Parent/root coordinator for one owned subtree.").length,
        ).toBeGreaterThan(0);
        expect(seenRequests[0]?.pathname).toBe("/definitions/roles");
        expect(seenRequests[0]?.searchParams.get("limit")).toBe("25");
        expect(seenRequests[0]?.searchParams.get("sort")).toBe("updated_at_desc");

        await user.selectOptions(screen.getByLabelText("Allowed node kind"), "worker");
        await waitFor(() => {
            expect(
                lastPathRequest(seenRequests, "/definitions/roles")?.searchParams.get(
                    "allowed_node_kind",
                ),
            ).toBe("worker");
        });

        await user.type(screen.getByLabelText("Search"), "frontend");
        await waitFor(() => {
            expect(hasRequestParam(seenRequests, "/definitions/roles", "q", "frontend")).toBe(true);
        });

        await user.selectOptions(screen.getByLabelText("Sort"), "key_asc");
        await waitFor(() => {
            expect(hasRequestParam(seenRequests, "/definitions/roles", "sort", "key_asc")).toBe(
                true,
            );
        });

        await user.click(screen.getByRole("button", { name: "Load more" }));
        expect((await screen.findAllByText("release_operator")).length).toBeGreaterThan(0);
        expect(
            lastPathRequest(seenRequests, "/definitions/roles")?.searchParams.get("cursor"),
        ).toBe("roles-page-2");

        await user.click(screen.getByText("Versions"));
        const versionsList = within(screen.getByRole("list", { name: "Definition versions" }));
        expect(versionsList.getByText("Revision 4")).toBeVisible();
        expect(versionsList.getByText("Revision 3")).toBeVisible();
        expect(screen.getAllByText("Recorded by: Not reported").length).toBeGreaterThan(0);

        await user.click(screen.getByRole("button", { name: "Policies" }));
        expect((await screen.findAllByText(POLICY_KEY)).length).toBeGreaterThan(0);
        expect(screen.getByLabelText("Applies to")).toBeVisible();
        expect(screen.queryByLabelText("Allowed node kind")).not.toBeInTheDocument();
        expect(screen.getByText(/child assignment limit not reported; 2 retries/)).toBeVisible();

        await user.selectOptions(screen.getByLabelText("Applies to"), "worker");
        await waitFor(() => {
            expect(
                lastPathRequest(seenRequests, "/definitions/policies")?.searchParams.get(
                    "applies_to",
                ),
            ).toBe("worker");
        });

        await user.click(screen.getByRole("button", { name: "Workflows" }));
        expect((await screen.findAllByText(WORKFLOW_KEY)).length).toBeGreaterThan(0);
        expect(screen.queryByLabelText("Allowed node kind")).not.toBeInTheDocument();
        expect(screen.queryByLabelText("Applies to")).not.toBeInTheDocument();
        const workflowRequest = lastPathRequest(seenRequests, "/definitions/workflows");
        expect(workflowRequest?.searchParams.get("allowed_node_kind")).toBeNull();
        expect(workflowRequest?.searchParams.get("applies_to")).toBeNull();
        expect(await screen.findByText("implement_frontend_scope")).toBeVisible();
        expect(screen.getByRole("link", { name: "Task Start" })).toHaveAttribute(
            "href",
            "/task-start",
        );
    });

    it("renders empty, no-results, stale-selection, detail-error, and history-error states", async () => {
        const user = userEvent.setup();
        const seenRequests: URL[] = [];
        const roleRows = createRoleDefinitionRows();
        server.use(
            http.get("*/definitions/roles", ({ request }) => {
                const requestUrl = new URL(request.url);
                seenRequests.push(requestUrl);
                if (requestUrl.searchParams.get("q") === "missing") {
                    return HttpResponse.json(createDefinitionSummaryList("role", [], null));
                }
                return HttpResponse.json(createDefinitionSummaryList("role", roleRows, null));
            }),
            http.get("*/definitions/:kind/:key/versions", () =>
                HttpResponse.json(createDefinitionVersions("role", ROLE_KEY)),
            ),
            http.get("*/definitions/:kind/:key", () =>
                HttpResponse.text("Detail read failed.", { status: 500 }),
            ),
        );

        renderDefinitionsPage();

        expect(await screen.findByText("Definition detail could not load")).toBeVisible();

        cleanup();
        server.resetHandlers();
        server.use(
            http.get("*/definitions/roles", ({ request }) => {
                const requestUrl = new URL(request.url);
                seenRequests.push(requestUrl);
                if (requestUrl.searchParams.get("q") === "missing") {
                    return HttpResponse.json(createDefinitionSummaryList("role", [], null));
                }
                return HttpResponse.json(createDefinitionSummaryList("role", roleRows, null));
            }),
            http.get("*/definitions/:kind/:key/versions", () =>
                HttpResponse.text("History read failed.", { status: 500 }),
            ),
            http.get("*/definitions/:kind/:key", () =>
                HttpResponse.json(createDefinitionDetailMap()[`role:${ROLE_KEY}`]),
            ),
        );

        renderDefinitionsPage();
        expect((await screen.findAllByText("planning_lead")).length).toBeGreaterThan(0);
        expect(await screen.findByText(/Coordinate only the current owned subtree/)).toBeVisible();
        await user.click(screen.getByText("Versions"));
        expect(await screen.findByText("Version history could not load")).toBeVisible();

        await user.type(screen.getByLabelText("Search"), "missing");
        expect(await screen.findByText("No matching roles")).toBeVisible();
        expect(await screen.findByText("Selected definition is stale")).toBeVisible();
        expect(hasRequestParam(seenRequests, "/definitions/roles", "q", "missing")).toBe(true);
    });

    it("renders empty, auth, and single-revision history states honestly", async () => {
        const user = userEvent.setup();
        server.use(
            http.get("*/definitions/roles", () =>
                HttpResponse.json(createDefinitionSummaryList("role", [], null)),
            ),
        );

        const { unmount } = renderDefinitionsPage();
        expect((await screen.findAllByText("No stored roles")).length).toBeGreaterThan(0);

        unmount();
        cleanup();
        server.resetHandlers();
        server.use(
            http.get("*/definitions/roles", () =>
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
        );

        renderDefinitionsPage();
        expect(await screen.findByText("Access to Definitions failed")).toBeVisible();
        expect(screen.getByText("The AutoClaw API key is missing or invalid.")).toBeVisible();

        cleanup();
        server.resetHandlers();
        installDefinitionsHandlers([]);
        renderDefinitionsPage();
        expect((await screen.findAllByText(ROLE_KEY)).length).toBeGreaterThan(0);
        await user.click(screen.getByRole("button", { name: /frontend_engineer/ }));
        expect(
            await screen.findByText(/Implement only the current meaningful frontend scope/),
        ).toBeVisible();
        await user.click(screen.getByText("Versions"));
        expect(await screen.findByText("Single current revision recorded.")).toBeVisible();
        const singleRevisionVersions = within(
            screen.getByRole("list", { name: "Definition versions" }),
        );
        expect(singleRevisionVersions.getByText("Revision 3")).toBeVisible();
    });
});

function renderDefinitionsPage() {
    return render(
        <MemoryRouter initialEntries={["/definitions"]}>
            <Routes>
                <Route element={<DefinitionsPage />} path="/definitions" />
                <Route element={<div>Definition Editor target</div>} path="/definitions/editor" />
                <Route element={<div>Task Start target</div>} path="/task-start" />
            </Routes>
        </MemoryRouter>,
    );
}

function installDefinitionsHandlers(seenRequests: URL[]): void {
    const details = createDefinitionDetailMap();
    const versions = createDefinitionVersionsMap();
    server.use(
        http.get("*/definitions/roles", ({ request }) => {
            const requestUrl = new URL(request.url);
            seenRequests.push(requestUrl);
            if (requestUrl.searchParams.get("cursor") === "roles-page-2") {
                return HttpResponse.json(
                    createDefinitionSummaryList(
                        "role",
                        [
                            {
                                allowed_node_kinds: ["worker"],
                                applies_to: null,
                                budget_spec: null,
                                current_revision_no: 1,
                                description: "Ordinary bounded release worker.",
                                key: "release_operator",
                                labels: ["authoring"],
                                title: "release_operator",
                                updated_at: "2026-06-29T12:00:00Z",
                            },
                        ],
                        null,
                    ),
                );
            }

            return HttpResponse.json(
                createDefinitionSummaryList("role", createRoleDefinitionRows(), "roles-page-2"),
            );
        }),
        http.get("*/definitions/policies", ({ request }) => {
            const requestUrl = new URL(request.url);
            seenRequests.push(requestUrl);
            return HttpResponse.json(
                createDefinitionSummaryList("policy", createPolicyDefinitionRows(), null),
            );
        }),
        http.get("*/definitions/workflows", ({ request }) => {
            const requestUrl = new URL(request.url);
            seenRequests.push(requestUrl);
            return HttpResponse.json(
                createDefinitionSummaryList("workflow", createWorkflowDefinitionRows(), null),
            );
        }),
        http.get("*/definitions/:kind/:key/versions", ({ params }) => {
            const lookupKey = `${String(params.kind)}:${String(params.key)}`;
            return HttpResponse.json(
                versions[lookupKey] ??
                    createDefinitionVersions(
                        String(params.kind) as components["schemas"]["DefinitionKind"],
                        String(params.key),
                    ),
            );
        }),
        http.get("*/definitions/:kind/:key", ({ params }) => {
            const lookupKey = `${String(params.kind)}:${String(params.key)}`;
            return HttpResponse.json(details[lookupKey] ?? details[`role:${ROLE_KEY}`]);
        }),
    );
}

function lastPathRequest(requests: readonly URL[], pathname: string): URL | null {
    return requests.filter((requestUrl) => requestUrl.pathname === pathname).at(-1) ?? null;
}

function hasRequestParam(
    requests: readonly URL[],
    pathname: string,
    name: string,
    value: string,
): boolean {
    return requests.some(
        (requestUrl) =>
            requestUrl.pathname === pathname && requestUrl.searchParams.get(name) === value,
    );
}
