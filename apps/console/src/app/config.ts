export interface ConsoleEnvironment {
    readonly DEV?: boolean;
    readonly VITE_AUTOCLAW_API_BASE_URL?: string;
    readonly VITE_AUTOCLAW_API_KEY?: string;
}

export interface ConsoleConfig {
    readonly apiBaseUrl: string;
    readonly apiKey: string | null;
}

export interface ConsoleConfigLoadOptions {
    readonly env?: ConsoleEnvironment;
    readonly fetchImpl?: typeof fetch;
    readonly origin?: string;
}

const LOCAL_DEV_API_BASE_URL = "http://127.0.0.1:18125";
const RUNTIME_CONFIG_PATH = "/console/config";
const defaultConsoleEnvironment = import.meta.env as ConsoleEnvironment;
let activeConsoleConfig: ConsoleConfig | null = null;

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

export function getConsoleConfig(): ConsoleConfig {
    return activeConsoleConfig ?? buildConsoleConfig();
}

export function setConsoleConfig(config: ConsoleConfig): void {
    activeConsoleConfig = config;
}

export async function initializeConsoleConfig(
    options: ConsoleConfigLoadOptions = {},
): Promise<ConsoleConfig> {
    const config = await loadConsoleConfig(options);
    setConsoleConfig(config);
    return config;
}

export async function loadConsoleConfig({
    env = defaultConsoleEnvironment,
    fetchImpl = fetch,
    origin = globalThis.location.origin,
}: ConsoleConfigLoadOptions = {}): Promise<ConsoleConfig> {
    const environmentConfig = buildConsoleConfig(env, defaultApiBaseUrl(env, origin));
    if (env.DEV === true || environmentConfig.apiKey !== null) {
        return environmentConfig;
    }

    try {
        const response = await fetchImpl(runtimeConfigUrl(environmentConfig), {
            cache: "no-store",
            headers: new Headers({ Accept: "application/json" }),
            method: "GET",
        });
        if (!response.ok) {
            return environmentConfig;
        }
        return configFromRuntimeResponse(await response.json(), environmentConfig);
    } catch {
        return environmentConfig;
    }
}

function runtimeConfigUrl(config: ConsoleConfig): URL {
    return new URL(RUNTIME_CONFIG_PATH.replace(/^\/+/, ""), `${config.apiBaseUrl}/`);
}

function configFromRuntimeResponse(
    responseBody: unknown,
    fallbackConfig: ConsoleConfig,
): ConsoleConfig {
    if (!isRecord(responseBody)) {
        return fallbackConfig;
    }

    const apiBaseUrl =
        typeof responseBody.apiBaseUrl === "string"
            ? normalizeApiBaseUrl(responseBody.apiBaseUrl, fallbackConfig.apiBaseUrl)
            : fallbackConfig.apiBaseUrl;
    const apiKey = typeof responseBody.apiKey === "string" ? responseBody.apiKey.trim() : "";

    return {
        apiBaseUrl,
        apiKey: apiKey === "" ? fallbackConfig.apiKey : apiKey,
    };
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}
