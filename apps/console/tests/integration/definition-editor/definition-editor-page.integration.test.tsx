import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "../../../src/api/generated/openapi";
import { DefinitionEditorPage } from "../../../src/features/definition-editor/DefinitionEditorPage";
import {
    DEFINITION_EDITOR_MATERIALIZED_KEY,
    DEFINITION_EDITOR_NEW_DRAFT_KEY,
    DEFINITION_EDITOR_ROLE_KEY,
    DEFINITION_EDITOR_UPDATED_BODY,
    DEFINITION_EDITOR_WORKFLOW_KEY,
    createCleanSavedDefinitionEditorDraftSet,
    createDefinitionEditorApply,
    createDefinitionEditorAuthFailure,
    createDefinitionEditorDraftFile,
    createDefinitionEditorDraftSetDetail,
    createDefinitionEditorDraftSetList,
    createDefinitionEditorDraftSetResponse,
    createDefinitionEditorPreview,
    createDefinitionEditorValidation,
    createMaterializedDraftSet,
    createNewDraftAddedSet,
    createRematerializedDefinitionEditorDraftSet,
    createResetDefinitionEditorDraftSet,
} from "../../fixtures/definition-editor";
import { TEST_API_BASE_URL, TEST_API_KEY } from "../../fixtures/console-api";

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

describe("DefinitionEditorPage", () => {
    it("loads a draft set, preserves mode while switching files, and keeps draft/preview truth separate", async () => {
        installDefinitionEditorHandlers();

        renderDefinitionEditorPage();

        expect(await screen.findByRole("heading", { name: "Definition Editor" })).toBeVisible();
        expect(
            await screen.findByRole("button", { name: new RegExp(DEFINITION_EDITOR_WORKFLOW_KEY) }),
        ).toBeVisible();
        expect(screen.getAllByText("Draft set").length).toBeGreaterThan(0);
        expect(screen.getAllByText("workflow").length).toBeGreaterThan(0);
        expect(screen.getAllByText("dirty").length).toBeGreaterThan(0);
        expect(screen.getByDisplayValue(new RegExp(DEFINITION_EDITOR_WORKFLOW_KEY))).toBeVisible();

        await userEvent.click(screen.getByRole("button", { name: "Preview" }));
        expect(await screen.findAllByText("Draft truth")).toHaveLength(2);
        await userEvent.click(
            within(screen.getByLabelText("Preview provenance")).getByRole("button", {
                name: "Stored truth",
            }),
        );
        expect(screen.getByText("Captured rev 12")).toBeVisible();
        await userEvent.click(screen.getByRole("button", { name: "Validate" }));
        expect(await screen.findByText("Validation Valid")).toBeVisible();
        await userEvent.click(
            screen.getByRole("button", { name: new RegExp(DEFINITION_EDITOR_ROLE_KEY) }),
        );
        expect(screen.getByText("Validation Valid")).toBeVisible();
        await userEvent.click(screen.getByRole("button", { name: "Edit" }));
        expect(screen.getByDisplayValue(new RegExp(DEFINITION_EDITOR_ROLE_KEY))).toBeVisible();
    });

    it("creates starter drafts and materializes stored definitions through authoring routes", async () => {
        const user = userEvent.setup();
        let writtenBody = "";
        installDefinitionEditorHandlers({
            onWrite: async (request, key) => {
                const body =
                    (await request.json()) as components["schemas"]["DefinitionDraftFileWriteRequest"];
                writtenBody = body.body;
                if (key === DEFINITION_EDITOR_NEW_DRAFT_KEY) {
                    return createDefinitionEditorDraftSetResponse(
                        createNewDraftAddedSet(body.body),
                    );
                }
                return createDefinitionEditorDraftSetResponse();
            },
        });

        renderDefinitionEditorPage();
        expect(
            await screen.findByRole("button", { name: new RegExp(DEFINITION_EDITOR_WORKFLOW_KEY) }),
        ).toBeVisible();

        await user.click(screen.getByRole("button", { name: "New draft" }));
        await user.type(screen.getByLabelText("Draft key"), DEFINITION_EDITOR_NEW_DRAFT_KEY);
        await user.clear(screen.getByLabelText("Description"));
        await user.type(screen.getByLabelText("Description"), "Review the editor page.");
        await user.click(screen.getByRole("button", { name: "Create draft" }));

        expect(
            await screen.findByRole("button", {
                name: new RegExp(DEFINITION_EDITOR_NEW_DRAFT_KEY),
            }),
        ).toBeVisible();
        expect(writtenBody).toContain("allowed_node_kinds");
        expect(screen.getByDisplayValue(new RegExp(DEFINITION_EDITOR_NEW_DRAFT_KEY))).toBeVisible();

        cleanup();
        server.resetHandlers();
        let createdDraftMaterialize:
            components["schemas"]["DefinitionDraftSetCreateRequest"]["materialize"] | undefined;
        installDefinitionEditorHandlers({
            onCreateDraftSet: async (request) => {
                const body =
                    (await request.json()) as components["schemas"]["DefinitionDraftSetCreateRequest"];
                createdDraftMaterialize = body.materialize;
                return createDefinitionEditorDraftSetResponse(createMaterializedDraftSet());
            },
        });

        renderDefinitionEditorPage(
            `/definitions/editor?materialize_kind=workflow&materialize_key=${DEFINITION_EDITOR_MATERIALIZED_KEY}`,
        );
        expect(
            await screen.findByRole("button", {
                name: new RegExp(DEFINITION_EDITOR_MATERIALIZED_KEY),
            }),
        ).toBeVisible();
        expect(createdDraftMaterialize).toEqual([
            { key: DEFINITION_EDITOR_MATERIALIZED_KEY, kind: "workflow" },
        ]);
    });

    it("saves dirty drafts, resets to captured baseline, and replaces from current stored revision separately", async () => {
        const user = userEvent.setup();
        installDefinitionEditorHandlers({
            onWrite: () =>
                Promise.resolve(
                    createDefinitionEditorDraftSetResponse(
                        createCleanSavedDefinitionEditorDraftSet(DEFINITION_EDITOR_UPDATED_BODY),
                    ),
                ),
        });

        renderDefinitionEditorPage();
        const editor = await screen.findByLabelText("Editable draft body");
        const saveButton = screen.getByRole("button", { name: "Save draft" });
        expect(saveButton).toBeVisible();
        expect(saveButton).toBeDisabled();

        await user.clear(editor);
        await user.type(editor, DEFINITION_EDITOR_UPDATED_BODY);
        expect(screen.getByText("local edits")).toBeVisible();
        expect(saveButton).toBeEnabled();

        await user.click(saveButton);
        await waitFor(() => {
            expect(screen.getByLabelText("Editable draft body")).toHaveValue(
                DEFINITION_EDITOR_UPDATED_BODY,
            );
        });
        expect(screen.getAllByText("clean").length).toBeGreaterThan(0);
        expect(saveButton).toBeDisabled();

        await user.type(screen.getByLabelText("Editable draft body"), "\nlocal change");
        await user.click(screen.getByRole("button", { name: "Reset draft" }));
        expect(await screen.findByRole("dialog", { name: "Reset draft" })).toBeVisible();
        await user.click(
            within(screen.getByRole("dialog")).getByRole("button", { name: "Reset draft" }),
        );
        await waitFor(() => {
            expect(screen.getByDisplayValue(/Captured stored baseline/)).toBeVisible();
        });

        await user.click(
            screen.getByRole("button", { name: "Replace with current stored revision" }),
        );
        expect(
            await screen.findByRole("dialog", { name: "Replace with current stored revision" }),
        ).toBeVisible();
        await user.click(
            within(screen.getByRole("dialog")).getByRole("button", { name: "Replace draft" }),
        );
        await waitFor(() => {
            expect(screen.getByDisplayValue(/Current stored revision body/)).toBeVisible();
        });
    });

    it("shows validation, stale validation, preview, no-op apply, published apply, and auth failures", async () => {
        const user = userEvent.setup();
        let applyCount = 0;
        installDefinitionEditorHandlers({
            onApply: () => {
                applyCount += 1;
                return createDefinitionEditorApply(applyCount === 1 ? "no_op" : "published");
            },
            previewResponse: createDefinitionEditorPreview("invalid"),
            validationResponse: createDefinitionEditorValidation("invalid"),
        });

        renderDefinitionEditorPage();
        expect(
            await screen.findByRole("button", { name: new RegExp(DEFINITION_EDITOR_WORKFLOW_KEY) }),
        ).toBeVisible();

        await user.click(screen.getByRole("button", { name: "Validate" }));
        expect(await screen.findByText("Validation Invalid")).toBeVisible();
        expect(screen.getByText("Workflow root.role is required.")).toBeVisible();
        expect(screen.getByText("missing_role_reference")).toBeVisible();
        expect(screen.getByText("preview_review_recommended")).toBeVisible();

        await user.click(screen.getByRole("button", { name: "Edit" }));
        await user.type(screen.getByLabelText("Editable draft body"), "\nchanged after validation");
        await user.click(screen.getByRole("button", { name: "Validate" }));
        expect(screen.getByText("Validation result is stale")).toBeVisible();

        await user.click(screen.getByRole("button", { name: "Preview" }));
        await user.click(screen.getByRole("button", { name: "Run preview" }));
        expect(await screen.findByText("Preview invalid")).toBeVisible();
        expect(
            screen.getByText("Preview task-compose input does not match the draft set."),
        ).toBeVisible();
        await user.click(screen.getByRole("button", { name: "Stored truth" }));
        expect(screen.getByText("Captured rev 12")).toBeVisible();

        await user.click(screen.getByRole("button", { name: "Apply" }));
        const noOpApplyDialog = await screen.findByRole("dialog", {
            name: "Apply completed with no new revision",
        });
        expect(
            within(noOpApplyDialog).getByText("No published revisions were returned."),
        ).toBeVisible();
        await user.click(within(noOpApplyDialog).getByRole("button", { name: "Close" }));
        await waitFor(() => {
            expect(
                screen.queryByRole("dialog", {
                    name: "Apply completed with no new revision",
                }),
            ).not.toBeInTheDocument();
        });

        await user.click(screen.getByRole("button", { name: "Apply" }));
        const publishedApplyDialog = await screen.findByRole("dialog", {
            name: "Apply published new current revisions",
        });
        expect(
            within(publishedApplyDialog).getByText(/workflow\/definition-editor-page revision 14/),
        ).toBeVisible();

        cleanup();
        server.resetHandlers();
        installDefinitionEditorHandlers({ listAuthFailure: true });
        renderDefinitionEditorPage();
        expect(await screen.findByText("Access to draft sets failed")).toBeVisible();
        expect(
            screen.getByText("Definition authoring requires an operator API key."),
        ).toBeVisible();
    });

    it("does not show previous draft truth while a switched draft-set detail is pending or failed", async () => {
        const user = userEvent.setup();
        const failedDraftSetId = "draft-set-detail-failed";
        const failedDraftSet = createDefinitionEditorDraftSetDetail({
            draft_set_id: failedDraftSetId,
            files: [
                createDefinitionEditorDraftFile({
                    key: "failed-detail-workflow",
                    kind: "workflow",
                    status: "clean",
                }),
            ],
            title: "Unavailable draft set",
        });
        const primaryDraftSet = createDefinitionEditorDraftSetDetail();
        server.use(
            http.get("*/authoring/definition-draft-sets", () =>
                HttpResponse.json({
                    items: [
                        createDefinitionEditorDraftSetList(primaryDraftSet).items[0],
                        createDefinitionEditorDraftSetList(failedDraftSet).items[0],
                    ],
                    next_cursor: null,
                }),
            ),
            http.get("*/authoring/definition-draft-sets/:draftSetId", async ({ params }) => {
                const draftSetId = String(params.draftSetId);
                if (draftSetId === failedDraftSetId) {
                    await new Promise((resolve) => {
                        setTimeout(resolve, 50);
                    });
                    return HttpResponse.json(
                        {
                            detail: {
                                code: "missing_resource",
                                field_path: null,
                                ok: false,
                                retryable: true,
                                suggested_next_step: "Choose another draft set.",
                                summary: "The selected draft set could not be read.",
                            },
                        },
                        { status: 404 },
                    );
                }

                return HttpResponse.json(createDefinitionEditorDraftSetResponse(primaryDraftSet));
            }),
        );

        renderDefinitionEditorPage();
        expect(
            await screen.findByRole("button", { name: new RegExp(DEFINITION_EDITOR_WORKFLOW_KEY) }),
        ).toBeVisible();
        expect(screen.getByDisplayValue(new RegExp(DEFINITION_EDITOR_WORKFLOW_KEY))).toBeVisible();

        await user.selectOptions(screen.getByLabelText("Draft set"), failedDraftSetId);

        expect(await screen.findByText("Loading selected draft")).toBeVisible();
        expect(
            screen.queryByRole("button", { name: new RegExp(DEFINITION_EDITOR_WORKFLOW_KEY) }),
        ).not.toBeInTheDocument();
        expect(
            screen.queryByDisplayValue(new RegExp(DEFINITION_EDITOR_WORKFLOW_KEY)),
        ).not.toBeInTheDocument();

        expect(await screen.findAllByText("Selected draft could not load")).toHaveLength(2);
        expect(screen.getAllByText("The selected draft set could not be read.")).toHaveLength(2);
        expect(
            screen.queryByRole("button", { name: new RegExp(DEFINITION_EDITOR_WORKFLOW_KEY) }),
        ).not.toBeInTheDocument();
        expect(
            screen.queryByDisplayValue(new RegExp(DEFINITION_EDITOR_WORKFLOW_KEY)),
        ).not.toBeInTheDocument();
    });

    it("keeps Definition Editor dialogs focused, closes with Escape, and restores opener focus", async () => {
        const user = userEvent.setup();
        installDefinitionEditorHandlers();

        renderDefinitionEditorPage();
        expect(
            await screen.findByRole("button", { name: new RegExp(DEFINITION_EDITOR_WORKFLOW_KEY) }),
        ).toBeVisible();

        const newDraftButton = screen.getByRole("button", { name: "New draft" });
        await user.click(newDraftButton);
        const newDraftDialog = await screen.findByRole("dialog", { name: "New draft" });
        await waitFor(() => {
            expect(within(newDraftDialog).getByLabelText("Draft key")).toHaveFocus();
        });
        await user.keyboard("{Escape}");
        await waitFor(() => {
            expect(newDraftButton).toHaveFocus();
        });

        const resetButton = screen.getByRole("button", { name: "Reset draft" });
        await user.click(resetButton);
        const resetDialog = await screen.findByRole("dialog", { name: "Reset draft" });
        await waitFor(() => {
            expect(within(resetDialog).getByRole("button", { name: "Cancel" })).toHaveFocus();
        });
        await user.keyboard("{Shift>}{Tab}{/Shift}");
        expect(resetDialog).toContainElement(
            document.activeElement as HTMLElement | SVGElement | null,
        );
        await user.keyboard("{Tab}{Tab}{Tab}{Tab}");
        expect(resetDialog).toContainElement(
            document.activeElement as HTMLElement | SVGElement | null,
        );
        await user.keyboard("{Escape}");
        await waitFor(() => {
            expect(resetButton).toHaveFocus();
        });

        const replaceButton = screen.getByRole("button", {
            name: "Replace with current stored revision",
        });
        await user.click(replaceButton);
        const deleteDialog = await screen.findByRole("dialog", {
            name: "Replace with current stored revision",
        });
        await waitFor(() => {
            expect(within(deleteDialog).getByRole("button", { name: "Cancel" })).toHaveFocus();
        });
        await user.keyboard("{Escape}");
        await waitFor(() => {
            expect(replaceButton).toHaveFocus();
        });
    });
});

function renderDefinitionEditorPage(initialEntry = "/definitions/editor") {
    return render(
        <MemoryRouter initialEntries={[initialEntry]}>
            <Routes>
                <Route element={<DefinitionEditorPage />} path="/definitions/editor" />
            </Routes>
        </MemoryRouter>,
    );
}

function installDefinitionEditorHandlers({
    listAuthFailure = false,
    onCreateDraftSet,
    onApply,
    onWrite,
    previewResponse = createDefinitionEditorPreview("valid"),
    validationResponse = createDefinitionEditorValidation("valid"),
}: {
    readonly listAuthFailure?: boolean;
    readonly onCreateDraftSet?: (
        request: Request,
    ) => Promise<components["schemas"]["DefinitionDraftSetDetailResponse"]>;
    readonly onApply?: () => components["schemas"]["DefinitionDraftApplyResponse"];
    readonly onWrite?: (
        request: Request,
        key: string,
    ) => Promise<components["schemas"]["DefinitionDraftSetDetailResponse"]>;
    readonly previewResponse?: components["schemas"]["DefinitionDraftTaskComposePreviewResponse"];
    readonly validationResponse?: components["schemas"]["DefinitionDraftValidationResponse"];
} = {}): void {
    let detail = createDefinitionEditorDraftSetDetail();
    server.use(
        http.get("*/authoring/definition-draft-sets", () => {
            if (listAuthFailure) {
                return HttpResponse.json(createDefinitionEditorAuthFailure(), { status: 401 });
            }
            return HttpResponse.json(createDefinitionEditorDraftSetList(detail));
        }),
        http.post("*/authoring/definition-draft-sets", async ({ request }) => {
            if (onCreateDraftSet !== undefined) {
                const response = await onCreateDraftSet(request);
                detail = response.draft_set;
                return HttpResponse.json(response);
            }
            detail = createDefinitionEditorDraftSetDetail();
            return HttpResponse.json(createDefinitionEditorDraftSetResponse(detail));
        }),
        http.get("*/authoring/definition-draft-sets/:draftSetId", () =>
            HttpResponse.json(createDefinitionEditorDraftSetResponse(detail)),
        ),
        http.delete(
            "*/authoring/definition-draft-sets/:draftSetId",
            () => new HttpResponse(null, { status: 204 }),
        ),
        http.post("*/authoring/definition-draft-sets/:draftSetId/materialize", () => {
            detail = createMaterializedDraftSet();
            return HttpResponse.json(createDefinitionEditorDraftSetResponse(detail));
        }),
        http.put(
            "*/authoring/definition-draft-sets/:draftSetId/files/:kind/:key",
            async ({ request }) => {
                const key = decodeURIComponent(
                    new URL(request.url).pathname.split("/").at(-1) ?? "",
                );
                if (onWrite !== undefined) {
                    const response = await onWrite(request, key);
                    detail = response.draft_set;
                    return HttpResponse.json(response);
                }
                detail = createCleanSavedDefinitionEditorDraftSet();
                return HttpResponse.json(createDefinitionEditorDraftSetResponse(detail));
            },
        ),
        http.post("*/authoring/definition-draft-sets/:draftSetId/files/:kind/:key/reset", () => {
            detail = createResetDefinitionEditorDraftSet();
            return HttpResponse.json(createDefinitionEditorDraftSetResponse(detail));
        }),
        http.post(
            "*/authoring/definition-draft-sets/:draftSetId/files/:kind/:key/rematerialize-current",
            () => {
                detail = createRematerializedDefinitionEditorDraftSet();
                return HttpResponse.json(createDefinitionEditorDraftSetResponse(detail));
            },
        ),
        http.post("*/authoring/definition-draft-sets/:draftSetId/validate", () =>
            HttpResponse.json(validationResponse),
        ),
        http.post("*/authoring/definition-draft-sets/:draftSetId/preview-task-compose", () =>
            HttpResponse.json(previewResponse),
        ),
        http.post("*/authoring/definition-draft-sets/:draftSetId/apply", () =>
            HttpResponse.json(onApply?.() ?? createDefinitionEditorApply("published")),
        ),
    );
}
