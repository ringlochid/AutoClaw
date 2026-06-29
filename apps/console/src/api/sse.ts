import { buildConsoleConfig, type ConsoleConfig } from "../app/config";

export function taskEventStreamUrl(
    taskId: string,
    options: {
        readonly config?: ConsoleConfig;
        readonly cursor?: string | null;
    } = {},
): string {
    const config = options.config ?? buildConsoleConfig();
    const url = new URL(
        `/control/tasks/${encodeURIComponent(taskId)}/events/stream`,
        config.apiBaseUrl,
    );

    if (options.cursor) {
        url.searchParams.set("cursor", options.cursor);
    }

    return url.toString();
}
