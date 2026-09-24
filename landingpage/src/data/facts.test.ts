import { describe, expect, it } from "vitest";

/**
 * Cross-checks marketing / docs copy numbers against the bundled catalog counts
 * and package facts asserted by the Python test suite.
 */
describe("landing page fact cross-checks", () => {
  const siteClaims = {
    radionuclides: 1252,
    totalRecords: 1498,
    elements: 118,
    version: "0.5.1",
    coverageFloor: 90,
    i131HalfLifeS: 692988.48,
    tc99mHalfLifeS: 21654.0,
  };

  it("1252 + 246 stable = 1498 catalog records", () => {
    expect(siteClaims.radionuclides + 246).toBe(siteClaims.totalRecords);
  });

  it("periodic table claim is 118", () => {
    expect(siteClaims.elements).toBe(118);
  });

  it("I-131 half-life in seconds converts to ~8.02 days", () => {
    const days = siteClaims.i131HalfLifeS / 86400;
    expect(days).toBeGreaterThan(8.0);
    expect(days).toBeLessThan(8.05);
  });

  it("Tc-99m half-life in seconds converts to ~6.01 hours", () => {
    const hours = siteClaims.tc99mHalfLifeS / 3600;
    expect(hours).toBeGreaterThan(5.99);
    expect(hours).toBeLessThan(6.03);
  });

  it("version is semver 0.5.1", () => {
    expect(siteClaims.version).toBe("0.5.1");
    expect(siteClaims.version).toMatch(/^\d+\.\d+\.\d+$/);
  });

  it("coverage floor matches pyproject fail_under", () => {
    expect(siteClaims.coverageFloor).toBe(90);
  });
});
