import { expect, test } from "@playwright/test";

test("routes root traffic into the task shell", async ({ page }) => {
    await page.goto("/");

    await expect(page).toHaveURL(/\/tasks$/);
    await expect(page.getByRole("main", { name: "AutoClaw Console" })).toBeVisible();
    await expect(page.getByRole("heading", { level: 1, name: "Tasks" })).toBeVisible();
});

test("keeps primary navigation on real product routes", async ({ page }) => {
    await page.goto("/tasks");

    await page.getByRole("link", { name: "Definitions" }).click();
    await expect(page).toHaveURL(/\/definitions$/);
    await expect(page.getByRole("heading", { level: 1, name: "Definitions" })).toBeVisible();

    await page.getByRole("link", { name: "Task Start" }).click();
    await expect(page).toHaveURL(/\/task-start$/);
    await expect(page.getByRole("heading", { level: 1, name: "Task Start" })).toBeVisible();
});

test("keeps task-scoped breadcrumbs below Tasks", async ({ page }) => {
    await page.goto("/tasks/runtime-copy-refresh/human-requests");

    const breadcrumb = page.getByRole("navigation", { name: "Breadcrumb" });
    await expect(breadcrumb).toContainText("Tasks");
    await expect(breadcrumb).toContainText("runtime-copy-refresh");
    await expect(breadcrumb).toContainText("Human Requests");
    await expect(page.getByRole("heading", { level: 1, name: "Human Requests" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Human Requests" })).toHaveCount(0);
});

test("keeps authoring breadcrumbs separate from selected task routes", async ({ page }) => {
    await page.goto("/definitions/editor");

    const breadcrumb = page.getByRole("navigation", { name: "Breadcrumb" });
    await expect(breadcrumb).toContainText("Definitions");
    await expect(breadcrumb).toContainText("Editor");
    await expect(page.getByText("Draft editing")).toBeVisible();
    await expect(page.getByText("Task Control Suite")).toHaveCount(0);
});

test("keeps the shell keyboard path visible", async ({ page }) => {
    await page.goto("/tasks");

    await page.keyboard.press("Tab");
    await expect(page.getByRole("link", { name: "Tasks" })).toBeFocused();
});

test("avoids document-level horizontal overflow on narrow shell routes", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });

    for (const route of [
        "/tasks",
        "/tasks/runtime-copy-refresh",
        "/tasks/runtime-copy-refresh/human-requests",
        "/definitions",
        "/definitions/editor",
        "/task-start",
        "/fixtures",
    ]) {
        await page.goto(route);
        await expect(page.getByRole("main", { name: "AutoClaw Console" })).toBeVisible();

        const overflow = await page.evaluate(
            () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        );

        expect(overflow).toBeLessThanOrEqual(1);
    }
});

test("renders the internal fixture gallery route", async ({ page }) => {
    await page.goto("/fixtures");

    await expect(page.getByRole("heading", { name: "Fixture Gallery" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Primary" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Refresh" })).toBeVisible();
    const overviewTab = page.getByRole("tab", { name: "Overview" });
    await expect(overviewTab).toBeVisible();

    await overviewTab.focus();
    await page.keyboard.press("ArrowRight");

    const checkpointTab = page.getByRole("tab", { name: "Checkpoint" });
    await expect(checkpointTab).toBeFocused();
    await expect(checkpointTab).toHaveAttribute("aria-selected", "true");
});
