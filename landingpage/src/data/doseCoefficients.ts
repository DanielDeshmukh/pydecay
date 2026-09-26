// Generated from src/pydecay/data/dose_coefficients.json — do not edit by hand.

export type DoseCoefficientRow = {
  id: string;
  /** Air-kerma exposure-rate constant, R·cm²/mCi/h (true value, 10× the Risø table display). */
  gammaRcm2mCiH: number;
  /** Provenance tag for the source table. */
  table: string;
};

export const doseCoefficientRows: DoseCoefficientRow[] = [
  { id: "Am-241", gammaRcm2mCiH: 0.121, table: "Risoe-M-2322 Table 4" },
  { id: "At-211", gammaRcm2mCiH: 0.01, table: "Risoe-M-2322 Table 4" },
  { id: "Ba-133", gammaRcm2mCiH: 2.024, table: "Risoe-M-2322 Table 4" },
  { id: "Bi-214", gammaRcm2mCiH: 7.46, table: "Risoe-M-2322 Table 4" },
  { id: "Co-57", gammaRcm2mCiH: 0.548, table: "Risoe-M-2322 Table 4" },
  { id: "Co-60", gammaRcm2mCiH: 12.987, table: "Risoe-M-2322 Table 4" },
  { id: "Cs-137", gammaRcm2mCiH: 3.224, table: "Risoe-M-2322 Table 4" },
  { id: "Eu-152", gammaRcm2mCiH: 5.983, table: "Risoe-M-2322 Table 4" },
  { id: "F-18", gammaRcm2mCiH: 5.895, table: "Risoe-M-2322 Table 4" },
  { id: "Ga-68", gammaRcm2mCiH: 5.455, table: "Risoe-M-2322 Table 4" },
  { id: "Ge-68", gammaRcm2mCiH: 5.466, table: "ICRP-107 Annex A" },
  { id: "I-125", gammaRcm2mCiH: 0.039, table: "Risoe-M-2322 Table 4" },
  { id: "I-131", gammaRcm2mCiH: 2.158, table: "Risoe-M-2322 Table 4" },
  { id: "In-111", gammaRcm2mCiH: 2.039, table: "Risoe-M-2322 Table 4" },
  { id: "Ir-192", gammaRcm2mCiH: 4.581, table: "Risoe-M-2322 Table 4" },
  { id: "K-40", gammaRcm2mCiH: 0.779, table: "Risoe-M-2322 Table 4" },
  { id: "Kr-85", gammaRcm2mCiH: 0.013, table: "Risoe-M-2322 Table 4" },
  { id: "Lu-177", gammaRcm2mCiH: 0.16, table: "Risoe-M-2322 Table 4" },
  { id: "Mn-54", gammaRcm2mCiH: 4.681, table: "Risoe-M-2322 Table 4" },
  { id: "Na-22", gammaRcm2mCiH: 11.882, table: "Risoe-M-2322 Table 4" },
  { id: "Pb-210", gammaRcm2mCiH: 0.016, table: "Risoe-M-2322 Table 4" },
  { id: "Pb-214", gammaRcm2mCiH: 1.294, table: "Risoe-M-2322 Table 4" },
  { id: "Pu-239", gammaRcm2mCiH: 0.00037, table: "ICRP-107 Annex A" },
  { id: "Ra-226", gammaRcm2mCiH: 8.782, table: "Risoe-M-2322 Table 4" },
  { id: "Rb-82", gammaRcm2mCiH: 6.247, table: "Risoe-M-2322 Table 4" },
  { id: "Se-75", gammaRcm2mCiH: 2.056, table: "Risoe-M-2322 Table 4" },
  { id: "Tc-99m", gammaRcm2mCiH: 0.59, table: "Risoe-M-2322 Table 4" },
  { id: "Th-232", gammaRcm2mCiH: 0.001, table: "Risoe-M-2322 Table 4" },
  { id: "Tl-201", gammaRcm2mCiH: 0.105, table: "Risoe-M-2322 Table 4" },
  { id: "U-235", gammaRcm2mCiH: 0.802, table: "ICRP-107 Annex A" },
  { id: "U-238", gammaRcm2mCiH: 0.085, table: "Risoe-M-2322 Table 4" },
  { id: "Xe-133", gammaRcm2mCiH: 0.136, table: "Risoe-M-2322 Table 4" },
  { id: "Yb-175", gammaRcm2mCiH: 0.209, table: "Risoe-M-2322 Table 4" },
  { id: "Zn-65", gammaRcm2mCiH: 3.105, table: "Risoe-M-2322 Table 4" },
];

/** Nuclides with no photon coefficients: pydecay raises DoseDataError for these. */
export const omittedPhotonNuclides: Record<string, string> = {
  "C-14": "pure beta emitter, no photon rows in Risoe-M-2322 Table 4",
  "Fe-55": "no photon emission >=30 keV (EC daughter Mn-55 X-rays excluded by Risoe sec. 1)",
  "H-3": "pure beta emitter, no photon rows in Risoe-M-2322 Table 4",
  "Po-210": "no photon emission >=30 keV (803 keV gamma branch absent from Risoe table)",
  "Sr-90": "pure beta emitter (Y-90 daughter has no gamma; ground-state Y-90 omitted)",
  "Y-90": "ground state is photon-free; the only Risoe Y-90 row is the 3.190 h isomer",
};

/** ICRP-74 Table A.21 H*(10)/Ka, linearly interpolated at 1.25 MeV (Co-60 average gamma). */
export const ambientDoseFactor = 1.16;
