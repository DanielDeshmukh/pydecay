import {
  ambientDoseFactor,
  doseCoefficientRows,
  omittedPhotonNuclides,
} from "../data/doseCoefficients";

/** 1 roentgen in air -> Gy (mirrors pydecay.dose.R_TO_GY_AIR). */
export const R_TO_GY_AIR = 8.76e-3;

const BQ_PER_MCI = 3.7e7;

export type DoseQuantity = "kerma" | "ambient";

/** Exposure-rate constant in R·cm²/mCi/h for a nuclide, or null if photon-free/unknown. */
export function doseCoefficientFor(nuclideId: string): number | null {
  const row = doseCoefficientRows.find((item) => item.id === nuclideId);
  return row ? row.gammaRcm2mCiH : null;
}

/** True for the six bundled nuclides with no photon coefficients. */
export function isOmittedPhotonNuclide(nuclideId: string): boolean {
  return Object.prototype.hasOwnProperty.call(omittedPhotonNuclides, nuclideId);
}

/** Point-source exposure rate at r_cm, in R/h (inverse-square from the tabulated constant). */
export function exposureRate(gammaRcm2mCiH: number, activityBq: number, rCm: number): number {
  return (gammaRcm2mCiH * (activityBq / BQ_PER_MCI)) / (rCm * rCm);
}

/** Air-kerma rate at r_cm, in Gy/h. */
export function airKermaRate(gammaRcm2mCiH: number, activityBq: number, rCm: number): number {
  return exposureRate(gammaRcm2mCiH, activityBq, rCm) * R_TO_GY_AIR;
}

/**
 * Point-source dose rate at r metres: air kerma in Gy/h (`"kerma"`) or ambient
 * dose equivalent in Sv/h (`"ambient"`). Returns null when the nuclide has no
 * photon coefficients — pydecay raises DoseDataError on that path.
 */
export function doseRate(
  activityBq: number,
  nuclideId: string,
  rM = 1.0,
  quantity: DoseQuantity = "kerma",
): number | null {
  const gamma = doseCoefficientFor(nuclideId);
  if (gamma === null) {
    return null;
  }
  const rate = airKermaRate(gamma, activityBq, rM * 100.0);
  return quantity === "ambient" ? rate * ambientDoseFactor : rate;
}

/** Engineering-suffix parts for readouts: 3.075e-7 -> { mantissa: "307.500", suffix: "n" }. */
export function engineeringParts(value: number, digits = 3): { mantissa: string; suffix: string } {
  if (!Number.isFinite(value)) {
    return { mantissa: "—", suffix: "" };
  }
  if (value === 0) {
    return { mantissa: "0", suffix: "" };
  }
  const suffixes = [
    { limit: 1e-12, suffix: "p", exp: -12 },
    { limit: 1e-9, suffix: "n", exp: -9 },
    { limit: 1e-6, suffix: "µ", exp: -6 },
    { limit: 1e-3, suffix: "m", exp: -3 },
    { limit: 1, suffix: "", exp: 0 },
    { limit: 1e3, suffix: "k", exp: 3 },
    { limit: 1e6, suffix: "M", exp: 6 },
    { limit: 1e9, suffix: "G", exp: 9 },
  ];
  const magnitude = Math.abs(value);
  if (magnitude < 1e-12) {
    return { mantissa: value.toExponential(2), suffix: "" };
  }
  let chosen = { suffix: "", exp: 0 };
  for (const item of suffixes) {
    if (magnitude < item.limit) {
      break;
    }
    chosen = item;
  }
  return { mantissa: (value / 10 ** chosen.exp).toFixed(digits), suffix: chosen.suffix };
}

/** Format a rate with engineering suffixes: 3.075e-7 -> "307.500n". */
export function formatEngineering(value: number, digits = 3): string {
  const { mantissa, suffix } = engineeringParts(value, digits);
  return `${mantissa}${suffix}`;
}
