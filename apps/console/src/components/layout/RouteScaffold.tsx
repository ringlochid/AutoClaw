import { PageFrame } from "./PageFrame";
import { Surface } from "../ui";

export interface RouteScaffoldProps {
    readonly backingSurfaces: readonly string[];
    readonly eyebrow: string;
    readonly title: string;
}

export function RouteScaffold({ backingSurfaces, eyebrow, title }: RouteScaffoldProps) {
    return (
        <PageFrame
            description="This route is intentionally thin until its page-owned data flow lands."
            eyebrow={eyebrow}
            title={title}
        >
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
                <Surface label="Route" title={title}>
                    <div className="h-36 rounded-md border border-dashed border-outline bg-surface-muted" />
                </Surface>
                <Surface label="Contract" title="Backing surfaces">
                    <ul className="space-y-2">
                        {backingSurfaces.map((surface) => (
                            <li
                                className="rounded-sm border border-outline-soft bg-surface px-3 py-2 font-mono text-label text-muted"
                                key={surface}
                            >
                                {surface}
                            </li>
                        ))}
                    </ul>
                </Surface>
            </div>
        </PageFrame>
    );
}
