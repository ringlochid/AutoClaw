import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TaskGraph } from "../../src/features/task-detail/task-detail-graph";
import type {
    TaskGraphEdge,
    TaskGraphNode,
} from "../../src/features/task-detail/task-detail-model";

const cyclicNodes: readonly TaskGraphNode[] = [
    {
        attemptId: "attempt.root.01",
        checkpointSummary: null,
        eventCount: 2,
        isActive: false,
        isCurrent: true,
        nodeKey: "root",
        order: 0,
        status: "active",
        summary: "Root task.",
    },
    {
        attemptId: "attempt.implementation.01",
        checkpointSummary: null,
        eventCount: 2,
        isActive: false,
        isCurrent: false,
        nodeKey: "implementation_delivery",
        order: 1,
        status: "quiet",
        summary: "Implementation delivery.",
    },
];

const cyclicEdges: readonly TaskGraphEdge[] = [
    {
        fromNodeKey: "root",
        kind: "structural",
        toNodeKey: "implementation_delivery",
    },
    {
        fromNodeKey: "implementation_delivery",
        kind: "staged",
        toNodeKey: "root",
    },
];

afterEach(() => {
    cleanup();
});

describe("task detail graph", () => {
    it("renders cyclic non-tree edges without overflowing the layout walk", () => {
        render(
            <TaskGraph
                edges={cyclicEdges}
                nodes={cyclicNodes}
                onOpenDetail={vi.fn()}
                onSelectNode={vi.fn()}
                selectedNodeKey="root"
            />,
        );

        expect(screen.getByLabelText("Execution graph")).toBeVisible();
        expect(screen.getByRole("button", { name: /root active/i })).toBeVisible();
        expect(
            screen.getByRole("button", { name: /implementation_delivery quiet/i }),
        ).toBeVisible();
    });

    it("centers the camera on the selected node itself", () => {
        render(
            <TaskGraph
                edges={[
                    { fromNodeKey: "root", kind: "structural", toNodeKey: "left_worker" },
                    { fromNodeKey: "root", kind: "structural", toNodeKey: "right_worker" },
                ]}
                nodes={[
                    {
                        attemptId: "attempt.root.01",
                        checkpointSummary: null,
                        eventCount: 1,
                        isActive: false,
                        isCurrent: false,
                        nodeKey: "root",
                        order: 0,
                        status: "quiet",
                        summary: "Root task.",
                    },
                    {
                        attemptId: "attempt.left.01",
                        checkpointSummary: null,
                        eventCount: 1,
                        isActive: true,
                        isCurrent: true,
                        nodeKey: "left_worker",
                        order: 1,
                        status: "active",
                        summary: "Left worker.",
                    },
                    {
                        attemptId: "attempt.right.01",
                        checkpointSummary: null,
                        eventCount: 1,
                        isActive: false,
                        isCurrent: false,
                        nodeKey: "right_worker",
                        order: 2,
                        status: "quiet",
                        summary: "Right worker.",
                    },
                ]}
                onOpenDetail={vi.fn()}
                onSelectNode={vi.fn()}
                selectedNodeKey="left_worker"
            />,
        );

        const cameraGroup = screen
            .getByLabelText("Execution graph")
            .querySelector('g[transform^="translate"]');

        const transform = cameraGroup?.getAttribute("transform") ?? "";
        const translateX = Number(
            /^translate\((?<translateX>-?\d+(?:\.\d+)?) /.exec(transform)?.groups?.translateX,
        );

        expect(translateX).toBeGreaterThan(250);
        expect(transform).toContain("scale(1.85)");
    });
});
