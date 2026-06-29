import { describe, expect, it } from "vitest";

import { buildConsoleConfig, normalizeApiBaseUrl } from "../../src/app/config";

describe("console config", () => {
    it("normalizes the configured API base URL", () => {
        expect(normalizeApiBaseUrl("http://127.0.0.1:18125///")).toBe("http://127.0.0.1:18125");
    });

    it("uses the local AutoClaw service as the default API base URL", () => {
        expect(buildConsoleConfig({}).apiBaseUrl).toBe("http://127.0.0.1:18125");
    });

    it("trims an operator API key and treats a blank key as absent", () => {
        expect(buildConsoleConfig({ VITE_AUTOCLAW_API_KEY: "  key  " }).apiKey).toBe("key");
        expect(buildConsoleConfig({ VITE_AUTOCLAW_API_KEY: "   " }).apiKey).toBeNull();
    });
});
