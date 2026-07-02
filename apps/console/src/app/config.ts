export interface ConsoleEnvironment {
    readonly DEV?: boolean;
    readonly VITE_AUTOCLAW_API_BASE_URL?: string;
    readonly VITE_AUTOCLAW_API_KEY?: string;
}

export interface ConsoleConfig {
    readonly apiBaseUrl: string;
    readonly apiKey: string | null;
}

const LOCAL_DEV_API_BASE_URL = "http://127.0.0.1:18125";
const defaultConsoleEnvironment = import.meta.env as ConsoleEnvironment;

export function defaultApiBaseUrl(
    env: ConsoleEnvironment = defaultConsoleEnvironment,
    origin = globalThis.location.origin,
): string {
    if (env.DEV === true) {
        return LOCAL_DEV_API_BASE_URL;
    }

    const trimmedOrigin = origin.trim();
    return trimmedOrigin === "" || trimmedOrigin === "null"
        ? LOCAL_DEV_API_BASE_URL
        : trimmedOrigin;
}

export function normalizeApiBaseUrl(
    value: string | undefined,
    fallbackBaseUrl = defaultApiBaseUrl(),
): string {
    const trimmedValue = value?.trim();
    const rawValue =
        trimmedValue === undefined || trimmedValue === "" ? fallbackBaseUrl : trimmedValue;
    return rawValue.replace(/\/+$/, "");
}

export function buildConsoleConfig(
    env: ConsoleEnvironment = defaultConsoleEnvironment,
    fallbackBaseUrl = defaultApiBaseUrl(env),
): ConsoleConfig {
    const apiKey = env.VITE_AUTOCLAW_API_KEY?.trim();

    return {
        apiBaseUrl: normalizeApiBaseUrl(env.VITE_AUTOCLAW_API_BASE_URL, fallbackBaseUrl),
        apiKey: apiKey === undefined || apiKey === "" ? null : apiKey,
    };
}
