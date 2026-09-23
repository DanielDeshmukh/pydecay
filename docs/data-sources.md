# Data sources

## Provenance

- **Source:** IAEA Live Chart of Nuclides (`nds.iaea.org`), JSON/CSV API.
- **Endpoint:** `https://nds.iaea.org/relnsd/v1/data?fields=ground_states&nuclides=...`
  (CSV response; requires `User-Agent: Livechart/1.0`).
- **Fetched:** 2026-09-22 via `src/pydecay/data/_fetch_iaea.py`
  (build-time tool; excluded from the wheel).
- **Metastable isomers** (`Tc-99m`, `Pa-234m`) are absent from
  `fields=ground_states`; they are read from `fields=levels` of the base
  nuclide and paired with the base ground-state mass excess plus the level
  excitation energy.
- **Bundle size:** 47 curated isotopes.
- **Per-record metadata:** every record carries `source`, `source_url`,
  and `fetched`.

## Year convention

`1 y = 31557600 s` (Julian year, 365.25 d). Applied uniformly by
`UNIT_TO_SECONDS` in the fetch script (`ys`/`Y`/`y` and scaled `ky`, `My`,
`Gy`).

## Mandatory six

Medical / industrial / dating anchors required by the design spec §6;
regeneration fails if any of these are missing:

| Nuclide | Why |
|---|---|
| Co-60 | industrial / radiotherapy |
| Cs-137 | industrial / medical |
| I-131 | medical imaging / therapy |
| C-14 | dating |
| U-238 | natural decay series |
| Tc-99m | medical imaging (metastable) |

## Limitations

- `decay_modes` is best-effort from the ground-states endpoint's
  `decay_1` / `decay_1_%` (and `decay_2`, `decay_3`) columns; rows may be
  incomplete depending on what the API reports for a given nuclide.
- Branching fractions for chain topology are **user-supplied** to
  `DecayChain.branching` — the dataset does not drive graph edges.
- Full ICRP-107 / ENSDF shipping is deferred (v2 candidate).
- `half_life_uncertainty_s` is currently `null` for all bundled records.

## Cross-check policy

`tests/test_crosscheck.py` compares every overlapping nuclide against
`radioactivedecay` (ICRP-107 evaluation). Policy:

- Print relative drift for all overlapping nuclides.
- **REL_TOL = 1e-3 locked.** Any nuclide outside the accepted-deviation
  allowlist beyond this tolerance fails the test.
- **IAEA wins conflicts** with secondary sources; these published
  evaluation differences are accepted and allowlisted in
  `ACCEPTED_DEVIATIONS` in `tests/test_crosscheck.py`.
- Any accepted deviation is listed below with both values (populated from
  observed cross-check output — not pre-invented).

### Accepted deviations (IAEA vs ICRP-107)

Note for every row: *IAEA Live Chart vs ICRP-107 evaluation difference;
accepted in `tests/test_crosscheck.py` `ACCEPTED_DEVIATIONS`.*

| Nuclide | pydecay (IAEA, s) | radioactivedecay (ICRP-107, s) | rel diff | note |
|---|---|---|---|---|
| Ar-39 | 8.457437e+09 | 8.488813e+09 | 3.696e-03 | IAEA Live Chart vs ICRP-107 evaluation difference; accepted in tests/test_crosscheck.py ACCEPTED_DEVIATIONS |
| C-11 | 1.221840e+03 | 1.223400e+03 | 1.275e-03 | IAEA Live Chart vs ICRP-107 evaluation difference; accepted in tests/test_crosscheck.py ACCEPTED_DEVIATIONS |
| Cs-137 | 949252608 | 951980944.7479681 | 2.866e-03 | IAEA Live Chart vs ICRP-107 evaluation difference; accepted in tests/test_crosscheck.py ACCEPTED_DEVIATIONS |
| I-123 | 4.760280e+04 | 4.777200e+04 | 3.542e-03 | IAEA Live Chart vs ICRP-107 evaluation difference; accepted in tests/test_crosscheck.py ACCEPTED_DEVIATIONS |
| K-40 | 3.938388e+16 | 3.947771e+16 | 2.377e-03 | IAEA Live Chart vs ICRP-107 evaluation difference; accepted in tests/test_crosscheck.py ACCEPTED_DEVIATIONS |
| Kr-85 | 3.388971e+08 | 3.394263e+08 | 1.559e-03 | IAEA Live Chart vs ICRP-107 evaluation difference; accepted in tests/test_crosscheck.py ACCEPTED_DEVIATIONS |
| Pa-234m | 6.954000e+01 | 7.020000e+01 | 9.402e-03 | IAEA Live Chart vs ICRP-107 evaluation difference; accepted in tests/test_crosscheck.py ACCEPTED_DEVIATIONS |
| Ra-224 | 3.137702e+05 | 3.162240e+05 | 7.760e-03 | IAEA Live Chart vs ICRP-107 evaluation difference; accepted in tests/test_crosscheck.py ACCEPTED_DEVIATIONS |
| S-35 | 7.548768e+06 | 7.560864e+06 | 1.600e-03 | IAEA Live Chart vs ICRP-107 evaluation difference; accepted in tests/test_crosscheck.py ACCEPTED_DEVIATIONS |
| Sr-90 | 912330216 | 908523901.8432001 | 4.190e-03 | IAEA Live Chart vs ICRP-107 evaluation difference; accepted in tests/test_crosscheck.py ACCEPTED_DEVIATIONS |
| Tc-99m | 2.162592e+04 | 2.165400e+04 | 1.297e-03 | IAEA Live Chart vs ICRP-107 evaluation difference; accepted in tests/test_crosscheck.py ACCEPTED_DEVIATIONS |
| Th-230 | 2.385250e+12 | 2.378761e+12 | 2.728e-03 | IAEA Live Chart vs ICRP-107 evaluation difference; accepted in tests/test_crosscheck.py ACCEPTED_DEVIATIONS |
| Th-232 | 4.418064e+17 | 4.433748e+17 | 3.537e-03 | IAEA Live Chart vs ICRP-107 evaluation difference; accepted in tests/test_crosscheck.py ACCEPTED_DEVIATIONS |
| Tl-201 | 2.628288e+05 | 2.624832e+05 | 1.317e-03 | IAEA Live Chart vs ICRP-107 evaluation difference; accepted in tests/test_crosscheck.py ACCEPTED_DEVIATIONS |

Systematic note: many year-scale OK rows sit at rel ≈ 2.136e-05 — a
year-convention difference (our Julian `1 y = 31557600 s` vs
radioactivedecay's internal `year_conv` ≈ 3.155691e7 s), two orders of
magnitude below tolerance and harmless.

## Golden values

`tests/golden/golden_values.json` freezes externally checked tuples for CI:

- **verified_on** records the last hand-check against the primary source
  (IAEA Live Chart; analytic formulas documented per entry).
- Entry `source` / `source_url` / `note` are mandatory -- bare numbers are
  rejected by `tests/golden/test_golden.py`.
- CI never re-fetches NNDC/IAEA; it only asserts the bundle still matches
  the frozen goldens.
- To re-verify: open each `source_url`, compare `half_life_s`, update
  `verified_on` and any changed values in the same commit.
