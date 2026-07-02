import { setConsoleConfig } from "../../src/app/config";

import { TEST_API_BASE_URL, TEST_API_KEY } from "./console-api";

export function installTestConsoleConfig(apiKey: string | null = TEST_API_KEY): void {
    setConsoleConfig({
        apiBaseUrl: TEST_API_BASE_URL,
        apiKey,
    });
}
