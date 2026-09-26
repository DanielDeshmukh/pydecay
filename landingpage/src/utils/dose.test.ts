import { describe, expect, it } from "vitest";
import { doseCoefficientRows } from "../data/doseCoefficients";
import {
  R_TO_GY_AIR,
  airKermaRate,
  doseCoefficientFor,
  doseRate,
  exposureRate,
  formatEngineering,
  isOmittedPhotonNuclide,
} from "./dose";

describe("exposureRate", () => {
  it("returns the tabulated constant for 1 mCi at 1 cm", () => {
    expect(exposureRate(12.987, 3.7e7, 1.0)).toBeCloseTo(12.987, 12);
  });

  it("falls off as inverse square", () => {
    expect(exposureRate(12.987, 3.7e7, 10)).toBeCloseTo(0.12987, 12);
    expect(exposureRate(12.987, 3.7e7, 100)).toBeCloseTo(0.0012987, 12);
  });
});

describe("airKermaRate", () => {
  it("converts R/h to Gy/h with the documented 8.76e-3 factor", () => {
    expect(airKermaRate(12.987, 3.7e7, 1.0)).toBeCloseTo(12.987 * R_TO_GY_AIR, 12);
  });
});

describe("doseCoefficientFor", () => {
  it("returns the Co-60 constant (true R·cm²/mCi/h, 10× the Risø display)", () => {
    expect(doseCoefficientFor("Co-60")).toBe(12.987);
  });

  it("returns null for photon-free and unknown nuclides", () => {
    expect(doseCoefficientFor("Sr-90")).toBeNull();
    expect(doseCoefficientFor("Xx-999")).toBeNull();
  });
});

describe("isOmittedPhotonNuclide", () => {
  it("flags exactly the six photon-free nuclides", () => {
    const flagged = doseCoefficientRows
      .map((row) => row.id)
      .filter((id) => isOmittedPhotonNuclide(id));
    expect(flagged).toEqual([]);
    for (const id of ["H-3", "C-14", "Fe-55", "Sr-90", "Y-90", "Po-210"]) {
      expect(isOmittedPhotonNuclide(id)).toBe(true);
    }
    expect(isOmittedPhotonNuclide("Co-60")).toBe(false);
  });
});

describe("doseRate", () => {
  it("matches pydecay's Co-60 golden: 1e6 Bq at 1 m, air kerma", () => {
    // pydecay: dose_rate(1e6, "Co-60") -> 3.0747600000000005e-07 Gy/h
    expect(doseRate(1e6, "Co-60")).toBeCloseTo(3.07476e-7, 15);
  });

  it("matches pydecay's ambient golden (Sv/h)", () => {
    // pydecay: dose_rate(1e6, "Co-60", quantity="ambient") -> 3.5667216000000003e-07
    expect(doseRate(1e6, "Co-60", 1.0, "ambient")).toBeCloseTo(3.5667216e-7, 15);
    const kerma = doseRate(1e6, "Co-60") as number;
    const ambient = doseRate(1e6, "Co-60", 1.0, "ambient") as number;
    expect(ambient / kerma).toBeCloseTo(1.16, 12);
  });

  it("follows inverse square with distance", () => {
    const at1 = doseRate(1e6, "Co-60", 1.0) as number;
    const at2 = doseRate(1e6, "Co-60", 2.0) as number;
    const at05 = doseRate(1e6, "Co-60", 0.5) as number;
    expect(at2).toBeCloseTo(at1 / 4, 20);
    expect(at05).toBeCloseTo(at1 * 4, 20);
  });

  it("scales linearly with activity", () => {
    const a = doseRate(1e6, "Cs-137") as number;
    const b = doseRate(2e6, "Cs-137") as number;
    expect(b).toBeCloseTo(a * 2, 20);
  });

  it("returns null for the six photon-free nuclides (pydecay DoseDataError)", () => {
    for (const id of ["H-3", "C-14", "Fe-55", "Sr-90", "Y-90", "Po-210"]) {
      expect(doseRate(1e6, id)).toBeNull();
    }
  });

  it("returns null for unknown nuclides", () => {
    expect(doseRate(1e6, "Xx-999")).toBeNull();
  });

  it("produces a finite positive rate for every bundled row", () => {
    for (const row of doseCoefficientRows) {
      const rate = doseRate(1e6, row.id);
      expect(rate).not.toBeNull();
      expect(rate as number).toBeGreaterThan(0);
    }
  });
});

describe("formatEngineering", () => {
  it("uses engineering suffixes", () => {
    expect(formatEngineering(3.07476e-7)).toBe("307.476n");
    expect(formatEngineering(0.5131)).toBe("513.100m");
    expect(formatEngineering(42.5)).toBe("42.500");
    expect(formatEngineering(1500)).toBe("1.500k");
    expect(formatEngineering(0)).toBe("0");
  });

  it("falls back to exponential below pico", () => {
    expect(formatEngineering(1.2e-15)).toBe("1.20e-15");
  });
});
