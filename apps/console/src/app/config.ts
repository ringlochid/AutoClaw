export interface ConsoleEnvironment {
    readonly VITE_AUTOCLAW_API_BASE_URL?: string;
    readonly VITE_AUTOCLAW_API_KEY?: string;
}

export interface ConsoleConfig {
    readonly apiBaseUrl: string;
    readonly apiKey: string | null;
}

const DEFAULT_API_BASE_URL = "http://127.0.0.1:18125";
const defaultConsoleEnvironment = import.meta.env as ConsoleEnvironment;

export function normalizeApiBaseUrl(value: string | undefined): string {
    const trimmedValue = value?.trim();
    const rawValue =
        trimmedValue === undefined || trimmedValue === "" ? DEFAULT_API_BASE_URL : trimmedValue;
    return rawValue.replace(/\/+$/, "");
}

export function buildConsoleConfig(
    env: ConsoleEnvironment = defaultConsoleEnvironment,
): ConsoleConfig {
    const apiKey = env.VITE_AUTOCLAW_API_KEY?.trim();

    return {
        apiBaseUrl: normalizeApiBaseUrl(env.VITE_AUTOCLAW_API_BASE_URL),
        apiKey: apiKey === undefined || apiKey === "" ? null : apiKey,
    };
}
