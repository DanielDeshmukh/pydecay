# pydecay v0.6 "Dose & Shielding" - landing-page handoff summary

> For a later, separately approved landing-page task. **This plan never
> modified `landingpage/**`.** Copy-paste ready.

## Goal (one paragraph)

pydecay 0.6 adds **dose rates** and **narrow-beam shielding** to the decay
math toolkit: point-source exposure / air-kerma / ambient H*(10) rates from
34 curated per-nuclide coefficients (31 Risø-M-2322 rows + 3 ICRP-107
fallbacks, full provenance per row), plus Beer-Lambert transmission, HVL/TVL,
and multi-layer slabs over seven bundled NIST XCOM materials (0.01-20 MeV).
Pure-SI core, pint at the edge, no network at runtime.

## New public API (v0.6.0)

- Dose: `dose_rate`, `exposure_rate`, `air_kerma_rate`,
  `Inventory.dose_rate()`; exceptions `DoseDataError`, `MaterialError`.
- Shielding: `material`, `available_materials`, `mu_from_material`,
  `hvl`, `hvl_slab`, `tvl`, `tvl_slab`, `transmit`, `transmit_slab`,
  `multilayer_transmit` (buildup reserved for v0.7).
- All are top-level exports; `__version__ == "0.6.0"`; `__all__` = 42 names.
- Data: `data/dose_coefficients.json` (provenance per row), `data/nist_mu.json.gz`,
  `data/LICENSE.nist.txt` - all wheel-included; generator scripts wheel-excluded.

## Example snippets (verified outputs)

```python
from pydecay import dose_rate, Inventory, hvl_slab, transmit_slab

# 1 MBq Co-60 at 1 m -> air kerma / ambient (Sv) dose rate
dose_rate(1e6, "Co-60", r_m=1.0)                     # 3.07e-7 Gy/h
dose_rate(1e6, "Co-60", r_m=1.0, quantity="ambient") # 3.57e-7 Sv/h

# Whole inventory, summed over the progeny closure (pint in -> pint out)
Inventory({"Co-60": 1e6, "Cs-137": 1e6}).dose_rate(r="1 m")   # 3.84e-7 Gy/h

# Narrow-beam shielding (NIST XCOM tables bundled)
hvl_slab("lead", 1.25)                    # 0.0104 m (Co-60 mean gamma)
transmit_slab(1.0, "lead", 0.01, 1.25)    # 0.513 through 1 cm Pb
```

## Screenshot suggestions (4-5)

1. **Dose hero**: `dose_rate(1e6, "Co-60", r_m=1.0)` result beside the
   provenance table row for Co-60 (12.987 R·cm²/mCi/h, Risø p.35).
2. **Inventory sum**: `Inventory(...).dose_rate(r="1 m")` one-liner with the
   inverse-square curve (Gy/h vs distance) as the visual.
3. **Shielding card**: HVL/TVL table (lead 1.04 cm / 3.45 cm @1.25 MeV)
   with a before/after bar: 1 cm Pb -> 51% transmission.
4. **Materials strip**: the 7 NIST materials with densities and mu @1.25 MeV.
5. **Trust/footnote**: "34 coefficients, provenance per row, 6 photon-free
   nuclides raise instead of returning 0" + Risø/ICRP-74/NIST citations.

## Copy-paste changelog

```markdown
## [0.6.0] - 2026-09-24

### Added
- Point-source air-kerma and exposure dose rates (`dose_rate`, `exposure_rate`, `air_kerma_rate`)
  with curated per-nuclide coefficients and optional ambient H*(10) quantity.
- Narrow-beam shielding: `mu`, `hvl`, `tvl`, `transmit`, `transmit_slab`, `multilayer_transmit`
  backed by bundled NIST XCOM attenuation tables for seven materials.
- `Inventory.dose_rate()` composing per-nuclide rates.
- New exceptions: `DoseDataError`, `MaterialError`.
```

## Citations for the page footer

- Risø-M-2322 (Lauridsen 1982), Table 4 - exposure-rate constants.
- ICRP-107 Annex A - 3 fallback rows (U-235, Pu-239, Ge-68).
- ICRP Publication 74 (1996), Table A.21 - H*(10)/Ka.
- NIST XCOM photon cross sections - attenuation tables (7 materials).
