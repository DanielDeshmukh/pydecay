# Data sources

## Runtime source: ICRP-107

- **Source:** ICRP Publication 107, *Nuclear Decay Data for Dosimetric
  Calculations* (Ann. ICRP 38(3), 2008). Catalog built from `ICRP-07.NDX`.
- **Artifact:** `src/pydecay/data/icrp107.json` — **1498 records total**,
  counted as:
  - **1252 radioactive radionuclides** — exactly the 1252 data lines in
    `ICRP-07.NDX` (one record per nuclide, not per decay branch; a nuclide
    with multiple branches is still one record).
  - **246 stable progeny endpoints** — stable daughters reached by the decay
    graph (e.g. Tc-99, Pb-206) so `Inventory` can close chains to a stable
    end without lookups failing. These carry `source = "ICRP-107-stable"`
    and `is_stable = true`.

  ICRP-107 itself documents 1,252 radionuclides; the extra 246 records are
  the stable endpoints pydecay adds for graph completeness, not duplicates
  and not decay-mode rows. Verify with:

  ```python
  from pydecay import Nuclide
  all_n = Nuclide.load_all()
  stable = sum(1 for n in all_n.values() if n.is_stable)
  assert len(all_n) == 1498 and stable == 246 and len(all_n) - stable == 1252
  ```
- **Rebuild:**

```bash
python -m pydecay.data._fetch_icrp --ndx-path path/to/ICRP-07.NDX
```

- **SHA-256 pins** (in `src/pydecay/data/_fetch_icrp.py`):

| File | SHA-256 |
|---|---|
| `ICRP-07.NDX` | `ac84a9cf1da890031c2ab81a33cba858ff637d701fca3bc33fb07c5a1d6cf2b9` |
| `LICENSE.ICRP-07` | `48b128ed84d3e2ee7693491d29fb4ecdf3d00a1e99db20ceb97a9ab36a21aa51` |
| `RadData_1.0.2.tar.gz` | `837f3369e26b43242e514e2d8e9f715cf09ddb0230079f528b11202062ecf54e` |

- **Per-record metadata:** every record carries `source`, `source_url`,
  `fetched`. Stable endpoints use `source = "ICRP-107-stable"`.
- Raw drop directory: `data/raw_icrp/` (large files gitignored; see
  `data/raw_icrp/README.md`).

## Spectra (RAD / BET)

- **Artifacts:** `src/pydecay/data/icrp107_rad.json.gz` (emission yields +
  energies, 1252 nuclides) and `src/pydecay/data/icrp107_bet.json.gz`
  (beta spectra, 955 nuclides).
- **Bootstrap:** CRAN `RadData` package (SHA-pinned; schema reference only,
  not a runtime dep) via `pyreadr` (optional extra `pydecay[icrp]`):

```bash
pip install -e ".[icrp]"
python -m pydecay.data._fetch_icrp --spectra --raddata-path path/to/RadData_1.0.2.tar.gz
```

- **Official zip:** preferred byte-level raw input when available; direct
  URL currently 403 without a session. Place extracted files under
  `data/raw_icrp/` (see README there).
- **API:** `pydecay.spectra.emissions(name)` / `beta_spectrum(name)` —
  lazy-loaded on first call; not read on `import pydecay`.

## License

`LICENSE.ICRP-07` ships with the package. ICRP grants permission to use,
copy, and distribute the data files for **educational, research, and
not-for-profit** purposes without fee, provided the license text
accompanies all copies. Commercial rights are not clearly granted —
flag commercial use for later review.

## IAEA Live Chart: test oracle only

- **Location:** `tests/fixtures/iaea_nuclides_47.json` (47 curated
  isotopes).
- **Role:** differential accuracy oracle in `tests/test_iaea_differential.py`
  with `REL_TOL_DATA = 1.5e-2`. Never mixed per-nuclide at runtime.
- ICRP-107 is the single source of truth for shipped values.

## Cross-check policy (radioactivedecay)

`tests/test_crosscheck.py` compares every overlapping nuclide against
`radioactivedecay` (same ICRP-107 evaluation family post-switch):

- Print relative drift for all overlapping nuclides.
- **REL_TOL = 1e-3 locked.** Stable (inf) endpoints compare as equal.
- Systematic year-convention note: many OK rows sit at rel ≈ 2.136e-05
  (Julian `1 y = 31557600 s` vs radioactivedecay's internal
  `year_conv` ≈ 3.155691e7 s).

### Accepted deviations (historical IAEA vs ICRP-107)

These were used when the runtime catalog was IAEA-based. ICRP-107 is now
the runtime default; the allowlist in `ACCEPTED_DEVIATIONS` documents the
published evaluation differences for reference (IAEA Live Chart vs
ICRP-107 evaluation):

| Nuclide | IAEA (s) | radioactivedecay ICRP (s) | rel diff |
|---|---|---|---|
| Ar-39 | 8.457437e+09 | 8.488813e+09 | 3.696e-03 |
| C-11 | 1.221840e+03 | 1.223400e+03 | 1.275e-03 |
| Cs-137 | 949252608 | 951980944.7479681 | 2.866e-03 |
| I-123 | 4.760280e+04 | 4.777200e+04 | 3.542e-03 |
| K-40 | 3.938388e+16 | 3.947771e+16 | 2.377e-03 |
| Kr-85 | 3.388971e+08 | 3.394263e+08 | 1.559e-03 |
| Pa-234m | 6.954000e+01 | 7.020000e+01 | 9.402e-03 |
| Ra-224 | 3.137702e+05 | 3.162240e+05 | 7.760e-03 |
| S-35 | 7.548768e+06 | 7.560864e+06 | 1.600e-03 |
| Sr-90 | 912330216 | 908523901.8432001 | 4.190e-03 |
| Tc-99m | 2.162592e+04 | 2.165400e+04 | 1.297e-03 |
| Th-230 | 2.385250e+12 | 2.378761e+12 | 2.728e-03 |
| Th-232 | 4.418064e+17 | 4.433748e+17 | 3.537e-03 |
| Tl-201 | 2.628288e+05 | 2.624832e+05 | 1.317e-03 |

## Year convention

`1 y = 31557600 s` (Julian year, 365.25 d). Applied uniformly by
`UNIT_TO_SECONDS` in the fetch script (`ys`/`Y`/`y` and scaled `ky`, `My`,
`Gy`).

## Limitations / deferred

- **ENSDF packaging** remains deferred (v2 candidate).
- `half_life_uncertainty_s` is currently `null` for all bundled records.
- Branching fractions for chain topology are **user-supplied** to
  `DecayChain.branching` — the dataset does not drive graph edges.

## Golden values

`tests/golden/golden_values.json` freezes externally checked tuples for CI:

- **verified_on** records the last hand-check against ICRP-107 / analytic
  formulas documented per entry.
- Entry `source` / `source_url` / `note` are mandatory — bare numbers are
  rejected by `tests/golden/test_golden.py`.
- CI never re-fetches external sources; it only asserts the bundle still
  matches the frozen goldens.
