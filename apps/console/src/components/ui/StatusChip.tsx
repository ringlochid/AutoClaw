import type { HTMLAttributes, ReactNode } from "react";

import { classNames } from "../../lib/classNames";

export type StatusTone = "active" | "danger" | "neutral" | "success" | "warning";

export interface StatusChipProps extends HTMLAttributes<HTMLSpanElement> {
    readonly children: ReactNode;
    readonly tone?: StatusTone;
    readonly withDot?: boolean;
}

const toneClasses: Record<StatusTone, string> = {
    active: "border-primary/20 bg-primary-soft text-primary-foreground",
    danger: "border-red-200 bg-danger-soft text-red-700",
    neutral: "border-outline-soft bg-surface-muted text-muted",
    success: "border-emerald-200 bg-emerald-50 text-emerald-700",
    warning: "border-amber-200 bg-amber-50 text-amber-700",
};

export function StatusChip({ children, className, tone = "neutral", ...props }: StatusChipProps) {
    const { withDot = false, ...spanProps } = props;

    return (
        <span
            className={classNames(
                "inline-flex h-7 items-center gap-2 rounded-control border px-2.5 font-mono text-label font-medium",
                toneClasses[tone],
                className,
            )}
            {...spanProps}
        >
            {withDot ? (
                <span aria-hidden="true" className="size-1.5 rounded-full bg-current" />
            ) : null}
            {children}
        </span>
    );
}
