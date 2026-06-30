import { ExternalLink, RotateCcw, ZoomIn, ZoomOut } from "lucide-react";

import { Button, IconButton, Surface } from "../../components/ui";
import { classNames } from "../../lib/classNames";
import type { TaskGraphEdge, TaskGraphNode } from "./task-detail-model";

interface GraphLayout {
    readonly height: number;
    readonly nodeHeight: number;
    readonly nodeWidth: number;
    readonly nodes: readonly GraphLayoutNode[];
    readonly width: number;
}

interface GraphLayoutNode extends TaskGraphNode {
    readonly x: number;
    readonly y: number;
}

export function TaskGraph({
    edges,
    nodes,
    onOpenDetail,
    onReset,
    onSelectNode,
    onZoomIn,
    onZoomOut,
    selectedNodeKey,
    zoomPercent,
}: {
    readonly edges: readonly TaskGraphEdge[];
    readonly nodes: readonly TaskGraphNode[];
    readonly onOpenDetail: () => void;
    readonly onReset: () => void;
    readonly onSelectNode: (nodeKey: string) => void;
    readonly onZoomIn: () => void;
    readonly onZoomOut: () => void;
    readonly selectedNodeKey: string | null;
    readonly zoomPercent: number;
}) {
    const layout = buildGraphLayout(nodes);
    const scale = zoomPercent / 100;

    return (
        <Surface
            actions={
                <div className="flex items-center gap-2">
                    <Button icon={<ExternalLink />} onClick={onOpenDetail}>
                        Open detail
                    </Button>
                    <IconButton icon={<ZoomOut />} label="Zoom out graph" onClick={onZoomOut} />
                    <span className="min-w-12 text-center font-mono text-label text-muted">
                        {zoomPercent}%
                    </span>
                    <IconButton icon={<ZoomIn />} label="Zoom in graph" onClick={onZoomIn} />
                    <IconButton icon={<RotateCcw />} label="Reset graph zoom" onClick={onReset} />
                </div>
            }
            className="min-w-0"
            label="Execution graph"
            title="Read-only task graph"
        >
            <GraphCanvas
                edges={edges}
                layout={layout}
                onSelectNode={onSelectNode}
                scale={scale}
                selectedNodeKey={selectedNodeKey}
            />
        </Surface>
    );
}

function GraphCanvas({
    edges,
    layout,
    onSelectNode,
    scale,
    selectedNodeKey,
}: {
    readonly edges: readonly TaskGraphEdge[];
    readonly layout: GraphLayout;
    readonly onSelectNode: (nodeKey: string) => void;
    readonly scale: number;
    readonly selectedNodeKey: string | null;
}) {
    return (
        <div
            aria-label="Execution graph"
            className="min-h-[30rem] overflow-auto rounded-card border border-outline-soft bg-[linear-gradient(180deg,#fff,#f7f4ef)] p-4"
            role="group"
        >
            <div
                className="relative"
                style={{
                    height: layout.height * scale,
                    width: layout.width * scale,
                }}
            >
                <div
                    className="relative"
                    style={{
                        height: layout.height,
                        transform: `scale(${String(scale)})`,
                        transformOrigin: "top left",
                        width: layout.width,
                    }}
                >
                    <GraphEdges edges={edges} layout={layout} />
                    <GraphNodes
                        layout={layout}
                        onSelectNode={onSelectNode}
                        selectedNodeKey={selectedNodeKey}
                    />
                </div>
            </div>
        </div>
    );
}

function GraphEdges({
    edges,
    layout,
}: {
    readonly edges: readonly TaskGraphEdge[];
    readonly layout: GraphLayout;
}) {
    const nodeByKey = new Map(layout.nodes.map((node) => [node.nodeKey, node]));

    return (
        <svg
            aria-hidden="true"
            className="absolute inset-0"
            height={layout.height}
            width={layout.width}
        >
            {edges.map((edge) => {
                const fromNode = nodeByKey.get(edge.fromNodeKey);
                const toNode = nodeByKey.get(edge.toNodeKey);
                if (fromNode === undefined || toNode === undefined) {
                    return null;
                }

                return (
                    <line
                        className={classNames(
                            "stroke-primary/50",
                            edge.kind === "staged" && "[stroke-dasharray:6_6]",
                            edge.kind === "chronology" && "stroke-outline",
                        )}
                        key={`${edge.fromNodeKey}-${edge.toNodeKey}-${edge.kind}`}
                        strokeLinecap="round"
                        strokeWidth={edge.kind === "boundary" ? 3 : 2}
                        x1={fromNode.x + layout.nodeWidth / 2}
                        x2={toNode.x + layout.nodeWidth / 2}
                        y1={fromNode.y + layout.nodeHeight}
                        y2={toNode.y}
                    />
                );
            })}
        </svg>
    );
}

function GraphNodes({
    layout,
    onSelectNode,
    selectedNodeKey,
}: {
    readonly layout: GraphLayout;
    readonly onSelectNode: (nodeKey: string) => void;
    readonly selectedNodeKey: string | null;
}) {
    return (
        <>
            {layout.nodes.map((node) => (
                <button
                    aria-pressed={node.nodeKey === selectedNodeKey}
                    className={classNames(
                        "absolute flex min-w-0 flex-col items-start rounded-card border bg-surface-low p-3 text-left shadow-panel transition-colors hover:border-primary/45 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary",
                        node.nodeKey === selectedNodeKey
                            ? "border-primary bg-primary-soft"
                            : "border-outline-soft",
                    )}
                    key={node.nodeKey}
                    onClick={() => {
                        onSelectNode(node.nodeKey);
                    }}
                    style={{
                        height: layout.nodeHeight,
                        left: node.x,
                        top: node.y,
                        width: layout.nodeWidth,
                    }}
                    type="button"
                >
                    <span className="font-mono text-label font-medium uppercase text-muted">
                        {node.status}
                    </span>
                    <span className="mt-1 max-w-full truncate font-display text-compact font-semibold text-foreground">
                        {node.nodeKey}
                    </span>
                    <span className="mt-1 line-clamp-2 text-utility text-muted">
                        {node.summary}
                    </span>
                </button>
            ))}
        </>
    );
}

function buildGraphLayout(nodes: readonly TaskGraphNode[]): GraphLayout {
    const nodeWidth = 224;
    const nodeHeight = 112;
    const columnGap = 80;
    const rowGap = 52;
    const columns = nodes.length > 8 ? 3 : nodes.length > 4 ? 2 : 1;
    const orderedNodes = [...nodes].sort((left, right) => left.order - right.order);
    const layoutNodes = orderedNodes.map((node, index): GraphLayoutNode => {
        const column = index % columns;
        const row = Math.floor(index / columns);
        return {
            ...node,
            x: 24 + column * (nodeWidth + columnGap),
            y: 24 + row * (nodeHeight + rowGap),
        };
    });

    const rows = Math.max(1, Math.ceil(layoutNodes.length / columns));
    return {
        height: 48 + rows * nodeHeight + Math.max(0, rows - 1) * rowGap,
        nodeHeight,
        nodeWidth,
        nodes: layoutNodes,
        width: 48 + columns * nodeWidth + Math.max(0, columns - 1) * columnGap,
    };
}
