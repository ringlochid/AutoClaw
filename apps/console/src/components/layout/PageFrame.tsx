import type { ReactNode } from "react";

import { classNames } from "../../lib/classNames";

export interface PageFrameProps {
    readonly actions?: ReactNode;
    readonly children: ReactNode;
    readonly className?: string;
    readonly description?: string;
    readonly eyebrow?: string;
    readonly title: string;
}

export function PageFrame({
    actions,
    children,
    className,
    description,
    eyebrow,
    title,
}: PageFrameProps) {
    return (
        <section
            className={classNames(
                "min-h-[calc(100vh-7rem)] rounded-shell border border-outline-soft bg-surface p-4 shadow-shell sm:p-5",
                className,
            )}
        >
            <header className="mb-5 flex flex-col gap-4 border-b border-outline-soft pb-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0">
                    {eyebrow === undefined ? null : (
                        <p className="font-mono text-label font-medium uppercase text-muted">
                            {eyebrow}
                        </p>
                    )}
                    <h1 className="mt-1 font-display text-display font-semibold text-foreground">
                        {title}
                    </h1>
                    {description === undefined ? null : (
                        <p className="mt-2 max-w-3xl text-compact text-muted">{description}</p>
                    )}
                </div>
                {actions === undefined ? null : (
                    <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
                )}
            </header>
            {children}
        </section>
    );
}
