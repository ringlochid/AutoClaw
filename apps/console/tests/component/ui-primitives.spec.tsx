import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button, StatusChip, Surface } from "../../src/components/ui";

describe("ui primitives", () => {
    it("keeps button type safe by default", () => {
        render(<Button>Pause</Button>);

        expect(screen.getByRole("button", { name: "Pause" })).toHaveAttribute("type", "button");
    });

    it("renders status chip content", () => {
        render(<StatusChip tone="active">running</StatusChip>);

        expect(screen.getByText("running")).toBeVisible();
    });

    it("renders surface heading and body", () => {
        render(
            <Surface label="Contract" title="Backing surfaces">
                <p>GET /runtime/tasks</p>
            </Surface>,
        );

        expect(screen.getByRole("heading", { name: "Backing surfaces" })).toBeVisible();
        expect(screen.getByText("GET /runtime/tasks")).toBeVisible();
    });
});
