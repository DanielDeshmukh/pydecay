# v2 ICRP-107 Landing-Page Summary (draft)

**Status:** Draft for review — do **not** edit `landingpage/**` until this
summary is approved.

**Branch:** `feat/icrp107-pipeline` · **Version:** 0.2.0

---

## 1. What shipped

- **Full ICRP-107 default catalog** — 1252 radioactive nuclides + stable
  progeny endpoints (1498 records total), replacing the 47-nuclide IAEA
  bundle as the single runtime source of truth.
- **Checksummed pure-Python pipeline** — own NDX parser; SHA-256 pins on
  NDX, LICENSE, and RadData tarball; build fetchers excluded from the wheel.
- **RAD/BET spectra API** — `pydecay.spectra.emissions` /
  `beta_spectrum` (also re-exported from package root); lazy-loaded gzip
  artifacts (1252 RAD / 955 BET nuclides); not read on `import pydecay`.
- **IAEA → test-only oracle** — 47-nuclide fixture retained for
  differential accuracy tests only; never mixed per-nuclide at runtime.
- **Second-isomer `n` suffix** accepted in nuclide names (JNDC state id 2).

## 2. Accuracy story

- **Single runtime source:** ICRP Publication 107 everywhere
  (`icrp107.json`).
- **IAEA differential oracle:** `tests/test_iaea_differential.py`,
  `REL_TOL_DATA = 1.5e-2` (worst observed drift Pa-234m ≈ 9.5e-3).
- **radioactivedecay cross-check:** same evaluation family post-switch;
  `REL_TOL = 1e-3`; stable (inf) endpoints compare as equal.
- **Golden values:** frozen half-lives / activity / chain tuples with
  ICRP provenance; `PROVENANCE_OK_PREFIXES` includes ICRP.
- **Gates:** full suite + ruff + mypy + coverage ≥ 90% (91.78% measured)
  + wheel ≤ 15 MB.

## 3. License callout

ICRP-07 data files ship under `LICENSE.ICRP-07`:
**educational / research / not-for-profit** use without fee, provided the
license text accompanies all copies. Commercial rights are **not** clearly
granted — flag commercial use for later review. Package code remains MIT.

## 4. Suggested landing copy bullets

- Masthead / badge: version **`0.2.0`** (replace `0.1.1`).
- Data section: **“1252+ ICRP-107 nuclides (default) + spectra API”**
  (replace “47 IAEA nuclides”).
- New spectra blurb: *“Access ICRP-107 emission yields and beta spectra
  with `pydecay.spectra.emissions` / `beta_spectrum` — lazy-loaded, not
  read at import time.”*
- Verification strip: keep Bateman vs expm + cross-check; add “IAEA
  differential oracle” line if space allows.
- License footer: *“MIT code · ICRP-107 data (educational/research)”*.

## 5. Open risks

| Risk | Notes |
|---|---|
| Commercial license | ICRP-07 commercial rights unclear; revisit before commercial marketing claims. |
| Official zip 403 | Sage/ICRP direct zip URL returns HTTP 403; RAD/BET currently bootstrapped from CRAN RadData (SHA-pinned). |
| Stable mass approximation | Stable endpoints use mass number as `atomic_mass_u` (no AME refinement); fine for chain topology, not for precision mass work. |
| Year-convention drift | Systematic rel ≈ 2.136e-05 vs radioactivedecay (Julian year); two orders below tolerance. |

---

**Next step:** review this summary → approve → open a separate task/plan
for `landingpage/**` edits (masthead, data row, spectra blurb, license
line).
