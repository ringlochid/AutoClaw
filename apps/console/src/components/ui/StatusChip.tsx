import type { HTMLAttributes, ReactNode } from "react";

import { classNames } from "../../lib/classNames";

export type StatusTone = "active" | "danger" | "neutral" | "success" | "warning";

export interface StatusChipProps extends HTMLAttributes<HTMLSpanElement> {
    readonly children: ReactNode;
    readonly tone?: StatusTone;
}

const toneClasses: Record<StatusTone, string> = {
    active: "border-primary/20 bg-primary-soft text-primary-foreground",
    danger: "border-danger/20 bg-danger-soft text-danger",
    neutral: "border-outline-soft bg-surface-muted text-muted",
    success: "border-emerald-200 bg-emerald-50 text-emerald-700",
    warning: "border-amber-200 bg-amber-50 text-amber-700",
};

export function StatusChip({ children, className, tone = "neutral", ...props }: StatusChipProps) {
    return (
        <span
            className={classNames(
                "inline-flex h-7 items-center rounded-control border px-2.5 font-mono text-label font-medium",
                toneClasses[tone],
                className,
            )}
            {...props}
        >
            {children}
        </span>
    );
}
