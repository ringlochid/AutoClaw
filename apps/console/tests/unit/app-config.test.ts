import { afterEach, describe, expect, it, vi } from "vitest";

import {
    buildConsoleConfig,
    defaultApiBaseUrl,
    getConsoleConfig,
    initializeConsoleConfig,
    loadConsoleConfig,
    normalizeApiBaseUrl,
    setConsoleConfig,
} from "../../src/app/config";

afterEach(() => {
    setConsoleConfig(buildConsoleConfig({ DEV: true }));
});

describe("console config", () => {
    it("normalizes the configured API base URL", () => {
        expect(normalizeApiBaseUrl("http://127.0.0.1:18125///")).toBe("http://127.0.0.1:18125");
    });

    it("uses the local AutoClaw service as the development API base URL", () => {
        expect(buildConsoleConfig({ DEV: true }).apiBaseUrl).toBe("http://127.0.0.1:18125");
    });

    it("uses same-origin API requests for packaged production builds", () => {
        expect(defaultApiBaseUrl({ DEV: false }, "http://127.0.0.1:19000")).toBe(
            "http://127.0.0.1:19000",
        );
        expect(buildConsoleConfig({ DEV: false }, "http://127.0.0.1:19000").apiBaseUrl).toBe(
            "http://127.0.0.1:19000",
        );
    });

    it("trims an operator API key and treats a blank key as absent", () => {
        expect(buildConsoleConfig({ VITE_AUTOCLAW_API_KEY: "  key  " }).apiKey).toBe("key");
        expect(buildConsoleConfig({ VITE_AUTOCLAW_API_KEY: "   " }).apiKey).toBeNull();
    });

    it("loads same-origin runtime config for packaged production builds", async () => {
        const fetchImpl = vi.fn<typeof fetch>(() => {
            return Promise.resolve(
                new Response(
                    JSON.stringify({
                        apiBaseUrl: "http://127.0.0.1:18125///",
                        apiKey: "  runtime-key  ",
                    }),
                    { status: 200 },
                ),
            );
        });

        const config = await loadConsoleConfig({
            env: { DEV: false },
            fetchImpl,
            origin: "http://127.0.0.1:18125",
        });
        expect(fetchImpl).toHaveBeenCalledTimes(1);
        const requestCall = fetchImpl.mock.calls[0];
        const [requestUrl, requestInit] = requestCall;
        const requestHref =
            requestUrl instanceof URL
                ? requestUrl.href
                : requestUrl instanceof Request
                  ? requestUrl.url
                  : requestUrl;

        expect(requestHref).toBe("http://127.0.0.1:18125/console/config");
        expect(requestInit?.cache).toBe("no-store");
        expect(requestInit?.method).toBe("GET");
        expect(new Headers(requestInit?.headers).get("Accept")).toBe("application/json");
        expect(config).toEqual({
            apiBaseUrl: "http://127.0.0.1:18125",
            apiKey: "runtime-key",
        });
    });

    it("keeps environment config when an API key is already provided", async () => {
        const fetchImpl = vi.fn<typeof fetch>();

        const config = await loadConsoleConfig({
            env: { DEV: false, VITE_AUTOCLAW_API_KEY: " env-key " },
            fetchImpl,
            origin: "http://127.0.0.1:18125",
        });

        expect(fetchImpl).not.toHaveBeenCalled();
        expect(config).toEqual({
            apiBaseUrl: "http://127.0.0.1:18125",
            apiKey: "env-key",
        });
    });

    it("updates the active config after runtime initialization", async () => {
        const fetchImpl = vi.fn<typeof fetch>(() => {
            return Promise.resolve(
                new Response(
                    JSON.stringify({
                        apiBaseUrl: "http://127.0.0.1:19000",
                        apiKey: "runtime-key",
                    }),
                    { status: 200 },
                ),
            );
        });
        setConsoleConfig({ apiBaseUrl: "http://old.example", apiKey: null });

        await initializeConsoleConfig({
            env: { DEV: false },
            fetchImpl,
            origin: "http://127.0.0.1:18125",
        });

        expect(getConsoleConfig()).toEqual({
            apiBaseUrl: "http://127.0.0.1:19000",
            apiKey: "runtime-key",
        });
    });
});
