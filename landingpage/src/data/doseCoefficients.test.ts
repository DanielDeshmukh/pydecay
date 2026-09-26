import { describe, expect, it } from "vitest";
import { ambientDoseFactor, doseCoefficientRows, omittedPhotonNuclides } from "./doseCoefficients";

describe("doseCoefficientRows", () => {
  it("has 34 sorted, unique nuclide ids", () => {
    expect(doseCoefficientRows).toHaveLength(34);
    const ids = doseCoefficientRows.map((row) => row.id);
    expect(ids).toEqual([...ids].sort());
    expect(new Set(ids).size).toBe(34);
  });

  it("carries the true Co-60 constant (10× the Risø display value)", () => {
    const co60 = doseCoefficientRows.find((row) => row.id === "Co-60");
    expect(co60?.gammaRcm2mCiH).toBe(12.987);
  });

  it("has strictly positive constants with provenance tags", () => {
    for (const row of doseCoefficientRows) {
      expect(row.gammaRcm2mCiH).toBeGreaterThan(0);
      expect(row.table.length).toBeGreaterThan(0);
    }
  });
});

describe("omittedPhotonNuclides", () => {
  it("documents exactly the six photon-free nuclides", () => {
    expect(Object.keys(omittedPhotonNuclides).sort()).toEqual(
      ["C-14", "Fe-55", "H-3", "Po-210", "Sr-90", "Y-90"].sort(),
    );
    for (const why of Object.values(omittedPhotonNuclides)) {
      expect(why.length).toBeGreaterThan(10);
    }
  });
});

describe("ambientDoseFactor", () => {
  it("is the ICRP-74 H*(10)/Ka value at 1.25 MeV", () => {
    expect(ambientDoseFactor).toBe(1.16);
  });
});
