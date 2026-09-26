import { describe, expect, it } from "vitest";
import { shieldingEnergiesMeV, shieldingMaterials } from "../data/shieldingTables";
import {
  hvl,
  hvlSlab,
  isShieldingMaterial,
  muFromMaterial,
  muOverRhoCm2G,
  transmitSlab,
  tvl,
  tvlSlab,
} from "./shielding";

describe("isShieldingMaterial", () => {
  it("accepts the seven bundled materials", () => {
    for (const name of ["air", "aluminum", "concrete", "iron", "lead", "polyethylene", "water"]) {
      expect(isShieldingMaterial(name)).toBe(true);
    }
    expect(isShieldingMaterial("unobtanium")).toBe(false);
  });
});

describe("muFromMaterial", () => {
  it("matches pydecay's lead value at 1.25 MeV", () => {
    // pydecay: mu_from_material("lead", 1.25) -> 66.73067360071543 m^-1
    expect(muFromMaterial("lead", 1.25)).toBeCloseTo(66.73067360071543, 9);
  });

  it("returns the exact table node at an exact energy", () => {
    const lead = shieldingMaterials.lead;
    const nodeIndex = 10;
    const node = shieldingEnergiesMeV[nodeIndex];
    expect(muOverRhoCm2G("lead", node)).toBe(lead.muOverRhoCm2G[nodeIndex]);
    expect(muFromMaterial("lead", node)).toBeCloseTo(
      lead.muOverRhoCm2G[nodeIndex] * lead.densityGcm3 * 100,
      9,
    );
  });

  it("orders materials by stopping power at 1.25 MeV", () => {
    const mu = (id: string) => muFromMaterial(id, 1.25) as number;
    expect(mu("lead")).toBeGreaterThan(mu("iron"));
    expect(mu("iron")).toBeGreaterThan(mu("concrete"));
    expect(mu("concrete")).toBeGreaterThan(mu("water"));
    expect(mu("water")).toBeGreaterThan(mu("air"));
  });

  it("returns null out of span, for bad energies, and unknown materials", () => {
    expect(muFromMaterial("lead", 0.005)).toBeNull();
    expect(muFromMaterial("lead", 25)).toBeNull();
    expect(muFromMaterial("lead", Number.NaN)).toBeNull();
    expect(muFromMaterial("unobtanium", 1.25)).toBeNull();
  });

  it("stays finite and positive for every material at every table energy", () => {
    for (const [id, material] of Object.entries(shieldingMaterials)) {
      for (const energy of shieldingEnergiesMeV) {
        const mu = muFromMaterial(id, energy);
        expect(mu, `${id} @ ${energy} MeV`).not.toBeNull();
        expect(mu as number).toBeGreaterThan(0);
        expect(Number.isFinite(mu as number)).toBe(true);
      }
      expect(material.muOverRhoCm2G.length).toBe(shieldingEnergiesMeV.length);
    }
  });
});

describe("hvl and tvl", () => {
  it("matches pydecay's lead slab values at 1.25 MeV", () => {
    // pydecay: hvl_slab("lead", 1.25) -> 0.010387234882528055 m
    // pydecay: tvl_slab("lead", 1.25) -> 0.034505647384463975 m
    expect(hvlSlab("lead", 1.25)).toBeCloseTo(0.010387234882528055, 10);
    expect(tvlSlab("lead", 1.25)).toBeCloseTo(0.034505647384463975, 10);
  });

  it("keeps tvl/hvl = ln10/ln2", () => {
    const half = hvlSlab("concrete", 1.25) as number;
    const tenth = tvlSlab("concrete", 1.25) as number;
    expect(tenth / half).toBeCloseTo(Math.log(10) / Math.LN2, 12);
  });

  it("rejects unusable mu", () => {
    expect(hvl(null)).toBeNull();
    expect(hvl(0)).toBeNull();
    expect(hvl(-1)).toBeNull();
    expect(tvl(null)).toBeNull();
  });
});

describe("transmitSlab", () => {
  it("matches pydecay's 1 cm lead transmission at 1.25 MeV", () => {
    // pydecay: transmit_slab(1.0, "lead", 0.01, 1.25) -> 0.5130886016239941
    expect(transmitSlab(1, "lead", 0.01, 1.25)).toBeCloseTo(0.5130886016239941, 12);
  });

  it("returns I0 through zero thickness", () => {
    expect(transmitSlab(1, "lead", 0, 1.25)).toBe(1);
  });

  it("halves intensity per half-value layer", () => {
    const half = hvlSlab("iron", 1.0) as number;
    expect(transmitSlab(1, "iron", half, 1.0)).toBeCloseTo(0.5, 10);
  });

  it("returns null for negative thickness or unusable input", () => {
    expect(transmitSlab(1, "lead", -0.01, 1.25)).toBeNull();
    expect(transmitSlab(1, "lead", 0.01, 99)).toBeNull();
    expect(transmitSlab(1, "unobtanium", 0.01, 1.25)).toBeNull();
  });
});
