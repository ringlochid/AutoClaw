/// <reference types="node" />

import { mkdirSync } from "node:fs";

import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";

import {
    DEFINITION_EDITOR_SCREENSHOT_DIR,
    DEFINITION_EDITOR_WORKFLOW_KEY,
    createDefinitionEditorApply,
    createDefinitionEditorDraftSetDetail,
    createDefinitionEditorDraftSetList,
    createDefinitionEditorDraftSetResponse,
    createDefinitionEditorPreview,
    createDefinitionEditorValidation,
    createRematerializedDefinitionEditorDraftSet,
    createResetDefinitionEditorDraftSet,
} from "../fixtures/definition-editor";

test("renders Definition Editor workbench, focus, accessibility, and replace modal at desktop width", async ({
    page,
}, testInfo) => {
    test.skip(testInfo.project.name !== "chromium", "desktop proof is captured once");

    await mockDefinitionEditor(page);
    await page.setViewportSize({ height: 1000, width: 1440 });
    await page.goto("/definitions/editor");

    await expect(page.getByRole("heading", { level: 1, name: "Definition Editor" })).toBeVisible();
    await expect(
        page.getByRole("button", { name: new RegExp(DEFINITION_EDITOR_WORKFLOW_KEY) }),
    ).toBeVisible();
    await expect(page.getByLabel("Draft body")).toBeVisible();
    await expect(page.getByText("Editable draft body")).toHaveCount(0);
    await expect(page.getByText("Reset restores the captured stored baseline.")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Save draft" })).toBeDisabled();
    await expectNoDocumentOverflow(page);

    const validateButton = page.getByRole("button", { name: "Validate" });
    await validateButton.focus();
    await expect(validateButton).toBeFocused();

    const accessibilityScanResults = await new AxeBuilder({ page })
        .exclude('a[aria-label="Fixture gallery"]')
        .analyze();
    expect(accessibilityScanResults.violations).toEqual([]);

    mkdirSync(DEFINITION_EDITOR_SCREENSHOT_DIR, { recursive: true });
    await page.evaluate(() => {
        if (document.activeElement instanceof HTMLElement) {
            document.activeElement.blur();
        }
        window.scrollTo(0, 0);
    });
    await page.screenshot({
        fullPage: true,
        path: `${DEFINITION_EDITOR_SCREENSHOT_DIR}/definition-editor-desktop.png`,
    });

    const replaceButton = page.getByRole("button", {
        name: "Replace with current stored revision",
    });
    await replaceButton.click();
    const replaceDialog = page.getByRole("dialog", {
        name: "Replace with current stored revision",
    });
    await expect(replaceDialog).toBeVisible();
    await expect(replaceDialog.getByRole("button", { name: "Cancel" })).toBeFocused();
    await page.evaluate(() => {
        if (document.activeElement instanceof HTMLElement) {
            document.activeElement.blur();
        }
    });
    await page.screenshot({
        path: `${DEFINITION_EDITOR_SCREENSHOT_DIR}/definition-editor-replace-modal.png`,
    });
    await replaceDialog.getByRole("button", { name: "Cancel" }).focus();
    await page.keyboard.press("Shift+Tab");
    expect(await replaceDialog.evaluate((dialog) => dialog.contains(document.activeElement))).toBe(
        true,
    );
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    expect(await replaceDialog.evaluate((dialog) => dialog.contains(document.activeElement))).toBe(
        true,
    );
    await page.keyboard.press("Escape");
    await expect(replaceDialog).toBeHidden();
    await expect(replaceButton).toBeFocused();

    await page.getByRole("button", { name: "Apply" }).click();
    const applyDialog = page.getByRole("dialog", {
        name: "Apply published new current revisions",
    });
    await expect(applyDialog).toBeVisible();
    await expect(
        applyDialog.getByText(/workflow\/definition-editor-page revision 14/),
    ).toBeVisible();
    await page.evaluate(() => {
        if (document.activeElement instanceof HTMLElement) {
            document.activeElement.blur();
        }
    });
    await page.screenshot({
        path: `${DEFINITION_EDITOR_SCREENSHOT_DIR}/definition-editor-apply-modal.png`,
    });
});

test("keeps Definition Editor draft selection and editor usable at mobile width", async ({
    page,
}, testInfo) => {
    test.skip(testInfo.project.name !== "mobile-chrome", "mobile proof is captured once");

    await mockDefinitionEditor(page);
    await page.goto("/definitions/editor");

    await expect(page.getByRole("heading", { level: 1, name: "Definition Editor" })).toBeVisible();
    await page.getByRole("button", { name: new RegExp(DEFINITION_EDITOR_WORKFLOW_KEY) }).click();
    await expect(page.getByLabel("Draft body")).toBeVisible();
    await page.getByRole("button", { name: "Preview" }).click();
    await expect(
        page.getByLabel("Preview provenance").getByRole("button", { name: "Draft truth" }),
    ).toBeVisible();
    await expectNoDocumentOverflow(page);

    mkdirSync(DEFINITION_EDITOR_SCREENSHOT_DIR, { recursive: true });
    await page.evaluate(() => {
        window.scrollTo(0, 0);
    });
    await page.screenshot({
        fullPage: true,
        path: `${DEFINITION_EDITOR_SCREENSHOT_DIR}/definition-editor-mobile.png`,
    });
});

async function mockDefinitionEditor(page: Page): Promise<void> {
    let detail = createDefinitionEditorDraftSetDetail();
    await page.route("http://127.0.0.1:18125/authoring/definition-draft-sets**", async (route) => {
        const request = route.request();
        const requestUrl = new URL(request.url());
        const path = requestUrl.pathname;
        const method = request.method();

        if (path === "/authoring/definition-draft-sets" && method === "GET") {
            await fulfillJson(route, createDefinitionEditorDraftSetList(detail));
            return;
        }

        if (path === "/authoring/definition-draft-sets" && method === "POST") {
            await fulfillJson(route, createDefinitionEditorDraftSetResponse(detail));
            return;
        }

        if (path.endsWith("/validate") && method === "POST") {
            await fulfillJson(route, createDefinitionEditorValidation("valid"));
            return;
        }

        if (path.endsWith("/preview-task-compose") && method === "POST") {
            await fulfillJson(route, createDefinitionEditorPreview("valid"));
            return;
        }

        if (path.endsWith("/apply") && method === "POST") {
            await fulfillJson(route, createDefinitionEditorApply("published"));
            return;
        }

        if (path.endsWith("/reset") && method === "POST") {
            detail = createResetDefinitionEditorDraftSet();
            await fulfillJson(route, createDefinitionEditorDraftSetResponse(detail));
            return;
        }

        if (path.endsWith("/rematerialize-current") && method === "POST") {
            detail = createRematerializedDefinitionEditorDraftSet();
            await fulfillJson(route, createDefinitionEditorDraftSetResponse(detail));
            return;
        }

        if (method === "PUT") {
            await fulfillJson(route, createDefinitionEditorDraftSetResponse(detail));
            return;
        }

        if (method === "DELETE") {
            await route.fulfill({ status: 204 });
            return;
        }

        await fulfillJson(route, createDefinitionEditorDraftSetResponse(detail));
    });
}

async function fulfillJson(route: Route, body: unknown): Promise<void> {
    await route.fulfill({
        body: JSON.stringify(body),
        contentType: "application/json",
    });
}

async function expectNoDocumentOverflow(page: Page): Promise<void> {
    const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );

    expect(overflow).toBeLessThanOrEqual(1);
}
