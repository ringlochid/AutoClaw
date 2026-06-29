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

test("renders the internal fixture gallery route", async ({ page }) => {
    await page.goto("/fixtures");

    await expect(page.getByRole("heading", { name: "Fixture Gallery" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Primary" })).toBeVisible();
});
