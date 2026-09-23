import { describe, expect, it } from "vitest";
import { demoNuclides, featuredIsotopes, type DemoNuclide } from "./nuclides";

describe("demoNuclides data integrity", () => {
  it("has exactly four demo nuclides", () => {
    expect(demoNuclides).toHaveLength(4);
  });

  it("covers I-131, Co-60, Cs-137, Tc-99m", () => {
    expect(demoNuclides.map((n) => n.id).sort()).toEqual(["Co-60", "Cs-137", "I-131", "Tc-99m"]);
  });

  const eachNuclide = (name: string, fn: (nuclide: DemoNuclide) => void) => {
    for (const nuclide of demoNuclides) {
      it(`${nuclide.id} ${name}`, () => fn(nuclide));
    }
  };

  eachNuclide("has positive halfLifeDays and daysPerUnit", (nuclide) => {
    expect(nuclide.halfLifeDays).toBeGreaterThan(0);
    expect(nuclide.daysPerUnit).toBeGreaterThan(0);
    expect(Number.isFinite(nuclide.halfLifeDays)).toBe(true);
    expect(Number.isFinite(nuclide.daysPerUnit)).toBe(true);
  });

  eachNuclide("has matching element and id prefix", (nuclide) => {
    const symbol = nuclide.id.split("-")[0];
    expect(nuclide.element.length).toBeGreaterThan(0);
    expect(symbol).toMatch(/^[A-Z][a-z]?$/);
  });

  eachNuclide("timeUnit matches daysPerUnit convention", (nuclide) => {
    if (nuclide.timeUnit === "days") expect(nuclide.daysPerUnit).toBe(1);
    if (nuclide.timeUnit === "years") expect(nuclide.daysPerUnit).toBe(365.2422);
    if (nuclide.timeUnit === "hours") expect(nuclide.daysPerUnit).toBe(1 / 24);
  });

  it("I-131 is 8.0228 days", () => {
    const i131 = demoNuclides.find((n) => n.id === "I-131");
    expect(i131).toBeDefined();
    expect(i131!.halfLifeDays).toBeCloseTo(8.0228, 6);
    expect(i131!.displayHalfLife).toBe("8.0228 days");
  });

  it("Co-60 display years match halfLifeDays / 365.2422", () => {
    const co60 = demoNuclides.find((n) => n.id === "Co-60");
    const years = co60!.halfLifeDays / 365.2422;
    expect(years).toBeCloseTo(5.27, 2);
    expect(co60!.displayHalfLife).toBe("5.27 years");
  });

  it("Cs-137 display years match halfLifeDays / 365.2422", () => {
    const cs137 = demoNuclides.find((n) => n.id === "Cs-137");
    const years = cs137!.halfLifeDays / 365.2422;
    expect(years).toBeCloseTo(30.09, 1);
    expect(cs137!.displayHalfLife).toBe("30.09 years");
  });

  it("Tc-99m display hours match halfLifeDays * 24", () => {
    const tc99m = demoNuclides.find((n) => n.id === "Tc-99m");
    const hours = tc99m!.halfLifeDays * 24;
    expect(hours).toBeCloseTo(6.01, 1);
    expect(tc99m!.displayHalfLife).toBe("6.01 hours");
  });

  it("Tc-99m is the shortest-lived demo (hours, not days/years)", () => {
    const tc99m = demoNuclides.find((n) => n.id === "Tc-99m")!;
    const i131 = demoNuclides.find((n) => n.id === "I-131")!;
    expect(tc99m.halfLifeDays).toBeLessThan(i131.halfLifeDays);
    expect(tc99m.timeUnit).toBe("hours");
  });

  it("Cs-137 is longer-lived than Co-60", () => {
    const cs137 = demoNuclides.find((n) => n.id === "Cs-137")!;
    const co60 = demoNuclides.find((n) => n.id === "Co-60")!;
    expect(cs137.halfLifeDays).toBeGreaterThan(co60.halfLifeDays);
  });
});

describe("featuredIsotopes", () => {
  it("maps I, Co, Cs, Tc to demo ids", () => {
    expect(featuredIsotopes).toEqual({
      I: "I-131",
      Co: "Co-60",
      Cs: "Cs-137",
      Tc: "Tc-99m",
    });
  });

  it("every featured id exists in demoNuclides", () => {
    const ids = new Set(demoNuclides.map((n) => n.id));
    for (const id of Object.values(featuredIsotopes)) {
      expect(ids.has(id)).toBe(true);
    }
  });
});
