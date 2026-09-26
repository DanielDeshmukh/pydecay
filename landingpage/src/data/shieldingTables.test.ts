import { describe, expect, it } from "vitest";
import {
  shieldingEnergiesMeV,
  shieldingMaterialOrder,
  shieldingMaterials,
} from "./shieldingTables";

describe("shieldingEnergiesMeV", () => {
  it("has 45 strictly ascending log-spaced points spanning 0.01-20 MeV", () => {
    expect(shieldingEnergiesMeV).toHaveLength(45);
    expect(shieldingEnergiesMeV[0]).toBe(0.01);
    expect(shieldingEnergiesMeV[44]).toBe(20);
    for (let i = 1; i < shieldingEnergiesMeV.length; i += 1) {
      expect(shieldingEnergiesMeV[i]).toBeGreaterThan(shieldingEnergiesMeV[i - 1]);
    }
  });
});

describe("shieldingMaterials", () => {
  it("lists the seven NIST materials in display order", () => {
    expect(shieldingMaterialOrder).toEqual([
      "air",
      "aluminum",
      "concrete",
      "iron",
      "lead",
      "polyethylene",
      "water",
    ]);
  });

  it("carries one mu/rho value per table energy and sane densities", () => {
    const expectedDensities: Record<string, number> = {
      air: 0.001205,
      aluminum: 2.699,
      concrete: 2.3,
      iron: 7.87,
      lead: 11.35,
      polyethylene: 0.94,
      water: 1.0,
    };
    for (const id of shieldingMaterialOrder) {
      const material = shieldingMaterials[id];
      expect(material.muOverRhoCm2G).toHaveLength(shieldingEnergiesMeV.length);
      expect(material.densityGcm3).toBe(expectedDensities[id]);
      for (const value of material.muOverRhoCm2G) {
        expect(value).toBeGreaterThan(0);
      }
    }
  });
});
