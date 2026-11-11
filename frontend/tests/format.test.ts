import { describe, expect, it } from "vitest";

import { errorMessage, firstFieldErrors, formatDate, formatKes, formatNumber } from "@/lib/format";

describe("format helpers", () => {
  it("formats Kenyan shillings without decimals", () => {
    expect(formatKes("150000.50")).toContain("150,001");
    expect(formatKes(0)).toContain("0");
    expect(formatKes(null)).toBe("—");
  });

  it("formats numbers and dates", () => {
    expect(formatNumber(1200)).toBe("1,200");
    expect(formatDate("2025-03-04")).toBe("4 Mar 2025");
    expect(formatDate(null)).toBe("—");
  });

  it("uses safe fallbacks for errors", () => {
    expect(errorMessage(new Error("Nope"))).toBe("Nope");
    expect(errorMessage("bad")).toBe("Something went wrong. Please try again.");
    expect(firstFieldErrors({ name: ["Required"], detail: "Invalid" })).toEqual({
      name: "Required",
      detail: "Invalid",
    });
  });
});
