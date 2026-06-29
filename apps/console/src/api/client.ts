import { buildConsoleConfig, type ConsoleConfig } from "../app/config";

export interface ApiRequestOptions {
    readonly body?: unknown;
    readonly config?: ConsoleConfig;
    readonly method?: "DELETE" | "GET" | "POST" | "PUT";
    readonly path: string;
    readonly query?: URLSearchParams;
    readonly signal?: AbortSignal;
}

export class AutoClawApiError extends Error {
    readonly response: Response;

    constructor(response: Response, message: string) {
        super(message);
        this.name = "AutoClawApiError";
        this.response = response;
    }
}

export async function requestJson<TResponse>({
    body,
    config = buildConsoleConfig(),
    method = "GET",
    path,
    query,
    signal,
}: ApiRequestOptions): Promise<TResponse> {
    const url = new URL(path, `${config.apiBaseUrl}/`);
    if (query !== undefined) {
        url.search = query.toString();
    }

    const headers = new Headers({ Accept: "application/json" });
    if (config.apiKey !== null) {
        headers.set("X-AutoClaw-API-Key", config.apiKey);
    }
    if (body !== undefined) {
        headers.set("Content-Type", "application/json");
    }

    const response = await fetch(url, {
        body: body === undefined ? undefined : JSON.stringify(body),
        headers,
        method,
        signal,
    });

    if (!response.ok) {
        throw new AutoClawApiError(
            response,
            `AutoClaw API request failed with ${String(response.status)}`,
        );
    }

    return (await response.json()) as TResponse;
}
