# ICRP-107 Data Pipeline — Design Spec

**Date:** 2026-09-23  
**Status:** Approved (brainstorm)  
**Sub-project:** v2 roadmap #2 — ICRP-107 data pipeline  
**Supersedes:** deferred note in `docs/data-sources.md` (“Full ICRP-107 / ENSDF shipping is deferred (v2 candidate)”)

---

## 1. Goal

Give pydecay **much larger nuclide coverage** by shipping the full ICRP Publication 107 recommended decay dataset (1252 radionuclides of 97 elements, plus stable progeny endpoints needed for chains), while keeping a **single source of truth** for runtime values and an **independent accuracy oracle** (IAEA Live Chart) in tests.

Out of scope for this sub-project: ENSDF packaging, dose-coefficient math, UI beyond data access.

---

## 2. Decisions (brainstorm)

| Topic | Decision |
|-------|----------|
| Primary motivation | Much larger coverage than the current 47-nuclide IAEA bundle |
| Data access | Free public, well-documented, trusted sources; research before lock-in |
| Source path | **Raw ICRP-07 files + own parser** (not third-party JSON/R packages as runtime deps) |
| Relationship to 47 IAEA set | **ICRP-107 = runtime default catalog.** IAEA 47 retained **only as differential tests / accuracy oracle** — never mixed per-nuclide at runtime |
| Field scope | **Everything on the ICRP-07 CD set:** NDX, RAD, BET, ACK, NSF |
| Approach | **A — Staged ship** (graph+RAD bundled; BET lazy-loaded; own fetch/parse) |
| License posture | Ship `LICENSE.ICRP-07` verbatim; document educational/research/not-for-profit redistribution terms; flag commercial use for later |

**Accuracy non-goals / rules:** no silent IAEA+ICRP merge; no values from unvetted mirrors at runtime; build fails on invariant violations.

---

## 3. Trusted public sources (research)

Authoritative publication: ICRP Publication 107, *Nuclear Decay Data for Dosimetric Calculations*, Ann. ICRP 38(3), 2008 (Eckerman & Endo). CD/supplement files: five data files.

**ICRP-07 license (verbatim intent):** permission to use, copy, and distribute the data files and documentation for **educational, research, and not-for-profit** purposes without fee, provided `LICENSE.TXT` (copyright + disclaimer paragraphs) accompanies all copies. Commercial rights are **not** clearly granted.

**Raw / parseable public references:**

1. **`radioactivedecay/datasets`** (GitHub) — notebook documents Fortran format of `ICRP-07.NDX` and full parse path into half-life, modes, progeny, branching; companion `LICENSE.ICRP-07` in `radioactivedecay/radioactivedecay`. Primary **format reference** for our parser. We already differential-test solvers against `radioactivedecay`.
2. **`markhogue/RadData`** (CRAN) — tidy tables of NDX/RAD/BET; documents column meanings. **Schema reference only** (not a runtime dependency).
3. **`OpenGATE/icrp107-database`** (PyPI/GitHub) — JSON spectra packaging (~4.7 MB wheel). **Size reference**; not used as upstream data.
4. **Official ICRP supplement / DECDATA** — preferred **byte-level raw input** when a stable URL or vendored copy is available; checksum-pinned in the fetch script.

NDX Fortran format (from ICRP-107 Table 1 footnote / radioactivedecay notebook):

```text
(a7,a8,a2,a8,3i7,i6,1x,3(a7,i6,e11.0,1x),a7,i6,e11.0,f7.0,2f8.0,3i4,i5,i4,e11.0,e10.0,e9.0)
```

Encoding: **ISO-8859-1**. Radioactive record count: **1252**.

---

## 4. Architecture & data flow

```
raw ICRP-07 files (local path or pinned URL)
        │
        ▼
 _fetch_icrp.py  ── verify checksums, locate inputs
        │
        ▼
 _parse_icrp.py  ── pure parsers (NDX, RAD, BET, ACK, NSF)
        │
        ▼
 build artifacts under src/pydecay/data/
  • icrp107.json           decay graph (default catalog)
  • icrp107_rad.json       emission yields/energies
  • icrp107_bet.*          beta spectra (compressed, lazy)
  • LICENSE.ICRP-07
  • optional raw copies for audit (gitignored or LFS — decide in plan)
        │
        ├─ data loaders → nuclide.py / chain.py / api.py  (existing pure core)
        └─ spectra.py   → lazy RAD/BET on first spectra call
```

### Layering (unchanged project rule)

- `decay.py`, `graph.py`, `_solver.py` remain **pint-free**, **ICRP-format-free**.
- Only `src/pydecay/data/*` and thin edge modules (`nuclide.py`, new `spectra.py`) know about ICRP artifacts and units strings.

### Import-time behavior

- Loading the **graph** catalog is allowed at first lookup / lazy module import (same as today’s `nuclides.json` pattern — prefer lazy load on first use, cached).
- **BET (and large RAD detail) must not be read on `import pydecay`.**

---

## 5. Components

| Path | Responsibility |
|------|----------------|
| `src/pydecay/data/_fetch_icrp.py` | Resolve raw file locations (local dir or HTTP), SHA-256 verify, call parse/build. **Excluded from wheel** (same hatch `exclude` pattern as `_fetch_iaea.py`). |
| `src/pydecay/data/_parse_icrp.py` | Pure functions: `parse_ndx`, `parse_rad`, `parse_bet`, `parse_ack`, `parse_nsf` → intermediate dicts/lists. Importable without network. |
| `src/pydecay/data/icrp107.json` | Default catalog artifact. |
| `src/pydecay/data/icrp107_rad.json` | Emission table (or split by nuclide if size demands). |
| `src/pydecay/data/icrp107_bet.*` | Beta spectra, compressed; lazy open. |
| `src/pydecay/data/LICENSE.ICRP-07` | Upstream license text (required). |
| `src/pydecay/data/__init__.py` | Cached loaders: `load_catalog()`, `load_rad()`, `load_bet(name)`. |
| `src/pydecay/spectra.py` | Public optional API for emissions / beta spectra. |
| `tests/fixtures/icrp/*` | Small raw slices for parser TDD. |

No new runtime dependencies for parsing if fixed-width/Fortran fields can be parsed with stdlib; if a tiny helper is required, justify in the implementation plan (prefer **zero** new runtime deps).

---

## 6. Graph record schema

Extends today’s bundled record shape so existing `Nuclide.from_record` / `_REQUIRED_KEYS` evolve deliberately (plan will list exact key migrations).

**Fields:**

- `name` — ICRP style (`U-238`, `Tc-99m`) after `normalize_nuclide_name` compatibility  
- `half_life_s` — float seconds (`inf` for stable endpoints)  
- `half_life_raw` — original numeric + `half_life_units` string from NDX (provenance/UX)  
- `modes` — decay mode codes aligned with ICRP (A, B-, B+, EC, IT, SF, …) mapped to pydecay’s existing mode vocabulary where 1:1; **raw code retained** if mapping is lossy  
- `progeny` — list of names (≤4 radioactive branches; may include `SF` sentinel handled like radioactivedecay notebook)  
- `branching` — list of floats aligned with `progeny`  
- `source` — `"ICRP-107"`  
- `atomic_mass` — from NDX when present (optional key; document default if missing)  
- Extra NDX scalars (kerma constants, emission counts, pointers) either omitted from graph JSON or kept under `icrp_extra` — **decision in plan: omit from hot path unless needed by RAD/BET join**

**Stable progeny:** synthetic records appended at build time: `half_life_s=inf`, `modes=[]`, `progeny=[]`, `branching=[]`, `source="ICRP-107-stable"` (or AME mass if we later join masses — not required for solver).

**Invariants (build + tests fail closed):**

1. Radioactive base count == **1252** before stable augmentation.  
2. Every non-stable record: `len(progeny)==len(branching)` and `abs(sum(branching)-1.0) <= tol` (tol chosen from NDX precision in plan; start `1e-6` relative or document exact).  
3. No unknown progeny names left dangling after stable injection (closed graph for referenced set; full 1252 may reference each other).  
4. Half-lives positive or `inf`; no NaN.  
5. Checksum of raw inputs matches pin.

---

## 7. Public API

### Unchanged (names)

Existing `__all__` (13 names) keep their signatures. **Behavior change:** default nuclide lookup / catalog size becomes full ICRP-107 (document in CHANGELOG as minor version bump — **0.2.0** candidate, not patch).

### Proposed additions (confirm in plan if exposed)

```python
from pydecay.spectra import emissions, beta_spectrum  # illustrative
```

- `emissions(name)` → RAD rows (energy MeV, yield, radiation code)  
- `beta_spectrum(name)` → energy grid + spectral intensity  

Exact names/signatures finalized in the implementation plan; **do not expand `__all__` until tests exist**.

### Errors

- Reuse existing exception module for unknown nuclides / bad input.  
- Spectra: dedicated clear error if nuclide has no BET/RAD rows (e.g. stable).  
- No new exception hierarchy unless a spectra-specific type proves necessary.

---

## 8. Packaging, license, docs

- Include data files via hatch `force-include` / package data as today for `nuclides.json`.  
- Ship **`LICENSE.ICRP-07`** inside the package data; reference from root `LICENSE`, `README`, `docs/data-sources.md`, `CHANGELOG`.  
- State non-profit/educational/research restriction prominently.  
- **Wheel size budget:** define hard cap in CI (recommend **15 MB** uncompressed wheel to start; revisit if BET exceeds — still Stage A lazy).  
- Rebuild pipeline documented in `docs/data-sources.md` and `docs/development.md`.  
- Landing page / version strings: bump when release ships (separate release task).

---

## 9. Accuracy & testing strategy

| Layer | Test |
|-------|------|
| Parser | Fixture slices of NDX/RAD/BET → golden intermediate dicts |
| Catalog build | 1252 count, branch sums, closed progeny, golden nuclides (U-238, Pu-239, Tc-99m, …) exact `half_life_s` + branches |
| Differential | Overlap with current IAEA 47: relative half-life deviation threshold — **measure first**, then set (expect tighter than solver crosscheck `1e-3` if sources agree) |
| Solver regression | Existing `radioactivedecay` differential + golden values + full suite (145 tests) stay green |
| Lazy load | Monkeypatch/spy: `import pydecay` and graph-only API never `open()` BET |
| Packaging | License file present in wheel; `_fetch_icrp` absent from wheel |

**Runtime truth:** ICRP-107 only.  
**Test oracles:** IAEA table + `radioactivedecay` + golden constants.

---

## 10. Error handling (ops)

- Fetch: network/hash/missing file → non-zero exit, no partial JSON overwrite (write temp + atomic replace).  
- Parse: record count mismatch or Fortran field overflow → fail build.  
- Runtime load: missing/corrupt JSON → explicit exception with path (not empty catalog fallback).  
- Stable API path: unknown name → existing `UnknownNuclide` behavior.

---

## 11. Explicit non-goals

- No commercial-license negotiation in this sub-project (tracked as open risk).  
- No ENSDF.  
- No dose coefficients / air kerma math in v2 pipeline sub-project (fields may exist in raw data but are unused).  
- No third-party ICRP package as a **runtime** dependency.  
- No per-record hybrid IAEA/ICRP values.

---

## 12. Open items for implementation plan (not design blockers)

1. Exact raw file URLs or “user-supplied directory” bootstrap; checksum table.  
2. Branch-sum tolerance measured against real NDX.  
3. Whether ACK/NSF are vendored raw-only (no parsed JSON) until a consumer exists.  
4. Compression format for BET (e.g. `.npz` vs JSON+gzip) — prefer existing stdlib/numpy stack.  
5. Semver: **0.2.0** for catalog expansion.  
6. Confirm final public spectra function names.

---

## 13. Approval

Brainstorm path: **Architectural**. Sections §architecture, §components/schema, §API/packaging/tests each approved by product owner on 2026-09-23.

Next step per workflow: **writing-plans** skill → `docs/superpowers/plans/2026-09-23-icrp107-data-pipeline.md` after user reviews this spec.
