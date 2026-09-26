import {
  shieldingEnergiesMeV,
  shieldingMaterials,
  type ShieldingMaterialId,
} from "../data/shieldingTables";

const ENERGIES = shieldingEnergiesMeV;
const E_MIN = ENERGIES[0];
const E_MAX = ENERGIES[ENERGIES.length - 1];

/** Type guard for the seven bundled NIST materials. */
export function isShieldingMaterial(value: string): value is ShieldingMaterialId {
  return Object.prototype.hasOwnProperty.call(shieldingMaterials, value);
}

/**
 * NIST mu/rho in cm²/g at energy_MeV, linear in (log E, log mu/rho) exactly
 * like numpy.interp on the log grid; exact node hits return the table value.
 * Returns null for unknown materials or energies outside 0.01–20 MeV
 * (pydecay raises MaterialError on those paths).
 */
export function muOverRhoCm2G(materialId: string, energyMeV: number): number | null {
  if (!isShieldingMaterial(materialId)) {
    return null;
  }
  if (!Number.isFinite(energyMeV) || energyMeV < E_MIN || energyMeV > E_MAX) {
    return null;
  }
  const mus = shieldingMaterials[materialId].muOverRhoCm2G;
  let index = 0;
  while (index < ENERGIES.length - 2 && energyMeV > ENERGIES[index + 1]) {
    index += 1;
  }
  const eLow = ENERGIES[index];
  const eHigh = ENERGIES[index + 1];
  if (energyMeV === eLow) {
    return mus[index];
  }
  if (energyMeV === eHigh) {
    return mus[index + 1];
  }
  const t = (Math.log(energyMeV) - Math.log(eLow)) / (Math.log(eHigh) - Math.log(eLow));
  return Math.exp(Math.log(mus[index]) + t * (Math.log(mus[index + 1]) - Math.log(mus[index])));
}

/**
 * Linear attenuation coefficient mu in m⁻¹ (cm²/g × g/cm³ = cm⁻¹, ×100 = m⁻¹).
 * Null mirrors pydecay's MaterialError for unknown/out-of-range input.
 */
export function muFromMaterial(materialId: string, energyMeV: number): number | null {
  const muOverRho = muOverRhoCm2G(materialId, energyMeV);
  if (muOverRho === null) {
    return null;
  }
  const densityGcm3 = shieldingMaterials[materialId as ShieldingMaterialId].densityGcm3;
  return muOverRho * densityGcm3 * 100.0;
}

/** Half-value layer in m: ln2 / mu. Null when mu is unusable. */
export function hvl(mu: number | null): number | null {
  if (mu === null || !Number.isFinite(mu) || mu <= 0) {
    return null;
  }
  return Math.LN2 / mu;
}

/** Tenth-value layer in m: ln10 / mu. Null when mu is unusable. */
export function tvl(mu: number | null): number | null {
  if (mu === null || !Number.isFinite(mu) || mu <= 0) {
    return null;
  }
  return Math.log(10) / mu;
}

/** Half-value layer in m for a material at an energy. */
export function hvlSlab(materialId: string, energyMeV: number): number | null {
  return hvl(muFromMaterial(materialId, energyMeV));
}

/** Tenth-value layer in m for a material at an energy. */
export function tvlSlab(materialId: string, energyMeV: number): number | null {
  return tvl(muFromMaterial(materialId, energyMeV));
}

/**
 * Narrow-beam Beer-Lambert transmission through a slab: I0 * exp(-mu * x).
 * Thickness in metres (same convention as pydecay.transmit_slab).
 */
export function transmitSlab(
  i0: number,
  materialId: string,
  thicknessM: number,
  energyMeV: number,
): number | null {
  if (!Number.isFinite(thicknessM) || thicknessM < 0) {
    return null;
  }
  const mu = muFromMaterial(materialId, energyMeV);
  if (mu === null) {
    return null;
  }
  return i0 * Math.exp(-mu * thicknessM);
}
