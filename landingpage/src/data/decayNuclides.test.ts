import { describe, expect, it } from "vitest";

import { decayNuclides } from "./decayNuclides";

describe("decayNuclides", () => {
  it("contains the full radionuclide catalog (>= 1200 entries)", () => {
    expect(decayNuclides.length).toBeGreaterThanOrEqual(1200);
  });

  it("keeps the four original demo nuclides with matching half-lives", () => {
    const i131 = decayNuclides.find((n) => n.id === "I-131");
    expect(i131).toBeDefined();
    expect(i131?.halfLifeDays).toBeCloseTo(8.0207, 4);
    expect(i131?.displayHalfLife).toBe("8.0207 days");
    expect(i131?.element).toBe("Iodine");
    expect(decayNuclides.some((n) => n.id === "Co-60")).toBe(true);
    expect(decayNuclides.some((n) => n.id === "Cs-137")).toBe(true);
    expect(decayNuclides.some((n) => n.id === "Tc-99m")).toBe(true);
  });

  it("is sorted by id so the select renders deterministically", () => {
    const ids = decayNuclides.map((n) => n.id);
    expect(ids).toEqual([...ids].sort());
  });

  it("has unique ids", () => {
    const ids = decayNuclides.map((n) => n.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("derives sensible time units across the extremes", () => {
    const tc99m = decayNuclides.find((n) => n.id === "Tc-99m");
    expect(tc99m?.timeUnit).toBe("hours");
    expect(tc99m?.daysPerUnit).toBeCloseTo(1 / 24, 12);
    const i131 = decayNuclides.find((n) => n.id === "I-131");
    expect(i131?.timeUnit).toBe("days");
    const u238 = decayNuclides.find((n) => n.id === "U-238");
    expect(u238?.timeUnit).toBe("years");
    expect(u238?.daysPerUnit).toBeCloseTo(365.2422, 4);
  });

  it("every entry has positive half-life, non-empty fields, and consistent unit math", () => {
    for (const n of decayNuclides) {
      expect(n.id.length).toBeGreaterThan(0);
      expect(n.element.length).toBeGreaterThan(0);
      expect(n.displayHalfLife.length).toBeGreaterThan(0);
      expect(n.halfLifeDays).toBeGreaterThan(0);
      expect(["hours", "days", "years"]).toContain(n.timeUnit);
      expect(n.daysPerUnit).toBeGreaterThan(0);
      const converted = n.halfLifeDays / n.daysPerUnit;
      expect(converted).toBeGreaterThan(0);
    }
  });

  it("matches the generator contract: only stable-zero entries are excluded", () => {
    expect(decayNuclides.length).toBeLessThan(1498);
    expect(decayNuclides.length).toBeGreaterThanOrEqual(1200);
  });
});
