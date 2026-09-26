# Dose rates

Point-source exposure, air-kerma, and ambient dose-equivalent rates for the
pydecay core-40 nuclides, built on curated exposure-rate constants
(v0.6.0).

## Goal

Answer "how much radiation does this source deliver at distance *r*?"
as a pure-SI computation: activities in becquerel, distances in metres,
results in R/h, Gy/h, or Sv/h. Everything is a point-source inverse-square
calculation from tabulated coefficients - no transport, no Monte Carlo.

## The gamma convention (and citations)

Each bundled row carries the exposure-rate constant in two units:

| Field | Unit | Meaning |
|---|---|---|
| `gamma_R_cm2_mCi_h` | R·cm²·mCi⁻¹·h⁻¹ | True SI-usable constant used by the API (10 × the Risø value) |
| `gamma_R_m2_h_per_Ci` | R·m²·h⁻¹·Ci⁻¹ | Verbatim source value, kept for provenance |

The API computes:

```text
exposure [R/h] = gamma_R_cm2_mCi_h * (A_Bq / 3.7e7) / r_cm**2
air kerma [Gy/h] = exposure * 8.76e-3          # R_TO_GY_AIR
```

**Sources:**

- 31 rows: Lauridsen, B. (1982) *Table of Exposure Rate Constants and Dose
  Equivalent Rate Constants*, Risø National Laboratory, **Risø-M No. 2322**,
  Table 4 (nuclear photon lines only; X-rays and photons below 30 keV are
  omitted per the report's section 1).
- 3 fallback rows (U-235, Pu-239, Ge-68): **ICRP-107** Annex A photon
  emission probabilities (E ≥ 30 keV) evaluated with the same validated
  formula, mirroring the Risø energy cut.
- Ambient quantity: **ICRP Publication 74 (1996), Table A.21**,
  H*(10)/Ka (Sv/Gy), monoenergetic photons 10 keV - 10 MeV.
- 1 R in air = 8.76 × 10⁻³ Gy (NIST-defined exposure-to-kerma relation).

## `exposure_rate` / `air_kerma_rate` / `dose_rate`

```python
from pydecay import dose_rate, exposure_rate, air_kerma_rate

# 1 MBq of Co-60 at 1 m
dose_rate(1e6, "Co-60", r_m=1.0)          # 3.07e-7 Gy/h (air kerma)

# Low-level helpers take the constant explicitly
exposure_rate(12.987, 3.7e7, 1.0)         # 12.987 R/h  (1 mCi at 1 cm)
air_kerma_rate(12.987, 3.7e7, 1.0)        # 0.1138 Gy/h
```

- `dose_rate(activity_Bq, nuclide, r_m=1.0, *, quantity="kerma",
  gamma_R_cm2_mCi_h=None, attenuate_in_air=False)` - table lookup unless you
  pass an explicit constant (which works for any nuclide name).
- `attenuate_in_air=True` multiplies by `exp(-mu_air * r)` at 1.25 MeV as a
  free-in-air refinement.
- Nuclides without photon coefficients (H-3, C-14, Fe-55, Sr-90, Y-90,
  Po-210) raise `DoseDataError` instead of returning a misleading `0`.

## `quantity="ambient"`

```python
dose_rate(1e6, "Co-60", r_m=1.0, quantity="kerma")    # 3.07e-7 Gy/h
dose_rate(1e6, "Co-60", r_m=1.0, quantity="ambient")  # 3.57e-7 Sv/h
```

`"ambient"` multiplies the air-kerma rate by the bundled ICRP-74 H*(10)/Ka
factor (linearly interpolated at 1.25 MeV - the plan-sanctioned default
energy for this release; the factor is ~1.16 Sv/Gy there). `h_star_rate(...)`
is an alias for the ambient path and returns Sv/h.

## `Inventory.dose_rate`

```python
from pydecay import Inventory

inv = Inventory({"Co-60": 1e6, "Cs-137": 1e6})   # Bq
inv.dose_rate(r="1 m")                           # 3.84e-7 Gy/h (summed)
inv.dose_rate(r="1 m", time="30 days")           # decays first, then sums
```

- Sums `dose_rate` over every closure species with positive activity; plain
  numbers are metres, strings/pint Quantities are parsed to metres, and a
  Quantity `r` returns a Quantity (kind mirrors input).
- Seeds without coefficients (bucket-1 nuclides) raise `DoseDataError`;
  closure-only progeny without bundled rows are skipped because their
  photons are already attributed to the parent row where Risø did so
  (e.g. `137Ba m` inside the Cs-137 row).

## Limitations

- **Point source** geometry and inverse-square scaling only.
- **Narrow beam**: no skyshine, no streaming, no scatter.
- **No buildup factor** (reserved for v0.7); see [Shielding](shielding.md).
- Ambient interpolation uses a fixed 1.25 MeV, not per-nuclide spectra.
- Coefficients omit X-rays and photons below 30 keV (source convention).
- This is an engineering aid, **not a regulatory or safety-analysis tool**.

## Provenance: bundled coefficients

All 34 bundled rows (unit `gamma_R_cm2_mCi_h` in R·cm²·mCi⁻¹·h⁻¹;
`gamma_R_m2_h_per_Ci` is the verbatim source value):

| Nuclide | γ (R·cm²/mCi/h) | γ (R·m²/h/Ci, source) | Source | Page (printed) | Evidence |
|---|---:|---:|---|---|---|
| Am-241 | 0.121 | 0.0121 | Risø | 418 (PDF 422) | text |
| At-211 | 0.01 | 0.0010 | Risø | 395 (PDF 399) | text |
| Ba-133 | 2.024 | 0.2024 | Risø | 191 (PDF 195) | text |
| Bi-214 | 7.46 | 0.7460 | Risø | 396 (PDF 400) | text |
| Co-57 | 0.548 | 0.0548 | Risø | 33 (PDF 37) | text |
| Co-60 | 12.987 | 1.2987 | Risø | 35 (PDF 39) | image |
| Cs-137 | 3.224 | 0.3224 | Risø | 199 (PDF 203) | text |
| Eu-152 | 5.983 | 0.5983 | Risø | 249-250 (PDF 253-254) | image |
| F-18 | 5.895 | 0.5895 | Risø | 21 (PDF 25) | text |
| Ga-68 | 5.455 | 0.5455 | Risø | 43 (PDF 47) | text |
| Ge-68 | 5.466 | 0.5466 | ICRP-107 fallback | - | derived |
| I-125 | 0.039 | 0.0039 | Risø | 167 (PDF 171) | text |
| I-131 | 2.158 | 0.2158 | Risø | 182 (PDF 186) | text |
| In-111 | 2.039 | 0.2039 | Risø | 146 (PDF 150) | text |
| Ir-192 | 4.581 | 0.4581 | Risø | 347 (PDF 351) | text |
| K-40 | 0.779 | 0.0779 | Risø | 25 (PDF 29) | text |
| Kr-85 | 0.013 | 0.0013 | Risø | 78 (PDF 82) | text |
| Lu-177 | 0.16 | 0.0160 | Risø | 313 (PDF 317) | text |
| Mn-54 | 4.681 | 0.4681 | Risø | 32 (PDF 36) | text |
| Na-22 | 11.882 | 1.1882 | Risø | 22 (PDF 26) | text |
| Pb-210 | 0.016 | 0.0016 | Risø | 394 (PDF 398) | image |
| Pb-214 | 1.294 | 0.1294 | Risø | 396 (PDF 400) | text |
| Pu-239 | 0.00037 | 0.000037 | ICRP-107 fallback | - | derived |
| Ra-226 | 8.782 | 0.8782 | Risø (226-Ra+da row) | 399-400 (PDF 403-404) | image |
| Rb-82 | 6.247 | 0.6247 | Risø | 71 (PDF 75) | text |
| Se-75 | 2.056 | 0.2056 | Risø | 57 (PDF 61) | text |
| Tc-99m | 0.59 | 0.0590 | Risø | 123 (PDF 127) | image |
| Th-232 | 0.001 | 0.0001 | Risø | 407 (PDF 411) | text |
| Tl-201 | 0.105 | 0.0105 | Risø | 369 (PDF 373) | text |
| U-235 | 0.802 | 0.0802 | ICRP-107 fallback | - | derived |
| U-238 | 0.085 | 0.0085 | Risø | 415 (PDF 419) | image |
| Xe-133 | 0.136 | 0.0136 | Risø | 191 (PDF 195) | text |
| Yb-175 | 0.209 | 0.0209 | Risø | 306 (PDF 310) | text |
| Zn-65 | 3.105 | 0.3105 | Risø | 39 (PDF 43) | text |

Omitted (no photon coefficients; the API raises `DoseDataError`):

| Nuclide | Reason |
|---|---|
| C-14 | pure beta emitter, no photon rows in Risø-M-2322 Table 4 |
| Fe-55 | no photon emission ≥ 30 keV (EC daughter X-rays excluded by Risø §1) |
| H-3 | pure beta emitter, no photon rows in Risø-M-2322 Table 4 |
| Po-210 | no photon emission ≥ 30 keV (803 keV gamma branch absent from the table) |
| Sr-90 | pure beta emitter (Y-90 daughter has no gamma) |
| Y-90 | ground state is photon-free; the only Risø Y-90 row is the 3.190 h isomer |

The machine-readable bundle lives at
`src/pydecay/data/dose_coefficients.json` (built by
`src/pydecay/data/_curate_dose.py`).
