import { classNames } from "../../lib/classNames";

export function controlClassName(extraClassName?: string): string {
    return classNames(
        "h-control w-full rounded-control border border-outline bg-surface px-3 text-compact text-foreground shadow-hairline transition-colors placeholder:text-muted focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/15",
        extraClassName,
    );
}

export function textAreaClassName(): string {
    return classNames(
        "min-h-24 w-full rounded-control border border-outline bg-surface px-3 py-2 text-compact text-foreground shadow-hairline transition-colors placeholder:text-muted focus:border-primary/50 focus:outline-none focus:ring-2 focus:ring-primary/15",
    );
}
