import {
    BookOpen,
    ClipboardList,
    GalleryHorizontalEnd,
    ListTree,
    Rocket,
    type LucideIcon,
} from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { classNames } from "../../lib/classNames";
import { StatusChip } from "../ui";

interface ShellNavItem {
    readonly icon: LucideIcon;
    readonly label: string;
    readonly match: (pathname: string) => boolean;
    readonly to: string;
}

interface ShellContext {
    readonly breadcrumbs: readonly string[];
    readonly section: string;
    readonly status: string;
    readonly statusTone: "active" | "neutral" | "success";
}

type PrimaryNavVariant = "mobile" | "rail";

const NAV_GROUPS: readonly {
    readonly items: readonly ShellNavItem[];
    readonly section: string;
}[] = [
    {
        section: "Runtime",
        items: [
            {
                icon: ListTree,
                label: "Tasks",
                match: (pathname) => pathname === "/tasks" || pathname.startsWith("/tasks/"),
                to: "/tasks",
            },
        ],
    },
    {
        section: "Authoring",
        items: [
            {
                icon: BookOpen,
                label: "Definitions",
                match: (pathname) =>
                    pathname === "/definitions" || pathname.startsWith("/definitions/"),
                to: "/definitions",
            },
            {
                icon: Rocket,
                label: "Task Start",
                match: (pathname) => pathname === "/task-start",
                to: "/task-start",
            },
        ],
    },
];

export function AppShell() {
    const location = useLocation();
    const context = getShellContext(location.pathname);

    return (
        <div className="min-h-screen bg-background text-foreground lg:grid lg:grid-cols-[16rem_minmax(0,1fr)]">
            <aside className="hidden border-r border-outline-soft bg-surface lg:flex lg:min-h-screen lg:flex-col">
                <div className="flex items-center gap-3 border-b border-outline-soft px-5 py-4">
                    <div className="flex size-10 shrink-0 items-center justify-center rounded-card bg-primary-soft font-display text-display font-semibold text-primary">
                        A
                    </div>
                    <div className="min-w-0">
                        <p className="truncate font-display text-compact font-semibold text-foreground">
                            AutoClaw
                        </p>
                        <p className="font-mono text-label font-medium uppercase text-muted">
                            Console
                        </p>
                    </div>
                </div>
                <nav aria-label="Primary" className="flex flex-1 flex-col gap-5 px-3 py-4">
                    <PrimaryNavGroups pathname={location.pathname} variant="rail" />
                </nav>
            </aside>
            <div className="min-w-0">
                <header className="sticky top-0 z-10 border-b border-outline-soft bg-background/95 backdrop-blur">
                    <div className="flex min-h-16 flex-wrap items-center justify-between gap-3 px-page-inline py-3">
                        <div className="min-w-0">
                            <p className="font-mono text-label font-medium uppercase text-muted">
                                {context.section}
                            </p>
                            <nav
                                aria-label="Breadcrumb"
                                className="mt-1 flex min-w-0 items-center gap-2 text-utility text-muted"
                            >
                                <ClipboardList aria-hidden="true" className="size-4 shrink-0" />
                                <ol className="flex min-w-0 flex-wrap items-center gap-1">
                                    {context.breadcrumbs.map((breadcrumb, index) => {
                                        const isCurrent = index === context.breadcrumbs.length - 1;

                                        return (
                                            <li
                                                className="flex min-w-0 items-center gap-1"
                                                key={`${breadcrumb}-${String(index)}`}
                                            >
                                                {index === 0 ? null : (
                                                    <span aria-hidden="true">/</span>
                                                )}
                                                <span
                                                    aria-current={isCurrent ? "page" : undefined}
                                                    className={classNames(
                                                        "min-w-0 truncate",
                                                        isCurrent &&
                                                            "font-semibold text-foreground",
                                                    )}
                                                >
                                                    {breadcrumb}
                                                </span>
                                            </li>
                                        );
                                    })}
                                </ol>
                            </nav>
                        </div>
                        <StatusChip tone={context.statusTone} withDot>
                            {context.status}
                        </StatusChip>
                    </div>
                    <nav
                        aria-label="Primary"
                        className="flex gap-2 overflow-x-auto px-page-inline pb-3 lg:hidden"
                    >
                        <PrimaryNavGroups pathname={location.pathname} variant="mobile" />
                    </nav>
                </header>
                <main
                    aria-label="AutoClaw Console"
                    className="min-h-[calc(100vh-4rem)] px-page-inline py-page-block"
                >
                    <Outlet />
                </main>
            </div>
            <NavLink
                aria-label="Fixture gallery"
                className="fixed bottom-4 right-4 hidden size-icon-control items-center justify-center rounded-full border border-outline-soft bg-surface-low text-muted shadow-panel transition-colors hover:text-primary-foreground xl:flex"
                to="/fixtures"
            >
                <GalleryHorizontalEnd aria-hidden="true" className="size-4" />
            </NavLink>
        </div>
    );
}

function PrimaryNavGroups({
    pathname,
    variant,
}: {
    readonly pathname: string;
    readonly variant: PrimaryNavVariant;
}) {
    return NAV_GROUPS.map((group) => (
        <div
            className={classNames(
                variant === "rail" && "space-y-2",
                variant === "mobile" && "flex shrink-0 items-center gap-2",
            )}
            key={group.section}
        >
            <p
                className={classNames(
                    "font-mono text-label font-medium uppercase text-muted",
                    variant === "mobile" && "sr-only",
                )}
            >
                {group.section}
            </p>
            <div
                className={classNames(
                    variant === "rail" && "space-y-1",
                    variant === "mobile" && "flex gap-2",
                )}
            >
                {group.items.map((item) => (
                    <PrimaryNavLink
                        item={item}
                        key={item.to}
                        pathname={pathname}
                        variant={variant}
                    />
                ))}
            </div>
        </div>
    ));
}

function PrimaryNavLink({
    item,
    pathname,
    variant,
}: {
    readonly item: ShellNavItem;
    readonly pathname: string;
    readonly variant: PrimaryNavVariant;
}) {
    const Icon = item.icon;

    return (
        <NavLink
            className={({ isActive }) =>
                classNames(
                    "flex h-control items-center gap-2 rounded-control px-3 text-utility font-semibold text-muted transition-colors hover:bg-surface-muted hover:text-foreground",
                    variant === "rail" && "w-full",
                    variant === "mobile" && "shrink-0 border border-outline-soft bg-surface-low",
                    (isActive || item.match(pathname)) && "bg-active text-active-foreground",
                )
            }
            to={item.to}
        >
            <span aria-hidden="true" className="size-1.5 shrink-0 rounded-full bg-current" />
            <Icon aria-hidden="true" className="size-4 shrink-0" />
            <span className="truncate">{item.label}</span>
        </NavLink>
    );
}

function getShellContext(pathname: string): ShellContext {
    const segments = pathname.split("/").filter((segment) => segment.length > 0);
    const taskIdSegment = segments.find((_segment, index) => index === 1);
    const taskId = taskIdSegment === undefined ? "Selected task" : safeDecode(taskIdSegment);

    if (segments[0] === "tasks" && segments[2] === "human-requests") {
        return {
            breadcrumbs: ["Tasks", taskId, "Human Requests"],
            section: "Runtime",
            status: "Live",
            statusTone: "active",
        };
    }

    if (segments[0] === "tasks" && segments[2] === "command-runs") {
        return {
            breadcrumbs: ["Tasks", taskId, "Command Runs"],
            section: "Runtime",
            status: "Live",
            statusTone: "active",
        };
    }

    if (segments[0] === "tasks" && segments.length > 1) {
        return {
            breadcrumbs: ["Tasks", taskId],
            section: "Runtime",
            status: "Live",
            statusTone: "active",
        };
    }

    if (segments[0] === "definitions" && segments[1] === "editor") {
        return {
            breadcrumbs: ["Definitions", "Editor"],
            section: "Authoring",
            status: "Draft editing",
            statusTone: "neutral",
        };
    }

    if (segments[0] === "definitions") {
        return {
            breadcrumbs: ["Definitions"],
            section: "Authoring",
            status: "Stored registry",
            statusTone: "neutral",
        };
    }

    if (segments[0] === "task-start") {
        return {
            breadcrumbs: ["Task Start"],
            section: "Authoring",
            status: "Workflow launch",
            statusTone: "neutral",
        };
    }

    if (segments[0] === "fixtures") {
        return {
            breadcrumbs: ["Fixtures"],
            section: "Internal",
            status: "Internal",
            statusTone: "success",
        };
    }

    return {
        breadcrumbs: ["Tasks"],
        section: "Runtime",
        status: "Live",
        statusTone: "active",
    };
}

function safeDecode(value: string): string {
    try {
        return decodeURIComponent(value);
    } catch {
        return value;
    }
}
