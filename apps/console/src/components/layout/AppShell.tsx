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
}

type PrimaryNavVariant = "mobile" | "rail";

const NAV_ITEMS: readonly ShellNavItem[] = [
    {
        icon: ListTree,
        label: "Tasks",
        match: (pathname) => pathname === "/tasks" || pathname.startsWith("/tasks/"),
        to: "/tasks",
    },
    {
        icon: BookOpen,
        label: "Definitions",
        match: (pathname) => pathname === "/definitions" || pathname.startsWith("/definitions/"),
        to: "/definitions",
    },
    {
        icon: Rocket,
        label: "Task Start",
        match: (pathname) => pathname === "/task-start",
        to: "/task-start",
    },
];

export function AppShell() {
    const location = useLocation();
    const context = getShellContext(location.pathname);

    return (
        <div className="min-h-screen bg-background text-foreground lg:grid lg:grid-cols-[16rem_minmax(0,1fr)]">
            <aside className="hidden border-r border-outline-soft bg-surface lg:flex lg:min-h-screen lg:flex-col">
                <div className="border-b border-outline-soft px-5 py-4">
                    <p className="font-mono text-label font-medium uppercase text-muted">
                        AutoClaw
                    </p>
                    <p className="mt-1 font-display text-compact font-semibold">Console</p>
                </div>
                <nav aria-label="Primary" className="flex flex-1 flex-col gap-1 px-3 py-4">
                    <PrimaryNavItems pathname={location.pathname} variant="rail" />
                </nav>
            </aside>
            <div className="min-w-0">
                <header className="sticky top-0 z-10 border-b border-outline-soft bg-background/95 backdrop-blur">
                    <div className="flex min-h-16 flex-wrap items-center justify-between gap-3 px-page-inline py-3">
                        <div className="min-w-0">
                            <p className="font-mono text-label font-medium uppercase text-muted">
                                {context.section}
                            </p>
                            <div className="mt-1 flex min-w-0 flex-wrap items-center gap-2 text-utility text-muted">
                                <ClipboardList aria-hidden="true" className="size-4 shrink-0" />
                                {context.breadcrumbs.map((breadcrumb, index) => (
                                    <span
                                        className={classNames(
                                            "min-w-0 truncate",
                                            index === context.breadcrumbs.length - 1 &&
                                                "font-semibold text-foreground",
                                        )}
                                        key={`${breadcrumb}-${String(index)}`}
                                    >
                                        {index === 0 ? breadcrumb : `/ ${breadcrumb}`}
                                    </span>
                                ))}
                            </div>
                        </div>
                        <StatusChip tone="active">Console</StatusChip>
                    </div>
                    <nav
                        aria-label="Primary"
                        className="flex gap-2 overflow-x-auto px-page-inline pb-3 lg:hidden"
                    >
                        <PrimaryNavItems pathname={location.pathname} variant="mobile" />
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

function PrimaryNavItems({
    pathname,
    variant,
}: {
    readonly pathname: string;
    readonly variant: PrimaryNavVariant;
}) {
    return NAV_ITEMS.map((item) => {
        const Icon = item.icon;

        return (
            <NavLink
                className={({ isActive }) =>
                    classNames(
                        "flex h-control items-center gap-2 rounded-control px-3 text-utility font-semibold text-muted transition-colors hover:bg-surface-muted hover:text-foreground",
                        variant === "rail" && "w-full",
                        variant === "mobile" &&
                            "shrink-0 border border-outline-soft bg-surface-low",
                        (isActive || item.match(pathname)) && "bg-active text-active-foreground",
                    )
                }
                key={item.to}
                to={item.to}
            >
                <Icon aria-hidden="true" className="size-4 shrink-0" />
                <span className="truncate">{item.label}</span>
            </NavLink>
        );
    });
}

function getShellContext(pathname: string): ShellContext {
    const segments = pathname.split("/").filter((segment) => segment.length > 0);
    const taskIdSegment = segments.find((_segment, index) => index === 1);
    const taskId =
        taskIdSegment === undefined ? "Selected task" : decodeURIComponent(taskIdSegment);

    if (segments[0] === "tasks" && segments[2] === "human-requests") {
        return {
            breadcrumbs: ["Tasks", taskId, "Human Requests"],
            section: "Runtime",
        };
    }

    if (segments[0] === "tasks" && segments[2] === "command-runs") {
        return {
            breadcrumbs: ["Tasks", taskId, "Command Runs"],
            section: "Runtime",
        };
    }

    if (segments[0] === "tasks" && segments.length > 1) {
        return {
            breadcrumbs: ["Tasks", taskId],
            section: "Runtime",
        };
    }

    if (segments[0] === "definitions" && segments[1] === "editor") {
        return {
            breadcrumbs: ["Definitions", "Editor"],
            section: "Authoring",
        };
    }

    if (segments[0] === "definitions") {
        return {
            breadcrumbs: ["Definitions"],
            section: "Authoring",
        };
    }

    if (segments[0] === "task-start") {
        return {
            breadcrumbs: ["Task Start"],
            section: "Authoring",
        };
    }

    if (segments[0] === "fixtures") {
        return {
            breadcrumbs: ["Fixtures"],
            section: "Internal",
        };
    }

    return {
        breadcrumbs: ["Tasks"],
        section: "Runtime",
    };
}
