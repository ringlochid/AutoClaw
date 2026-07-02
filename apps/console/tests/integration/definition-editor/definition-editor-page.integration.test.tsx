import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "../../../src/api/generated/openapi";
import { DefinitionEditorPage } from "../../../src/features/definition-editor/DefinitionEditorPage";
import { TEST_API_BASE_URL, TEST_API_KEY } from "../../fixtures/console-api";
import { installTestConsoleConfig } from "../../fixtures/console-config";
import {
    DEFINITION_EDITOR_NEW_DRAFT_KEY,
    DEFINITION_EDITOR_ROLE_KEY,
    DEFINITION_EDITOR_UPDATED_BODY,
    DEFINITION_EDITOR_WORKFLOW_KEY,
    bodyForKind,
    createCleanDefinitionEditorDraft,
    createDefinitionEditorAuthFailure,
    createDefinitionEditorDraftDetail,
    createDefinitionEditorDraftList,
    createDefinitionEditorDraftResponse,
    createDefinitionEditorPublish,
    createDefinitionEditorValidation,
    createNewRoleDraft,
    createUnsavedCurrentDefinitionDraft,
} from "../../fixtures/definition-editor";

const server = setupServer();

beforeAll(() => {
    server.listen({ onUnhandledRequest: "error" });
});

beforeEach(() => {
    vi.stubEnv("VITE_AUTOCLAW_API_BASE_URL", TEST_API_BASE_URL);
    vi.stubEnv("VITE_AUTOCLAW_API_KEY", TEST_API_KEY);
    installTestConsoleConfig();
});

afterEach(() => {
    cleanup();
    server.resetHandlers();
    installTestConsoleConfig(null);
    vi.unstubAllEnvs();
});

afterAll(() => {
    server.close();
});

describe("DefinitionEditorPage", () => {
    it("loads one flat saved draft, saves before validate, and publishes one revision", async () => {
        const user = userEvent.setup();
        let savedBody = "";
        installDefinitionEditorHandlers({
            onWrite: async (request) => {
                const body =
                    (await request.json()) as components["schemas"]["DefinitionDraftWriteRequest"];
                savedBody = body.body;
                return createDefinitionEditorDraftResponse(
                    createCleanDefinitionEditorDraft(body.body),
                );
            },
        });

        renderDefinitionEditorPage();

        expect(await screen.findByRole("heading", { name: "Definition Editor" })).toBeVisible();
        expect(
            await screen.findByRole("button", { name: new RegExp(DEFINITION_EDITOR_WORKFLOW_KEY) }),
        ).toBeVisible();
        expect(await screen.findByLabelText("Draft body")).toHaveValue(
            bodyForKind("workflow", DEFINITION_EDITOR_WORKFLOW_KEY),
        );

        await user.clear(screen.getByLabelText("Draft body"));
        await user.type(screen.getByLabelText("Draft body"), DEFINITION_EDITOR_UPDATED_BODY);
        expect(screen.getByText("local edits")).toBeVisible();
        await user.click(screen.getByRole("button", { name: "Validate" }));

        expect(savedBody).toBe(DEFINITION_EDITOR_UPDATED_BODY);
        const validationDialog = await screen.findByRole("dialog", { name: "Validation valid" });
        expect(within(validationDialog).getByText("No validation issues returned.")).toBeVisible();
        await user.click(within(validationDialog).getByRole("button", { name: /^Close$/ }));
        await waitFor(() => {
            expect(
                screen.queryByRole("dialog", { name: "Validation valid" }),
            ).not.toBeInTheDocument();
        });

        await user.click(screen.getByRole("button", { name: "Publish" }));
        const publishDialog = await screen.findByRole("dialog", { name: "Publish published" });
        expect(
            within(publishDialog).getByText(/Workflow definition-editor-page revision 14/),
        ).toBeVisible();
    });

    it("creates flat definition drafts and keeps name collisions in the dialog", async () => {
        const user = userEvent.setup();
        installDefinitionEditorHandlers({
            onCreate: async (request) => {
                const body =
                    (await request.json()) as components["schemas"]["DefinitionDraftCreateRequest"];
                if (body.key === DEFINITION_EDITOR_ROLE_KEY) {
                    return HttpResponse.json(
                        {
                            detail: {
                                code: "name_collision",
                                field_path: "key",
                                ok: false,
                                retryable: false,
                                suggested_next_step: "Choose a different definition key.",
                                summary: "A stored role already owns this key.",
                            },
                        },
                        { status: 409 },
                    );
                }
                return HttpResponse.json(createDefinitionEditorDraftResponse(createNewRoleDraft()));
            },
        });

        renderDefinitionEditorPage();
        await screen.findByRole("button", { name: new RegExp(DEFINITION_EDITOR_WORKFLOW_KEY) });

        await user.click(screen.getAllByRole("button", { name: "New draft" })[0]);
        const dialog = await screen.findByRole("dialog", { name: "New draft" });
        await user.type(within(dialog).getByLabelText("Key"), DEFINITION_EDITOR_ROLE_KEY);
        await user.click(within(dialog).getByRole("button", { name: "Create draft" }));
        expect(
            await within(dialog).findByText("A stored role already owns this key."),
        ).toBeVisible();

        await user.clear(within(dialog).getByLabelText("Key"));
        await user.type(within(dialog).getByLabelText("Key"), DEFINITION_EDITOR_NEW_DRAFT_KEY);
        await user.click(within(dialog).getByRole("button", { name: "Create draft" }));

        expect(
            await screen.findByRole("button", {
                name: new RegExp(DEFINITION_EDITOR_NEW_DRAFT_KEY),
            }),
        ).toBeVisible();
        expect(screen.getByDisplayValue(new RegExp(DEFINITION_EDITOR_NEW_DRAFT_KEY))).toBeVisible();
    });

    it("opens a current stored definition from query params and saves it as an update draft", async () => {
        const user = userEvent.setup();
        const currentDraft = createUnsavedCurrentDefinitionDraft("from-definitions-link");
        installDefinitionEditorHandlers({
            detail: currentDraft,
            list: createDefinitionEditorDraftList(createDefinitionEditorDraftDetail()),
        });

        renderDefinitionEditorPage("/definitions/editor?kind=workflow&key=from-definitions-link");
        expect(await screen.findByDisplayValue(/from-definitions-link/)).toBeVisible();
        expect(screen.getAllByText("Update").length).toBeGreaterThan(0);

        await user.type(screen.getByLabelText("Draft body"), "\n# saved from link");
        await user.click(screen.getByRole("button", { name: "Save draft" }));
        await waitFor(() => {
            expect(screen.queryByText("local edits")).not.toBeInTheDocument();
        });
    });

    it("uses Tab and Shift+Tab for draft body indentation without leaving the editor", async () => {
        const user = userEvent.setup();
        installDefinitionEditorHandlers();

        renderDefinitionEditorPage();
        const editorElement = await screen.findByLabelText("Draft body");
        expect(editorElement).toBeInstanceOf(HTMLTextAreaElement);
        const editor = editorElement as HTMLTextAreaElement;
        await user.clear(editor);
        await user.type(editor, "root:\nchild: value");
        editor.setSelectionRange("root:\n".length, "root:\nchild".length);

        await user.keyboard("{Tab}");
        expect(editor).toHaveFocus();
        expect(editor).toHaveValue("root:\n  child: value");

        editor.setSelectionRange("root:\n".length, "root:\n  child".length);
        await user.keyboard("{Shift>}{Tab}{/Shift}");
        expect(editor).toHaveFocus();
        expect(editor).toHaveValue("root:\nchild: value");
    });

    it("shows API-key failures on the flat draft list", async () => {
        server.use(
            http.get("*/authoring/definition-drafts", () =>
                HttpResponse.json(createDefinitionEditorAuthFailure(), { status: 401 }),
            ),
        );

        renderDefinitionEditorPage();
        expect(await screen.findByText("Access to drafts failed")).toBeVisible();
        expect(
            screen.getByText("Definition authoring requires an operator API key."),
        ).toBeVisible();
    });
});

function renderDefinitionEditorPage(initialEntry = "/definitions/editor") {
    render(
        <MemoryRouter initialEntries={[initialEntry]}>
            <Routes>
                <Route element={<DefinitionEditorPage />} path="/definitions/editor" />
            </Routes>
        </MemoryRouter>,
    );
}

function installDefinitionEditorHandlers({
    detail = createDefinitionEditorDraftDetail(),
    list,
    onCreate,
    onWrite,
    publishResponse = createDefinitionEditorPublish("published"),
    validationResponse = createDefinitionEditorValidation("valid"),
}: {
    readonly detail?: components["schemas"]["DefinitionDraftDetail"];
    readonly list?: components["schemas"]["DefinitionDraftListResponse"];
    readonly onCreate?: (request: Request) => Promise<Response>;
    readonly onWrite?: (
        request: Request,
    ) => Promise<components["schemas"]["DefinitionDraftDetailResponse"]>;
    readonly publishResponse?: components["schemas"]["DefinitionDraftPublishResponse"];
    readonly validationResponse?: components["schemas"]["DefinitionDraftValidationResponse"];
} = {}) {
    server.use(
        http.get("*/authoring/definition-drafts", () =>
            HttpResponse.json(list ?? createDefinitionEditorDraftList(detail)),
        ),
        http.post("*/authoring/definition-drafts", async ({ request }) => {
            if (onCreate !== undefined) {
                return onCreate(request);
            }
            return HttpResponse.json(createDefinitionEditorDraftResponse(createNewRoleDraft()));
        }),
        http.get("*/authoring/definitions/:kind/:key/draft", ({ params }) =>
            HttpResponse.json(
                createDefinitionEditorDraftResponse(
                    createDraftForPath(detail, String(params.kind), String(params.key)),
                ),
            ),
        ),
        http.put("*/authoring/definitions/:kind/:key/draft", async ({ params, request }) => {
            if (onWrite !== undefined) {
                return HttpResponse.json(await onWrite(request));
            }
            const body =
                (await request.json()) as components["schemas"]["DefinitionDraftWriteRequest"];
            return HttpResponse.json(
                createDefinitionEditorDraftResponse(
                    createCleanDefinitionEditorDraft(body.body).kind === detail.kind
                        ? createCleanDefinitionEditorDraft(body.body)
                        : createDefinitionEditorDraftDetail({
                              body: body.body,
                              is_saved: true,
                              key: String(params.key),
                              kind: params.kind as components["schemas"]["DefinitionKind"],
                              status: "clean",
                          }),
                ),
            );
        }),
        http.delete(
            "*/authoring/definitions/:kind/:key/draft",
            () => new HttpResponse(null, { status: 204 }),
        ),
        http.post("*/authoring/definitions/:kind/:key/draft/validate", () =>
            HttpResponse.json(validationResponse),
        ),
        http.post("*/authoring/definitions/:kind/:key/draft/publish", () =>
            HttpResponse.json(publishResponse),
        ),
    );
}

function createDraftForPath(
    baseDraft: components["schemas"]["DefinitionDraftDetail"],
    kind: string,
    key: string,
): components["schemas"]["DefinitionDraftDetail"] {
    if (kind !== "role" && kind !== "policy" && kind !== "workflow") {
        return baseDraft;
    }
    if (baseDraft.kind === kind && baseDraft.key === key) {
        return baseDraft;
    }
    return createDefinitionEditorDraftDetail({
        body: bodyForKind(kind, key),
        is_saved: false,
        key,
        kind,
        mode: "update",
        status: "clean",
    });
}
