import { describe, expect, it } from "vitest";

import { formatBudgetSpec } from "../../../src/features/definitions/definition-model";

describe("formatBudgetSpec", () => {
    it("renders absent budgets as unbounded", () => {
        expect(formatBudgetSpec(null)).toBe("No controller budget limit");
        expect(formatBudgetSpec({})).toBe("No controller budget limit");
    });

    it("renders only configured child-assignment budgets", () => {
        expect(formatBudgetSpec({ child_assignment_limit: 1 })).toBe("1 child assignment");
        expect(formatBudgetSpec({ child_assignment_limit: 4 })).toBe("4 child assignments");
    });

    it("renders only configured retry budgets", () => {
        expect(formatBudgetSpec({ retry_limit: 1 })).toBe("1 retry");
        expect(formatBudgetSpec({ retry_limit: 2 })).toBe("2 retries");
    });
});
