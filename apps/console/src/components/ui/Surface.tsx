import type { HTMLAttributes, ReactNode } from "react";

import { classNames } from "../../lib/classNames";

export interface SurfaceProps extends HTMLAttributes<HTMLElement> {
    readonly actions?: ReactNode;
    readonly children: ReactNode;
    readonly label?: string;
    readonly title?: string;
}

export function Surface({ actions, children, className, label, title, ...props }: SurfaceProps) {
    const hasHeader = actions !== undefined || label !== undefined || title !== undefined;

    return (
        <section
            className={classNames(
                "rounded-card border border-outline-soft bg-surface-low p-4 shadow-hairline",
                className,
            )}
            {...props}
        >
            {hasHeader ? (
                <header className="mb-4 flex items-start justify-between gap-4">
                    <div className="min-w-0">
                        {label === undefined ? null : (
                            <p className="font-mono text-label font-medium uppercase text-muted">
                                {label}
                            </p>
                        )}
                        {title === undefined ? null : (
                            <h2 className="mt-1 font-display text-compact font-semibold text-foreground">
                                {title}
                            </h2>
                        )}
                    </div>
                    {actions === undefined ? null : (
                        <div className="flex shrink-0 items-center gap-2">{actions}</div>
                    )}
                </header>
            ) : null}
            {children}
        </section>
    );
}
