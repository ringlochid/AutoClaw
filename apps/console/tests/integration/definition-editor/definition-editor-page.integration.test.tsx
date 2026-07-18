import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "../../../src/api/generated/openapi";
import { DefinitionEditorPage } from "../../../src/features/definition-editor/DefinitionEditorPage";
import { TEST_API_BASE_URL, createOperationFailureBody } from "../../fixtures/console-api";
import { installTestConsoleConfig } from "../../fixtures/console-config";
import {
    DEFINITION_EDITOR_NEW_DRAFT_KEY,
    DEFINITION_EDITOR_ROLE_KEY,
    DEFINITION_EDITOR_UPDATED_BODY,
    DEFINITION_EDITOR_WORKFLOW_KEY,
    bodyForKind,
    createCleanDefinitionEditorDraft,
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
    installTestConsoleConfig();
});

afterEach(() => {
    cleanup();
    server.resetHandlers();
    installTestConsoleConfig();
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
                        createOperationFailureBody({
                            code: "name_collision",
                            field_path: "key",
                            retryable: false,
                            suggested_next_step: "Choose a different definition key.",
                            summary: "A stored role already owns this key.",
                        }),
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

    it("confirms reset, replace, and discard as separate saved draft actions", async () => {
        const user = userEvent.setup();
        const baselineBody = bodyForKind("workflow", DEFINITION_EDITOR_WORKFLOW_KEY).replace(
            "Deliver the Definition Editor authoring surface.",
            "Captured stored baseline for reset.",
        );
        const replacedBody = bodyForKind("workflow", DEFINITION_EDITOR_WORKFLOW_KEY).replace(
            "Deliver the Definition Editor authoring surface.",
            "Current stored truth after replace.",
        );
        let deletedCount = 0;
        let replacedCount = 0;
        let resetBody = "";

        installDefinitionEditorHandlers({
            detail: createDefinitionEditorDraftDetail({
                baseline_body: baselineBody,
                body: DEFINITION_EDITOR_UPDATED_BODY,
                status: "modified",
            }),
            onDelete: () => {
                deletedCount += 1;
            },
            onReplaceCurrent: () => {
                replacedCount += 1;
                return createDefinitionEditorDraftResponse(
                    createDefinitionEditorDraftDetail({
                        based_on: {
                            content_hash: "sha256:current-replace",
                            revision_no: 13,
                            source_path: null,
                        },
                        baseline_body: replacedBody,
                        body: replacedBody,
                        content_hash: "sha256:current-replace",
                        status: "clean",
                    }),
                );
            },
            onWrite: async (request) => {
                const body =
                    (await request.json()) as components["schemas"]["DefinitionDraftWriteRequest"];
                resetBody = body.body;
                return createDefinitionEditorDraftResponse(
                    createDefinitionEditorDraftDetail({
                        baseline_body: baselineBody,
                        body: body.body,
                        status: body.body === baselineBody ? "clean" : "modified",
                    }),
                );
            },
        });

        renderDefinitionEditorPage();
        expect(await screen.findByLabelText("Draft body")).toHaveValue(
            DEFINITION_EDITOR_UPDATED_BODY,
        );

        await user.click(screen.getByRole("button", { name: "Reset draft" }));
        const resetDialog = await screen.findByRole("dialog", { name: "Reset draft" });
        expect(
            within(resetDialog).getByText(
                /restores the selected file to its captured draft baseline/i,
            ),
        ).toBeVisible();
        await user.click(within(resetDialog).getByRole("button", { name: "Reset draft" }));
        await waitFor(() => {
            expect(screen.queryByRole("dialog", { name: "Reset draft" })).not.toBeInTheDocument();
        });
        expect(resetBody).toBe(baselineBody);
        expect(deletedCount).toBe(0);
        expect(replacedCount).toBe(0);
        expect(screen.getByLabelText("Draft body")).toHaveValue(baselineBody);

        await user.click(
            screen.getByRole("button", { name: "Replace with current stored revision" }),
        );
        const replaceDialog = await screen.findByRole("dialog", {
            name: "Replace with current stored revision",
        });
        expect(
            within(replaceDialog).getByText(/reads the current stored registry revision/i),
        ).toBeVisible();
        await user.click(within(replaceDialog).getByRole("button", { name: "Replace draft" }));
        await waitFor(() => {
            expect(
                screen.queryByRole("dialog", { name: "Replace with current stored revision" }),
            ).not.toBeInTheDocument();
        });
        expect(deletedCount).toBe(0);
        expect(replacedCount).toBe(1);
        expect(screen.getByLabelText("Draft body")).toHaveValue(replacedBody);

        await user.click(screen.getByRole("button", { name: "Discard saved draft" }));
        const discardDialog = await screen.findByRole("dialog", {
            name: "Discard saved draft",
        });
        expect(
            within(discardDialog).getByText(/permanently removes the saved draft file/i),
        ).toBeVisible();
        await user.click(
            within(discardDialog).getByRole("button", { name: "Discard saved draft" }),
        );
        await waitFor(() => {
            expect(
                screen.queryByRole("dialog", { name: "Discard saved draft" }),
            ).not.toBeInTheDocument();
        });
        expect(deletedCount).toBe(1);
        expect(replacedCount).toBe(1);
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

    it("shows local-admission failures on the flat draft list", async () => {
        server.use(
            http.get("*/authoring/definition-drafts", () =>
                HttpResponse.json(
                    createOperationFailureBody({
                        code: "local_admission_denied",
                        retryable: false,
                        summary: "The request was not admitted by the loopback control plane.",
                    }),
                    { status: 403 },
                ),
            ),
        );

        renderDefinitionEditorPage();
        expect(await screen.findByText("Access to drafts failed")).toBeVisible();
        expect(
            screen.getByText("The request was not admitted by the loopback control plane."),
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
    onDelete,
    onReplaceCurrent,
    onWrite,
    publishResponse = createDefinitionEditorPublish("published"),
    validationResponse = createDefinitionEditorValidation("valid"),
}: {
    readonly detail?: components["schemas"]["DefinitionDraftDetail"];
    readonly list?: components["schemas"]["DefinitionDraftListResponse"];
    readonly onCreate?: (request: Request) => Promise<Response>;
    readonly onDelete?: () => void;
    readonly onReplaceCurrent?: () => components["schemas"]["DefinitionDraftDetailResponse"];
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
        http.post("*/authoring/definitions/:kind/:key/draft/replace-current", () => {
            if (onReplaceCurrent !== undefined) {
                return HttpResponse.json(onReplaceCurrent());
            }
            return HttpResponse.json(
                createDefinitionEditorDraftResponse(
                    createDefinitionEditorDraftDetail({ status: "clean" }),
                ),
            );
        }),
        http.delete("*/authoring/definitions/:kind/:key/draft", () => {
            onDelete?.();
            return new HttpResponse(null, { status: 204 });
        }),
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
