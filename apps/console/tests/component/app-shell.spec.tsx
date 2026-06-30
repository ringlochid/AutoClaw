import { cleanup, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import { AppShell } from "../../src/components/layout";

afterEach(() => {
    cleanup();
});

describe("app shell", () => {
    it("keeps task-scoped runtime breadcrumbs under Tasks", () => {
        renderShell("/tasks/task-123/human-requests");

        const breadcrumb = within(screen.getByRole("navigation", { name: "Breadcrumb" }));
        expect(breadcrumb.getByText("Tasks")).toBeVisible();
        expect(breadcrumb.getByText("task-123")).not.toHaveAttribute("aria-current");
        expect(breadcrumb.getByText("Human Requests")).toHaveAttribute("aria-current", "page");
        expect(screen.getAllByText("Runtime").length).toBeGreaterThan(0);
        expect(screen.getByText("Live")).toBeVisible();
    });

    it("keeps authoring breadcrumbs separate from selected task routes", () => {
        renderShell("/definitions/editor");

        const breadcrumb = within(screen.getByRole("navigation", { name: "Breadcrumb" }));
        expect(breadcrumb.getByText("Definitions")).toBeVisible();
        expect(breadcrumb.getByText("Editor")).toHaveAttribute("aria-current", "page");
        expect(screen.getAllByText("Authoring").length).toBeGreaterThan(0);
        expect(screen.getByText("Draft editing")).toBeVisible();
    });

    it("limits primary navigation to the accepted product destinations", () => {
        renderShell("/tasks/task-123/command-runs");

        const primaryLabels = screen.getAllByRole("link").map((link) => link.textContent.trim());

        expect(primaryLabels).toContain("Tasks");
        expect(primaryLabels).toContain("Definitions");
        expect(primaryLabels).toContain("Task Start");
        expect(primaryLabels).not.toContain("Task Detail");
        expect(primaryLabels).not.toContain("Human Requests");
        expect(primaryLabels).not.toContain("Command Runs");
    });
});

function renderShell(initialPath: string) {
    render(
        <MemoryRouter initialEntries={[initialPath]}>
            <Routes>
                <Route element={<AppShell />} path="/*">
                    <Route element={<p>Page content</p>} path="*" />
                </Route>
            </Routes>
        </MemoryRouter>,
    );
}
