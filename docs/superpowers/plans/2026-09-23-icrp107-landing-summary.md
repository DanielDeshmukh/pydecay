# v2 ICRP-107 landing-page summary (draft for review)

**Status:** DRAFT — awaiting user approval. Do **not** edit `landingpage/**` until this is approved.
**Branch:** `feat/icrp107-pipeline` · **Version:** `0.2.0` · **Date:** 2026-09-23

---

## 1. What shipped

- **Full ICRP-107 default catalog** — 1252 radionuclides + stable progeny endpoints (1498 records total) in `src/pydecay/data/icrp107.json`, replacing the 47-nuclide IAEA bundle as the runtime source of truth.
- **Stable endpoints** — `half_life_s = inf`, `source = "ICRP-107-stable"`, chain-closed against radioactive progeny.
- **RAD/BET spectra API** — `pydecay.spectra.emissions(name)` / `beta_spectrum(name)`, lazy-loaded from gzipped artifacts (`icrp107_rad.json.gz`, 1252 nuclides; `icrp107_bet.json.gz`, 955 nuclides). Also re-exported from the package root.
- **Checksummed build pipeline** — `_fetch_icrp.py` verifies SHA-256 pins on NDX, LICENSE, and RadData tarball before writing any artifact; fetch scripts excluded from the wheel.
- **IAEA → test-only oracle** — the 47-nuclide fixture moved to `tests/fixtures/iaea_nuclides_47.json`; differential test with `REL_TOL_DATA = 1.5e-2`.
- **Version bump** — `0.2.0`; goldens and crosscheck retargeted to ICRP-107; wheel size budget (15 MB) enforced by test.

Commits: `3c6d271` … `e5cf6be` (15 commits on `feat/icrp107-pipeline`).

## 2. Accuracy story

- **Single runtime source** — no silent IAEA+ICRP merge; every shipped value comes from ICRP-107 with per-record `source` / `source_url` / `fetched`.
- **IAEA differential oracle** — independent Live Chart cross-check on 47 curated nuclides, tolerance 1.5%.
- **radioactivedecay crosscheck** — same ICRP-107 evaluation family; REL_TOL = 1e-3; stable (inf) endpoints compare equal; worst observed drift Pa-234m ≈ 9.5e-03 (accepted deviation, allowlisted).
- **Golden values** — frozen externally checked tuples with provenance (`source`, `source_url`, `note`, `verified_on`); bare numbers rejected.
- **Branch-sum invariant** — measured tolerance 0.035 on NDX data; build fails closed; no renormalization.

## 3. License callout

Code: MIT. **Data files** (`ICRP-07.NDX`, `LICENSE.ICRP-07`, RAD/BET artifacts): ICRP grants use/copy/distribute for **educational, research, and not-for-profit** purposes without fee, provided the license text accompanies all copies. **Commercial rights are not clearly granted** — flag commercial use for later review.

## 4. Suggested landing copy bullets

- Masthead version: **`0.2.0`** (currently `0.1.1` in `landingpage/src/App.tsx`).
- Data section: **“1252 ICRP-107 nuclides”** (currently “47 nuclides”).
- New spectra blurb: *“Lazy-loaded RAD/BET emission yields and beta spectra via `emissions()` / `beta_spectrum()`.”*
- Verification section: add IAEA differential oracle + radioactivedecay crosscheck line items.
- License section: mention MIT + ICRP-07 data license (non-profit terms).

## 5. Open risks

| Risk | Status |
|---|---|
| ICRP-07 commercial license terms | Not clearly granted; flag for legal review before any commercial claim |
| Official Sage/DECDATA zip URL | HTTP 403 without session; RAD/BET bootstrapped from CRAN RadData (SHA-pinned) |
| Stable nuclide mass approximation | `atomic_mass_u` set to mass number for stable endpoints |
| Wheel size growth | 15 MB budget enforced by test; currently well under |

---

**Next step:** user reviews this summary → approves → separate task/plan edits `landingpage/**`.
