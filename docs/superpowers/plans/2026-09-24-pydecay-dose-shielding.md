# pydecay v0.6 — Dose & Shielding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add dose and shielding to pydecay — activity → air-kerma/exposure rate at distance (point source, photons), plus narrow-beam shielding (μ, HVL/TVL, multi-layer transmit) using bundled NIST attenuation data and a curated coefficient table — validated against published handbook values.

**Architecture:** Pure-SI modules (`dose.py`, `shielding.py`, `materials.py`) never import pint; pint parses/mirrors only at the public API edge. Build-time fetchers under `data/_fetch_nist.py` (excluded from wheel) emit `nist_mu.json.gz` + license; `_dose_data.py` loads curated `dose_coefficients.json`. Runtime never hits the network. New `Inventory.dose_rate()` composes existing activities with `dose.dose_rate`.

**Tech Stack:** Python ≥3.10; existing runtime deps only (`numpy`, `scipy`, `pint`); stdlib `gzip`/`json`/`hashlib`/`urllib` for fetchers; pytest + pytest-cov, ruff, mypy (strict); no new runtime deps.

**Spec:** `docs/superpowers/specs/2026-09-24-pydecay-dose-shielding-design.md` — executors read both. Locked signatures, tolerances, and data pins below are intentional refinements resolved at plan time.

## Global Constraints

- Interpreter: `D:\Vs Code\themis\venv\Scripts\python.exe` (Python 3.13.14). Repo: `D:\Vs Code\VS code\pydecay` on `main`.
- Console encoding cp1252 — avoid non-ASCII in shell output; files use UTF-8.
- PowerShell 5.1: no `&&`; use `;` or separate commands. Prefer `& "D:\Vs Code\themis\venv\Scripts\python.exe" ...`.
- Git commits: `git -c core.hooksPath=/dev/null add ...` then `git -c core.hooksPath=/dev/null commit -m "..."`. Identity already `DanielDeshmukh`. **Commit every task** unless a step says otherwise.
- Strict TDD: failing test → run fail → implement → run pass → commit. No production code without a test (exceptions: config/boilerplate and documentation prose).
- Layer rule: `src/pydecay/dose.py`, `shielding.py`, `materials.py` never import pint; they accept/return plain SI floats (Gy/h, m⁻¹, m, MeV, Bq).
- Units policy: `api.py` / `__init__.py` / `Inventory.dose_rate` parse via `units.to_float` / `mirror_quantity` at their public surface only.
- Existing public `__all__` keeps its current names until Task 8 adds dose/shield exports; no renames of existing APIs.
- Version target after this plan: **`0.6.0`** (new feature area = minor).
- `landingpage/**` is **out of scope** — no edits until a later approved summary (same rule as ICRP plan).
- Gates after every task that touches code:  
  `python -m pytest` · `python -m ruff check src tests` · `python -m mypy src` · coverage ≥ 90 when tests change.
- Network rule: fetchers are build-time only. If NIST is unreachable, use the manual-drop path (Task 1); never fabricate μ or Γ values.
- Do not modify `landingpage/**` in Tasks 0–7.

### Resolved open items (from spec §10)

| # | Resolution |
|---|------------|
| 1 | **Coefficient granularity:** ship a curated **core-40** set first (medical + industrial + common fission products): Co-60, Cs-137, I-131, I-125, Tc-99m, F-18, Ga-68, Lu-177, Y-90, Sr-90, C-14, H-3, Na-22, Mn-54, Fe-55, Co-57, Zn-65, Ge-68, Rb-82, Kr-85, Xe-133, Ba-133, Eu-152, Am-241, Pu-239, U-238, U-235, Th-232, K-40, Ra-226, Po-210, Pb-210, Bi-214, Pb-214, At-211, Tl-201, In-111, Yb-175, Ir-192, Se-75 — plus everything already in ICRP-107 that these alias to. Loader raises `DoseDataError` (not silent 0) for missing nuclides; API accepts explicit `gamma=` override. |
| 2 | **Buildup:** narrow-beam only in v0.6. `transmit(..., buildup=None)` keyword reserved; passing anything other than `None` raises `NotImplementedError` (ships in v0.7). Document clearly. |
| 3 | **Geometry:** point source only in v0.6. `Inventory.dose_rate` / `dose_rate` use inverse-square from `r`; no disk/volume factors. |
| 4 | **Sv vs Gy:** default quantity is **air kerma rate (Gy/h)**. `quantity=` accepts `"kerma"` (default) or `"ambient"`; `"ambient"` multiplies by bundled energy-dependent `h_star_over_ka` conversion (small table in `dose_coefficients.json`, ICRP-103/116 conversion coefficients — implementers must cite exact table). |
| 5 | **NIST license:** ship `LICENSE.nist.txt` verbatim (XCOM / NIST public-domain notice) next to `nist_mu.json.gz`. |

### Data pins (research before lock-in; update this table when locked)

| Data | Primary source | Fallback | Pin |
|------|----------------|----------|-----|
| μ/ρ vs E for Pb, Fe, H₂O, concrete, Al, air, polyethylene (0.01–20 MeV) | NIST XCOM form `https://physics.nist.gov/PhysRefData/Xcom/html/xcom1.html` (scripted POST or manual CSV) | Operator drops CSV/text into `data/raw_nist/` (gitignored) | SHA-256 recorded in `_fetch_nist.py` on first successful obtain |
| Per-nuclide Γ / air-kerma constants (core-40) | ICRP Publication 107 Annex A / published air-kerma rate constants; cross-check vs Hickman or Eckerman tables | Handbook values (Lamarsh/Cember) with citation recorded per entry | Fixture JSON records `source`, `table`, `page`, `fetched` per row |
| `h_star_over_ka` conversion | ICRP-103 / ICRP-116 published H\*(10)/Ka vs E | — | Same provenance fields |
| R ↔ Gy (air) | NIST: 1 R = 0.00876 Gy-air (0.00876 exact-by-definition of R at STP air; use CODATA-consistent `8.76e-3` with comment) | — | Constant + comment in `dose.py` |

**Accuracy non-goals:** no silent source merging; every golden fixture carries a citation; missing data raises, never returns 0.

## File Structure (create/modify map)

| Path | Responsibility | Task |
|------|----------------|------|
| Create: `src/pydecay/materials.py` | Material registry (name → density, composition id) + `mu()` interpolation over bundled NIST μ/ρ (pure SI) | 2 |
| Create: `src/pydecay/shielding.py` | `mu`, `hvl`, `tvl`, `transmit`, `transmit_slab`, `multilayer_transmit` (pure SI) | 3 |
| Create: `src/pydecay/dose.py` | `air_kerma_rate`, `exposure_rate`, `dose_rate`, beta helpers (pure SI) | 5 |
| Create: `src/pydecay/_dose_data.py` | Cached loaders for `dose_coefficients.json` + `nist_mu.json.gz` | 4 |
| Create: `src/pydecay/data/_fetch_nist.py` | Build-time NIST XCOM fetch/parse → `nist_mu.json.gz` (wheel-excluded) | 1 |
| Create: `src/pydecay/data/_curate_dose.py` | Build-time curation helper → `dose_coefficients.json` (wheel-excluded) | 4 |
| Create: `src/pydecay/data/nist_mu.json.gz` | Bundled μ/ρ tables (generated, committed) | 1 |
| Create: `src/pydecay/data/LICENSE.nist.txt` | NIST public-domain notice (committed) | 1 |
| Create: `src/pydecay/data/dose_coefficients.json` | Γ, h\*/Ka table, provenance (generated, committed) | 4 |
| Modify: `src/pydecay/exceptions.py` | Add `DoseDataError`, `MaterialError` | 6 |
| Modify: `src/pydecay/inventory.py` | `Inventory.dose_rate(r=..., quantity=...)` | 6 |
| Modify: `src/pydecay/api.py` | pint-aware wrappers if needed for parity | 6 |
| Modify: `src/pydecay/__init__.py` | Version `0.6.0`; export dose/shield/materials names | 8 |
| Modify: `pyproject.toml` | hatch exclude `_fetch_nist.py`, `_curate_dose.py`; coverage omit same | 1, 4 |
| Create: `tests/test_materials.py` | Registry + μ interpolation tests | 2 |
| Create: `tests/test_shielding.py` | HVL/TVL identities, multi-layer, errors | 3 |
| Create: `tests/test_dose_data.py` | Loader schema + provenance presence | 4 |
| Create: `tests/test_dose.py` | Known Γ values, quantity modes, distance scaling, inventory compose | 5, 6 |
| Create: `tests/fixtures/dose/*` | Golden coefficient snippets + NIST μ slices + handbook HVL values | 1, 4, 5 |
| Modify: `tests/test_inventory.py` | `dose_rate` composition tests | 6 |
| Modify: `tests/test_smoke.py`, `tests/test_api.py`, `tests/test_packaging.py` | Version + exports + wheel excludes | 8 |
| Create: `docs/dose.md`, `docs/shielding.md` | User docs + worked examples | 7 |
| Modify: `docs/api.md`, `docs/user-guide.md`, `docs/index.md`, `mkdocs.yml` | Nav + API refs | 7 |
| Modify: `README.md`, `CHANGELOG.md` | Feature bullet + `## [0.6.0] - 2026-09-XX` | 7, 8 |
| Create: `docs/superpowers/plans/2026-09-24-pydecay-dose-shielding-summary.md` | Task 9 only — **no `landingpage/` edits** | 9 |

Do **not** modify `landingpage/**` in Tasks 0–8.

---

### Task 0: Dev environment + baseline green

**Files:**
- Modify: none (commands only)

**Interfaces:**
- Consumes: existing repo at 0.5.1, all gates green.
- Produces: editable install in themis venv from **source**, green baseline.

- [x] **Step 1: Confirm editable install from this repo**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pip install -e ".[test,dev]"
& "D:\Vs Code\themis\venv\Scripts\python.exe" -c "import pydecay, pathlib; print(pydecay.__version__, pathlib.Path(pydecay.__file__).parent)"
```

Expected: `0.5.1` and path under `D:\Vs Code\VS code\pydecay\src\pydecay`. If it still resolves to `site-packages`, the editable install did not take — re-run and verify.

- [x] **Step 2: Full green baseline**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest -q
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m ruff check src tests
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m mypy src
```

Expected: all pass; coverage ≥ 90 on the pytest run (add `--cov` if the default addopts do not show it). Fix baseline failures in a separate `fix:` commit before proceeding if any fail.

- [x] **Step 3: No commit** unless Step 2 required fixes.

---

### Task 1: NIST μ/ρ data pipeline + license

**Files:**
- Create: `src/pydecay/data/_fetch_nist.py`
- Create: `src/pydecay/data/LICENSE.nist.txt`
- Create: `src/pydecay/data/nist_mu.json.gz` (generated)
- Create: `tests/fixtures/dose/nist_mu_slice.json` (small frozen slice)
- Create: `tests/test_fetch_nist.py` (parser tests; network tests skipped by default)
- Modify: `pyproject.toml` (hatch exclude + coverage omit for `_fetch_nist.py`)

**Interfaces:**
- Consumes: NIST XCOM data (scripted or manual drop).
- Produces: `nist_mu.json.gz` with schema:

```json
{
  "source": "NIST XCOM",
  "source_url": "https://physics.nist.gov/PhysRefData/Xcom/html/xcom1.html",
  "fetched": "YYYY-MM-DD",
  "units": {"E_MeV": "MeV", "mu_over_rho": "cm^2/g"},
  "materials": {
    "lead": {"density_g_cm3": 11.35, "E_MeV": [...], "mu_over_rho": [...]},
    ...
  }
}
```

- Materials required in v0.6: `lead`, `iron`, `water`, `concrete`, `aluminum`, `air`, `polyethylene`.
- Energies: log-spaced ≥ 40 points covering **0.01–20 MeV**, strictly increasing.

- [x] **Step 1: Write failing schema/parser tests**

`tests/fixtures/dose/nist_mu_slice.json`: hand-build a minimal object matching the schema above with 5 fake E/μ rows for `lead` (values clearly synthetic — parser tests only, never used as physics truth).

`tests/test_fetch_nist.py`:

```python
"""NIST XCOM fetcher parse + bundle tests (no network by default)."""

import gzip
import json
from pathlib import Path

import pytest

from pydecay.data._fetch_nist import parse_xcom_text, validate_payload

FIXTURE = Path(__file__).parent / "fixtures" / "dose" / "nist_mu_slice.json"


def test_parse_xcom_text_rows():
    text = "1.00000E-02  4.00000E+00\n1.50000E-02  2.50000E+00\n"
    rows = parse_xcom_text(text)
    assert rows[0][0] == pytest.approx(1e-2)
    assert rows[0][1] == pytest.approx(4.0)
    assert len(rows) == 2


def test_validate_payload_requires_all_materials():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # slice fixture has only lead; validate against full REQUIRED set should fail
    with pytest.raises(Exception):
        validate_payload(payload)


def test_bundled_gzip_roundtrip():
    raw = Path("src/pydecay/data/nist_mu.json.gz").read_bytes()
    data = json.loads(gzip.decompress(raw))
    assert set(data["materials"]) >= {
        "lead", "iron", "water", "concrete", "aluminum", "air", "polyethylene",
    }
    assert data["source"].startswith("NIST")
```

- [x] **Step 2: Run tests to verify they fail**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/test_fetch_nist.py -v
```

Expected: FAIL — module `pydecay.data._fetch_nist` missing; later asserts fail until bundle exists.

- [x] **Step 3: Research + obtain XCOM data (manual acceptable)**

1. Open `https://physics.nist.gov/PhysRefData/Xcom/html/xcom1.html`.
2. Prefer scripted POST of the multi-material form (materials + energies 0.01–20 MeV, 40+ log points). If the form blocks scripts, download manually and drop the raw response/text under `data/raw_nist/` (create `data/raw_nist/.gitkeep`; gitignore `data/raw_nist/*` except `.gitkeep`).
3. Record SHA-256 of the raw response in `_fetch_nist.py` as `RAW_SHA256`.

- [x] **Step 4: Implement `_fetch_nist.py`**

- `parse_xcom_text(text) -> list[tuple[float, float]]` — pure, tested in Step 1.
- `validate_payload(payload)` — requires all `REQUIRED_MATERIALS`, finite positive μ/ρ, strictly increasing E, E span ⊇ [0.01, 20] MeV.
- `build(raw_path, out_path)` — parse all materials, set densities (documented constants: Pb 11.35, Fe 7.87, H₂O 1.00, concrete 2.30, Al 2.699, air 1.205e-3 at 20 °C/1 atm, polyethylene 0.94 g/cm³ — cite sources in docstring), gzip-write `nist_mu.json.gz`.
- CLI: `python -m pydecay.data._fetch_nist --raw data/raw_nist/xcom.txt` (network fetch path if raw absent).
- Wheel exclude: add to `pyproject.toml` hatch `exclude` and `[tool.coverage.run] omit`.

- [x] **Step 5: Ship `LICENSE.nist.txt`**

Copy the NIST/XCOM public-domain/copyright notice verbatim from the XCOM page footer or NIST disclaimers page. Commit it.

- [x] **Step 6: Build bundle + green parser tests**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pydecay.data._fetch_nist --raw data\raw_nist\xcom.txt
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/test_fetch_nist.py -v
```

Expected: PASS including `test_bundled_gzip_roundtrip`.

- [x] **Step 7: Commit**

```bash
git -c core.hooksPath=/dev/null add src/pydecay/data/_fetch_nist.py src/pydecay/data/nist_mu.json.gz src/pydecay/data/LICENSE.nist.txt tests/test_fetch_nist.py tests/fixtures/dose/nist_mu_slice.json pyproject.toml data/raw_nist/.gitkeep .gitignore
git -c core.hooksPath=/dev/null commit -m "feat: bundle NIST XCOM mu/rho tables for shielding materials"
```

---

### Task 2: `materials.py` — registry + μ(E) interpolation

**Files:**
- Create: `src/pydecay/materials.py`
- Create: `tests/test_materials.py`

**Interfaces:**
- Consumes: `nist_mu.json.gz` via `_dose_data.load_nist_mu()`.
- Produces:

```python
def material(name: str) -> Material: ...          # case-insensitive registry lookup
class Material:
    name: str
    density_g_cm3: float
    def mu_over_rho(self, energy_MeV: float) -> float: ...   # cm^2/g, log-log interp
    def mu(self, energy_MeV: float) -> float: ...            # m^-1 (converts units)
def available_materials() -> tuple[str, ...]: ...
```

- Errors: unknown name → `MaterialError`; E outside [0.01, 20] → `MaterialError` (no silent clamp).
- Interpolation: linear in (log E, log μ/ρ); exact node hits return table values.

- [x] **Step 1: Write failing tests**

```python
"""Material registry and mu(E) interpolation tests."""

import pytest

from pydecay.exceptions import MaterialError
from pydecay.materials import available_materials, material


def test_available_materials_contains_core_set():
    mats = available_materials()
    for name in ("lead", "water", "concrete", "air"):
        assert name in mats


def test_lead_mu_decreases_in_pair_production_valley():
    pb = material("lead")
    mu_1mev = pb.mu(1.0)
    mu_6mev = pb.mu(6.0)
    # above ~4 MeV pair production turns up, but between 1 and ~4 mu falls;
    # assert monotone fall 1.0 -> 3.0 MeV (well-established for Pb)
    mu_3mev = pb.mu(3.0)
    assert mu_1mev > mu_3mev


def test_water_mu_approx_known_value():
    # NIST: H2O total mu/rho at 1 MeV ~ 0.0707 cm^2/g (cross-check tolerance 2%)
    water = material("water")
    assert water.mu_over_rho(1.0) == pytest.approx(0.0707, rel=0.02)


def test_energy_out_of_range_raises():
    with pytest.raises(MaterialError):
        material("lead").mu(0.005)
    with pytest.raises(MaterialError):
        material("lead").mu(25.0)


def test_unknown_material_raises():
    with pytest.raises(MaterialError):
        material("unobtanium")


def test_mu_units_are_per_meter():
    # mu = (mu/rho) * rho; water at 1 MeV ~ 0.0707 cm^2/g * 1 g/cm3 = 0.0707 cm^-1
    # = 7.07 m^-1
    water = material("water")
    assert water.mu(1.0) == pytest.approx(7.07, rel=0.03)
```

- [x] **Step 2: Run to verify FAIL**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/test_materials.py -v
```

Expected: `ModuleNotFoundError: No module named 'pydecay.materials'`.

- [x] **Step 3: Implement `materials.py`**

- Lazy-load NIST payload once (module-level cache, mirroring `data/__init__.py` `lru_cache` pattern — call `_dose_data.load_nist_mu()` which Task 4 stubs; **if Task 4 not done yet, implement `_dose_data.load_nist_mu` inline in this task as a minimal loader and keep it** — Tasks 2 and 4 may share the loader; prefer creating `_dose_data.py` here with just `load_nist_mu()` and extending it in Task 4).
- Densities come from the payload itself (written by the fetcher).
- Log-log `numpy.interp` on `log(E)`; raise `MaterialError` on OOR / unknown.
- Docstring: cite NIST XCOM + density sources.

- [x] **Step 4: Tests green + gates**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/test_materials.py -q
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m ruff check src tests
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m mypy src
```

Expected: pass.

- [x] **Step 5: Commit**

```bash
git -c core.hooksPath=/dev/null add src/pydecay/materials.py src/pydecay/_dose_data.py tests/test_materials.py
git -c core.hooksPath=/dev/null commit -m "feat: material registry with NIST-backed mu(E) interpolation"
```

---

### Task 3: `shielding.py` — HVL/TVL, transmit, multi-layer

**Files:**
- Create: `src/pydecay/shielding.py`
- Create: `tests/test_shielding.py`

**Interfaces:**
- Consumes: `materials.material`.
- Produces (all pure SI floats, no pint):

```python
def mu_from_material(material: str, energy_MeV: float) -> float: ...   # m^-1 (thin wrapper)
def hvl(mu: float) -> float: ...                                        # m, ln2/mu
def tvl(mu: float) -> float: ...                                        # m, ln10/mu
def hvl_slab(material: str, energy_MeV: float) -> float: ...
def tvl_slab(material: str, energy_MeV: float) -> float: ...
def transmit(I0: float, mu: float, x: float, *, buildup: float | None = None) -> float: ...
def transmit_slab(I0: float, material: str, thickness: float, energy_MeV: float, *, buildup: float | None = None) -> float: ...
def multilayer_transmit(I0: float, layers: Sequence[tuple[str, float]], energy_MeV: float) -> float: ...
    # layers = [(material_name, thickness_m), ...]; product of exponentials
```

- Errors: `mu <= 0` or non-finite → `ValueError`; `x < 0` → `ValueError`; `buildup is not None` → `NotImplementedError("buildup factors ship in v0.7")`; unknown material → `MaterialError`.

- [x] **Step 1: Write failing tests**

```python
"""Narrow-beam shielding identities and multi-layer composition."""

import math

import pytest

from pydecay.exceptions import MaterialError
from pydecay.shielding import hvl, hvl_slab, multilayer_transmit, transmit, transmit_slab, tvl


def test_transmit_zero_thickness_is_identity():
    assert transmit(100.0, 1.0, 0.0) == pytest.approx(100.0)


def test_hvl_halves_exactly():
    mu = 2.0
    assert transmit(100.0, mu, hvl(mu)) == pytest.approx(50.0)


def test_tvl_tenths_exactly():
    mu = 3.5
    assert transmit(100.0, mu, tvl(mu)) == pytest.approx(10.0)


def test_hvl_tvl_relationship():
    # TVL = ln10/ln2 * HVL ~ 3.3219 HVL
    mu = 4.2
    assert tvl(mu) / hvl(mu) == pytest.approx(math.log(10) / math.log(2))


def test_multilayer_equals_single_combined_mu():
    # pure attenuation: product of exps == exp of sum
    layers = [("water", 0.5), ("lead", 0.01)]
    mu_w = 7.0  # synthetic for identity test via transmit, not materials
    # identity checked with raw transmit composition:
    a = transmit(1.0, mu_w, 0.5)
    b = transmit(a, 500.0, 0.01)
    assert b == pytest.approx(math.exp(-(mu_w * 0.5 + 500.0 * 0.01)))


def test_multilayer_real_materials_order_independent():
    e = 1.25
    one = multilayer_transmit(1.0, [("lead", 0.01), ("water", 0.5)], e)
    two = multilayer_transmit(1.0, [("water", 0.5), ("lead", 0.01)], e)
    assert one == pytest.approx(two)


def test_transmit_slab_lead_co60_energy_reduces_intensity():
    i0 = 1.0
    out = transmit_slab(i0, "lead", 0.01, 1.25)
    assert 0.0 < out < 1.0


def test_buildup_reserved():
    with pytest.raises(NotImplementedError):
        transmit(1.0, 1.0, 0.1, buildup=2.0)


def test_negative_mu_rejected():
    with pytest.raises(ValueError):
        hvl(0.0)
    with pytest.raises(ValueError):
        hvl(-1.0)


def test_unknown_material_propagates():
    with pytest.raises(MaterialError):
        transmit_slab(1.0, "unobtanium", 0.1, 1.0)
```

- [x] **Step 2: Run to verify FAIL**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/test_shielding.py -v
```

- [x] **Step 3: Implement `shielding.py`**

Pure floats; docstrings cite Beer-Lambert and Google style (ruff `D` rules).

- [x] **Step 4: Tests green + gates**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/test_shielding.py -q
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m ruff check src tests
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m mypy src
```

- [x] **Step 5: Commit**

```bash
git -c core.hooksPath=/dev/null add src/pydecay/shielding.py tests/test_shielding.py
git -c core.hooksPath=/dev/null commit -m "feat: narrow-beam shielding with HVL/TVL and multi-layer transmit"
```

---

### Task 4: Curated `dose_coefficients.json` + loader

**Files:**
- Create: `src/pydecay/data/_curate_dose.py` (build-time, wheel-excluded)
- Create: `src/pydecay/data/dose_coefficients.json` (generated, committed)
- Create: `tests/fixtures/dose/dose_coefficients_slice.json`
- Create: `tests/test_dose_data.py`
- Modify: `src/pydecay/_dose_data.py` (extend with `load_dose_coefficients`)
- Modify: `pyproject.toml` (exclude + coverage omit for `_curate_dose.py`)

**Interfaces:**
- Produces `dose_coefficients.json` schema:

```json
{
  "source": "ICRP-107 Annex A (air-kerma rate constants); see per-row source",
  "fetched": "YYYY-MM-DD",
  "units": {"gamma_R_cm2_mCi_h": "R*cm^2/(mCi*h)", "air_kerma_Gy_h_per_Bq_at_1m": "Gy/h per Bq at 1 m"},
  "rows": {
    "Co-60": {"gamma_R_cm2_mCi_h": 1.32, "source": "...", "table": "...", "page": "..."},
    ...
  },
  "h_star_over_ka": {"E_MeV": [...], "factor": [...], "source": "..."}
}
```

- Loader: `_dose_data.load_dose_coefficients() -> dict` (cached); missing nuclide lookups raise `DoseDataError` at the dose API layer (Task 5), not here.

- [x] **Step 1: Research + lock golden Γ values**

Assemble core-40 table (spec §10 resolution 1). For each row record `source`, `table`, `page`. Minimum golden subset that **must** be in fixtures for tests (widely published values — verify against primary source during curation, adjust only if primary disagrees, and note the deviation in `source`):

| Nuclide | Γ (R·cm²·mCi⁻¹·h⁻¹) ≈ | Notes |
|---------|------------------------|-------|
| Co-60 | 1.32 | classic handbook |
| Cs-137 | 0.326 | classic handbook |
| I-131 | 0.24 | verify |
| Na-22 | 1.23 | verify |
| Ir-192 | 0.48 | verify |
| Tc-99m | 0.078 | verify |

Record actual locked values + citations in `tests/fixtures/dose/dose_coefficients_slice.json`.

- [x] **Step 2: Write failing loader tests**

```python
"""dose_coefficients.json schema and loader tests."""

import json
from pathlib import Path

import pytest

from pydecay import _dose_data

SLICE = Path(__file__).parent / "fixtures" / "dose" / "dose_coefficients_slice.json"


def test_slice_schema_fields():
    payload = json.loads(SLICE.read_text(encoding="utf-8"))
    for name, row in payload["rows"].items():
        assert "gamma_R_cm2_mCi_h" in row, name
        assert row.get("source"), name


def test_bundle_contains_core_nuclides():
    payload = _dose_data.load_dose_coefficients()
    for name in ("Co-60", "Cs-137", "I-131", "Tc-99m"):
        assert name in payload["rows"]


def test_h_star_table_present_and_monotone():
    payload = _dose_data.load_dose_coefficients()
    ks = payload["h_star_over_ka"]
    assert len(ks["E_MeV"]) == len(ks["factor"])
    assert ks["factor"][0] > 0
```

- [x] **Step 3: Run to verify FAIL**

- [x] **Step 4: Implement `_curate_dose.py` + extend `_dose_data.py`**

- `_curate_dose.py`: builds the JSON from an embedded source table (researched values + citations); CLI writes `dose_coefficients.json`.
- `_dose_data.load_dose_coefficients()`: `resources.files("pydecay.data").joinpath("dose_coefficients.json")`, `json.loads`, `lru_cache` — same pattern as `load_catalog`.
- hatch exclude + coverage omit for `_curate_dose.py`.

- [x] **Step 5: Build bundle + tests green + gates**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pydecay.data._curate_dose
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/test_dose_data.py -q
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m ruff check src tests
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m mypy src
```

- [x] **Step 6: Commit**

```bash
git -c core.hooksPath=/dev/null add src/pydecay/data/_curate_dose.py src/pydecay/data/dose_coefficients.json src/pydecay/_dose_data.py tests/test_dose_data.py tests/fixtures/dose/dose_coefficients_slice.json pyproject.toml
git -c core.hooksPath=/dev/null commit -m "feat: curated dose coefficient table with per-row provenance"
```

---

### Task 5: `dose.py` — air kerma, exposure, dose rate (pure SI)

**Files:**
- Create: `src/pydecay/dose.py`
- Create: `tests/test_dose.py`
- Create: `tests/fixtures/dose/golden_dose_rates.json`

**Interfaces:**
- Consumes: `_dose_data.load_dose_coefficients`, `materials.material` (for air path attenuation), existing `spectra`/RAD only if needed (v0.6 uses tabulated Γ — no RAD integration required).
- Produces:

```python
R_TO_GY_AIR = 8.76e-3  # 1 R -> Gy in air (documented)

def exposure_rate(gamma_R_cm2_mCi_h: float, activity_Bq: float, r_cm: float) -> float:
    """R/h at r from point source: scale Gamma by A and 1/r^2 (r in cm)."""

def air_kerma_rate(gamma_R_cm2_mCi_h: float, activity_Bq: float, r_cm: float) -> float:
    """Gy/h = exposure_rate * R_TO_GY_AIR."""

def dose_rate(
    activity_Bq: float,
    nuclide: str,
    r_m: float = 1.0,
    *,
    quantity: str = "kerma",   # "kerma" | "ambient"
    gamma_R_cm2_mCi_h: float | None = None,  # explicit override; skips table lookup
    attenuate_in_air: bool = False,          # optional e^-mu_air*r refinement
) -> float:
    """Point-source dose rate at r_m. Raises DoseDataError if nuclide not in table and no override."""

def h_star_rate(...) -> float: ...  # ambient (Sv/h) via quantity="ambient" path
```

- Physics notes (docstring):
  - Tabulated Γ is referenced at **1 cm** (classic convention: R·cm²·mCi⁻¹·h⁻¹ implies rate at 1 cm for that activity unit). Implementation: `rate(r) = Γ_scaled * (1/r_cm^2)` where `Γ_scaled` converts Γ × A(Bq) → R/h at 1 cm. **Lock the convention in Step 1 tests with a known published example** (e.g. 1 mCi Co-60 at 1 cm ≈ 1.32 R/h; at 100 cm ≈ 1.32e-4 R/h) — if the published example disagrees with 1/r² scaling from 1 cm, document the actual convention from the source.
  - `"ambient"`: `dose_rate * h_star_over_ka` interpolated at 1.25 MeV (or gamma-weighted if source publishes effective E — use simple 1.25 MeV default for Co-60-like, else max-γ energy of nuclide; document choice).

- [x] **Step 1: Write golden fixture + failing tests**

`tests/fixtures/dose/golden_dose_rates.json`:

```json
{
  "cases": [
    {
      "id": "co60_1mCi_1cm_exposure",
      "nuclide": "Co-60",
      "activity_Ci": 0.001,
      "r_cm": 1.0,
      "expected_R_h": 1.32,
      "rel_tol": 0.01,
      "source": "handbook Gamma x 1 mCi at 1 cm"
    },
    {
      "id": "co60_1mCi_100cm_exposure",
      "nuclide": "Co-60",
      "activity_Ci": 0.001,
      "r_cm": 100.0,
      "expected_R_h": 1.32e-4,
      "rel_tol": 0.01,
      "source": "inverse-square from same Gamma"
    },
    {
      "id": "co60_1MBq_1m_kerma",
      "nuclide": "Co-60",
      "activity_Bq": 1e6,
      "r_m": 1.0,
      "expected_Gy_h": "<computed from gamma * R_TO_GY_AIR, fill during curation>",
      "rel_tol": 0.02,
      "source": "derived"
    }
  ]
}
```

Fill the computed expectation during curation (Task 4) using locked Γ — the test asserts **your code matches published Γ math**, not a magic number.

```python
"""Dose rate known-value and behavior tests."""

import json
from pathlib import Path

import pytest

from pydecay.exceptions import DoseDataError
from pydecay.dose import R_TO_GY_AIR, air_kerma_rate, dose_rate, exposure_rate

GOLDEN = json.loads((Path(__file__).parent / "fixtures" / "dose" / "golden_dose_rates.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", GOLDEN["cases"], ids=lambda c: c["id"])
def test_golden_dose_cases(case):
    if "expected_R_h" in case:
        got = exposure_rate(
            gamma_lookup(case["nuclide"]),
            case["activity_Ci"] * 3.7e10,
            case["r_cm"],
        )
        assert got == pytest.approx(case["expected_R_h"], rel=case["rel_tol"])
    else:
        got = dose_rate(case["activity_Bq"], case["nuclide"], case["r_m"])
        assert got == pytest.approx(case["expected_Gy_h"], rel=case["rel_tol"])


def test_dose_rate_unknown_nuclide_raises():
    with pytest.raises(DoseDataError):
        dose_rate(1e6, "Not-123", 1.0)


def test_dose_rate_override_bypasses_table():
    # explicit gamma works for unknown nuclide
    val = dose_rate(3.7e7, "X-1", 1.0, gamma_R_cm2_mCi_h=1.0)
    assert val > 0


def test_distance_scaling_is_inverse_square():
    a = dose_rate(1e6, "Co-60", 1.0)
    b = dose_rate(1e6, "Co-60", 2.0)
    assert b == pytest.approx(a / 4.0)


def test_quantity_ambient_ge_kerma():
    kerma = dose_rate(1e6, "Co-60", 1.0, quantity="kerma")
    ambient = dose_rate(1e6, "Co-60", 1.0, quantity="ambient")
    assert ambient >= kerma


def test_r_to_gy_constant():
    assert R_TO_GY_AIR == pytest.approx(8.76e-3, rel=1e-3)
```

(`gamma_lookup` = thin helper reading `dose_coefficients.json` in the test.)

- [x] **Step 2: Run to verify FAIL**

- [x] **Step 3: Implement `dose.py`**

- Resolve Γ convention exactly as Step 1 golden cases document.
- `DoseDataError` does not exist yet — create it in `exceptions.py` **in this task** (Task 6 also touches exceptions; do the class add here if tests need it, Task 6 reuses).

- [x] **Step 4: Tests green + gates**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/test_dose.py -q
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m ruff check src tests
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m mypy src
```

- [x] **Step 5: Commit**

```bash
git -c core.hooksPath=/dev/null add src/pydecay/dose.py src/pydecay/exceptions.py tests/test_dose.py tests/fixtures/dose/golden_dose_rates.json
git -c core.hooksPath=/dev/null commit -m "feat: point-source exposure and air-kerma dose rates with golden checks"
```

---

### Task 6: `Inventory.dose_rate` + api edge + `MaterialError`

**Files:**
- Modify: `src/pydecay/inventory.py` (add method)
- Modify: `src/pydecay/exceptions.py` (`MaterialError` if not yet added; move `DoseDataError` there if created inline in Task 5)
- Modify: `src/pydecay/api.py` (pint-aware `dose_rate` / `hvl` wrappers if mirroring requires)
- Modify: `tests/test_inventory.py` (new cases)
- Modify: `tests/test_units.py` or new parity tests for pint edge

**Interfaces:**
- `Inventory.dose_rate(r="1 m", *, quantity="kerma") -> float | pint.Quantity`
  - Sums `dose.dose_rate(activity_Bq, nuclide, r_m)` over current inventory at `t=0` state (or accepts `time=` kwarg to decay first — mirror `Inventory.at` semantics; decide in Step 1 and document).
  - Uses pint edge: parse `r` via `to_seconds`-style `to_float(r, "meter")`; mirror result kind off `r`.
- `MaterialError` added to hierarchy.

- [x] **Step 1: Write failing inventory tests**

```python
"""Inventory dose-rate composition tests."""

import pytest

from pydecay import Inventory, Nuclide
from pydecay.dose import dose_rate


def test_inventory_dose_rate_is_sum_of_singles():
    inv = Inventory({"Co-60": 1e6, "Cs-137": 1e6})  # adjust constructor to real API
    total = inv.dose_rate(r="1 m")
    part1 = dose_rate(1e6, "Co-60", 1.0)
    part2 = dose_rate(1e6, "Cs-137", 1.0)
    assert total == pytest.approx(part1 + part2, rel=1e-9)


def test_inventory_dose_rate_mirrors_pint_input():
    import pint
    r = 1.0 * pint.UnitRegistry().meter
    val = Inventory({"Co-60": 1e6}).dose_rate(r=r)
    assert hasattr(val, "units")  # Quantity out when Quantity in
```

(Adapt `Inventory` constructor call to the real API after reading `inventory.py`.)

- [x] **Step 2: Run to verify FAIL**

- [x] **Step 3: Implement method + exceptions + pint edge**

- Prefer small pure helper in `dose.py` that takes `(activity_Bq, nuclide, r_m, ...)`; `Inventory.dose_rate` converts units and sums.
- If `time=` kwarg is supported: call `self.at(t)` (or equivalent) first, then sum activities.

- [x] **Step 4: Tests green + gates**

- [x] **Step 5: Commit**

```bash
git -c core.hooksPath=/dev/null add src/pydecay/inventory.py src/pydecay/exceptions.py src/pydecay/api.py tests/test_inventory.py
git -c core.hooksPath=/dev/null commit -m "feat: Inventory.dose_rate composing point-source rates with pint edge"
```

---

### Task 7: Docs — `dose.md`, `shielding.md`, nav, references

**Files:**
- Create: `docs/dose.md`
- Create: `docs/shielding.md`
- Modify: `mkdocs.yml` (nav entries after `units` or near `spectra`)
- Modify: `docs/api.md`, `docs/user-guide.md`, `docs/index.md`
- Modify: `README.md` (feature bullet + example snippet)
- Modify: `CHANGELOG.md` (`## [0.6.0] - 2026-09-24` under Unreleased structure)

**Interfaces:**
- Consumes: public APIs from Tasks 3–6.
- Produces: `mkdocs build --strict` green; every public function has an API entry.

- [x] **Step 1: Write `docs/dose.md`**

Sections: goal · Γ convention + citations · `dose_rate` / `exposure_rate` / `air_kerma_rate` examples · `quantity="ambient"` · `Inventory.dose_rate` · limitations (point source, narrow-beam, no buildup, not a regulatory tool) · provenance table for coefficients.

Worked example (must match tested values):

```python
from pydecay import dose_rate
dose_rate(1e6, "Co-60", r_m=1.0)  # Gy/h from 1 MBq Co-60 at 1 m
```

- [x] **Step 2: Write `docs/shielding.md`**

Sections: Beer-Lambert · HVL/TVL definitions · material table (density + μ at 1.0 / 1.25 MeV) · multi-layer example · buildup reserved-for-v0.7 note · NIST citation.

Worked example:

```python
from pydecay import material, hvl_slab, transmit_slab
pb = material("lead")
hvl_slab("lead", 1.25)   # meters
transmit_slab(1.0, "lead", 0.01, 1.25)
```

- [x] **Step 3: Wire nav + api + user-guide + README + CHANGELOG**

- `mkdocs.yml` nav: add `dose.md` and `shielding.md` after existing entries.
- `docs/api.md`: sections for dose/shielding/materials exports.
- `docs/user-guide.md`: short "Dose rates & shielding" section linking both pages.
- `README.md`: one bullet under features + keep existing examples intact.
- `CHANGELOG.md`:

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

- [x] **Step 4: Docs build gate**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m mkdocs build --strict
```

Expected: no warnings-as-errors.

- [x] **Step 5: Commit**

```bash
git -c core.hooksPath=/dev/null add docs/dose.md docs/shielding.md docs/api.md docs/user-guide.md docs/index.md mkdocs.yml README.md CHANGELOG.md
git -c core.hooksPath=/dev/null commit -m "docs: dose and shielding guides with provenance and examples"
```

---

### Task 8: Public exports, version 0.6.0, packaging gates

**Files:**
- Modify: `src/pydecay/__init__.py` (version + `__all__` additions)
- Modify: `tests/test_smoke.py`, `tests/test_api.py`, `tests/test_packaging.py`
- Modify: `pyproject.toml` (description can mention dose/shielding; keywords optional)

**Interfaces:**
- `__version__ = "0.6.0"`
- New `__all__` names (append, keep all existing):

```
"DoseDataError", "MaterialError",
"air_kerma_rate", "dose_rate", "exposure_rate",
"hvl", "hvl_slab", "mu_from_material",
"material", "available_materials",
"multilayer_transmit", "transmit", "transmit_slab", "tvl", "tvl_slab",
```

- Existing 13+ names unchanged.

- [x] **Step 1: Update smoke/api/packaging tests**

- `test_smoke.py`: assert `__version__ == "0.6.0"`.
- `test_api.py`: assert new names importable and in `__all__`; parity spot-check (plain float vs pint) for `dose_rate` / `transmit_slab`.
- `test_packaging.py`: assert `data/nist_mu.json.gz` and `data/dose_coefficients.json` and `LICENSE.nist.txt` are in the wheel; assert `_fetch_nist.py` / `_curate_dose.py` are **not** in the wheel.

- [x] **Step 2: Update `__init__.py`**

- Version bump + imports + `__all__` list (keep sorted per existing style).

- [x] **Step 3: Run tests to verify FAIL first, then green**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest -q
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m ruff check src tests
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m mypy src
```

- [x] **Step 4: Coverage + build gates**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest --cov=pydecay --cov-report=term-missing --cov-fail-under=90 -q
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m build
```

Expected: coverage ≥ 90; `dist/pydecay-0.6.0-*` artifacts; wheel size sane (add data, still well under 15 MB budget).

- [x] **Step 5: Commit**

```bash
git -c core.hooksPath=/dev/null add src/pydecay/__init__.py tests/test_smoke.py tests/test_api.py tests/test_packaging.py pyproject.toml
git -c core.hooksPath=/dev/null commit -m "release: 0.6.0 — dose and shielding public API"
```

---

### Task 9: Landing-page summary doc (no `landingpage/` edits)

**Files:**
- Create: `docs/superpowers/plans/2026-09-24-pydecay-dose-shielding-summary.md`

**Interfaces:**
- Consumes: everything above.
- Produces: a short summary (goal, API list, example snippets, 4–5 screenshot suggestions, copy-paste changelog) the user can hand to a later landing-page task. **Does not modify `landingpage/**`.**

- [x] **Step 1: Write the summary document** (bullet-style, 60–100 lines).

- [x] **Step 2: Commit**

```bash
git -c core.hooksPath=/dev/null add docs/superpowers/plans/2026-09-24-pydecay-dose-shielding-summary.md
git -c core.hooksPath=/dev/null commit -m "docs: dose/shielding landing-page handoff summary"
```

---

## Definition of Done

- [x] All tasks 0–9 checkboxes complete.
- [x] Full gates green: pytest, ruff, mypy strict, coverage ≥ 90, `mkdocs build --strict`, `python -m build`.
- [x] Wheel contains `nist_mu.json.gz`, `dose_coefficients.json`, `LICENSE.nist.txt`; excludes both `_fetch_nist.py` and `_curate_dose.py`.
- [x] `pydecay.__version__ == "0.6.0"`; new exports importable.
- [x] Golden dose cases pass against cited sources; shielding identities exact.
- [x] No `landingpage/**` changes in this plan.
- [x] CHANGELOG `0.6.0` entry present.

## Explicit non-goals (restate)

Buildup factors (v0.7) · neutron dose (v0.7+) · Monte Carlo (v0.9) · extended-source geometry · activation/depletion (v0.8) · regulatory claims · landing-page UI (separate approved task).
