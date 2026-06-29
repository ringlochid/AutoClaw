import { CheckCircle2, Pause, Play, Trash2 } from "lucide-react";

import { PageFrame } from "../components/layout";
import { Button, StatusChip, Surface } from "../components/ui";

export function FixtureGalleryPage() {
    return (
        <PageFrame
            description="Internal scaffold route for checking shell, layout, and primitive geometry."
            eyebrow="Internal"
            title="Fixture Gallery"
        >
            <div className="grid gap-4 lg:grid-cols-2">
                <Surface label="Controls" title="Buttons">
                    <div className="flex flex-wrap gap-3">
                        <Button icon={<Play className="size-4" />} variant="primary">
                            Primary
                        </Button>
                        <Button icon={<Pause className="size-4" />}>Secondary</Button>
                        <Button icon={<Trash2 className="size-4" />} variant="danger">
                            Danger
                        </Button>
                        <Button variant="ghost">Ghost</Button>
                    </div>
                </Surface>
                <Surface label="State" title="Status chips">
                    <div className="flex flex-wrap gap-2">
                        <StatusChip tone="active">running</StatusChip>
                        <StatusChip tone="success">ready</StatusChip>
                        <StatusChip tone="warning">waiting</StatusChip>
                        <StatusChip tone="danger">blocked</StatusChip>
                        <StatusChip>quiet</StatusChip>
                    </div>
                </Surface>
                <Surface
                    actions={<StatusChip tone="success">green</StatusChip>}
                    className="lg:col-span-2"
                    label="Surface"
                    title="Panel rhythm"
                >
                    <div className="grid gap-3 sm:grid-cols-3">
                        {["Task tree", "Execution", "Inspector"].map((item) => (
                            <div
                                className="rounded-md border border-outline-soft bg-surface-muted p-3"
                                key={item}
                            >
                                <CheckCircle2
                                    aria-hidden="true"
                                    className="mb-3 size-4 text-primary"
                                />
                                <p className="font-display text-compact font-semibold">{item}</p>
                                <p className="mt-1 font-mono text-label text-muted">
                                    scaffold fixture
                                </p>
                            </div>
                        ))}
                    </div>
                </Surface>
            </div>
        </PageFrame>
    );
}
