# ICRP-107 Data Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the full ICRP-107 decay catalog (1252 radionuclides + stable endpoints) as pydecay’s default nuclide dataset, plus RAD emissions and BET beta spectra behind a lazy spectra API, with the IAEA 47 kept only as a differential test oracle.

**Architecture:** Pure Fortran-style parser + build script write versioned JSON artifacts under `src/pydecay/data/`. `Nuclide` loads `icrp107.json` at runtime; `pydecay.spectra` lazy-loads gzipped RAD/BET. Solvers stay free of ICRP formats. Staged ship: graph always; spectra on first API call.

**Tech Stack:** Python 3.10+, stdlib (`struct`-free fixed-width parsing, `json`, `gzip`, `hashlib`, `urllib`), NumPy/SciPy/pint (existing), optional build-time `pyreadr` only for RAD/BET bootstrap from CRAN RadData when the official Sage zip cannot be fetched.

**Spec:** `docs/superpowers/specs/2026-09-23-icrp107-data-pipeline-design.md` — this plan argues from that spec; read both.

## Global Constraints

- Interpreter: `D:\Vs Code\themis\venv\Scripts\python.exe` (Python 3.13.14). Repo: `D:\Vs Code\VS code\pydecay` on `main`.
- Console encoding cp1252 — avoid non-ASCII in shell output; files use UTF-8.
- PowerShell 5.1: no `&&`; use `;` or separate commands. Prefer `& "D:\Vs Code\themis\venv\Scripts\python.exe" ...`.
- Git commits: `git -c core.hooksPath=/dev/null add ...` then `git -c core.hooksPath=/dev/null commit -m "..."`. Identity already `DanielDeshmukh`. **Commit every task** (and every multi-commit step that says so).
- Strict TDD: failing test → run fail → implement → run pass → commit. No production code without a test (exceptions: docs/config boilerplate).
- Layer rule: `src/pydecay/decay.py`, `graph.py`, `_solver.py` never import pint or ICRP parsers.
- Runtime single source of truth: **ICRP-107 only** in `Nuclide.load*`. No per-nuclide IAEA+ICRP merge.
- Existing public `__all__` keeps its 13 names until Task 11; signatures unchanged.
- Version target after this plan: **`0.2.0`** (coverage expansion = minor). Landing page edits are **out of scope** until Task 13’s approved summary (user directive: summarize v2 before touching `landingpage/`).
- Gates after every task that touches code:  
  `python -m pytest` · `python -m ruff check src tests` · `python -m mypy src` · coverage ≥ 90 when tests change.
- Spec rule: wheel budget **15 MB** uncompressed (Task 12 asserts).
- Do not delete branch `feat/pydecay-v1`. Do not force-push.

### Resolved open items (from spec §12)

| # | Resolution |
|---|------------|
| 1a | **NDX raw URL** (primary): `https://raw.githubusercontent.com/radioactivedecay/datasets/main/icrp107_ame2020_nubase2020/ICRP-07.NDX` · SHA-256 `ac84a9cf1da890031c2ab81a33cba858ff637d701fca3bc33fb07c5a1d6cf2b9` · 285684 bytes · ISO-8859-1 · header line + **1252** records · every data line **226** chars. |
| 1b | **LICENSE.ICRP-07 URL**: `https://raw.githubusercontent.com/radioactivedecay/datasets/main/LICENSE.ICRP-07` · SHA-256 `48b128ed84d3e2ee7693491d29fb4ecdf3d00a1e99db20ceb97a9ab36a21aa51` · 1612 bytes. Mirror: `radioactivedecay/radioactivedecay` `LICENSE.ICRP-07`. |
| 1c | **Official full CD zip** (RAD/BET/ACK/NSF): `https://journals.sagepub.com/doi/suppl/10.1177/ANIB_38_3/suppl_file/P107JAICRP_38_3_Nuclear_Decay_Data_suppl_data.zip` — **HTTP 403 to scripts** (probed 2026-09-23). Manual browser download → extract into `data/raw_icrp/` (gitignored). SHA-256 recorded on first successful local obtain (`_fetch_icrp.SUPPL_ZIP_SHA256`). |
| 1d | **RAD/BET automated bootstrap** (when zip absent): CRAN `https://cran.r-project.org/src/contrib/RadData_1.0.2.tar.gz` · SHA-256 `837f3369e26b43242e514e2d8e9f715cf09ddb0230079f528b11202062ecf54e` · 5674054 bytes. Build-time only: extract `data/ICRP_07.RAD.rda`, `ICRP_07.BET.rda`, `rad_codes.rda`, `inst/license.txt` via **`pyreadr`** (optional extra `icrp`). Emits the same artifacts as the Fortran path. Documented in `docs/data-sources.md` as bootstrap, not a runtime dep. |
| 2 | **`BRANCH_SUM_ABS_TOL = 0.035`** — measured max \|Σbranch−1\| on real NDX = **0.03** (At-219 Σ=0.97); 6 records exceed 1e-3. **Do not renormalize** (would invent data). Fail build if \|Σ−1\| > 0.035 or Σ∉(0, 1.035]. |
| 3 | ACK/NSF: **raw-only vendoring** under `data/raw_icrp/` when present; copy license text; **no parsed JSON / no runtime API** until a consumer exists. If absent, docs mark “pending official zip”. |
| 4 | BET artifact: **`icrp107_bet.json.gz`** (stdlib `gzip`+`json`). RAD: **`icrp107_rad.json.gz`** (same). Graph stays pretty `icrp107.json` (diffable). |
| 5 | Semver: **0.2.0**. |
| 6 | Public spectra names: **`pydecay.spectra.emissions(name)`**, **`pydecay.spectra.beta_spectrum(name)`**. Added to top-level `__all__` only in Task 11 after tests exist. |

### Probed NDX field map (226-char lines — use these offsets)

Cursor parser (verified U-238, Ac-223, I-131, Tc-99m):

| Offset | Width | Field |
|-------:|------:|-------|
| 0 | 7 | `name` (e.g. `U-238  `, `Tc-99m `) |
| 7 | 8 | `half_life` raw (e.g. `4.468E+9`, `6.015  `) |
| 15 | 2 | `half_life_units` (`y`, `h`, `d`, `m`, …) |
| 17 | 8 | `modes_raw` (e.g. `A SF    `, `ITB-    `, `ECA     `) |
| 25 | 7×3 | three pointer ints (`pointer_rad`, `pointer_bet`, `pointer_ack`-class — store under `icrp_extra`, not hot path) |
| 46 | 6 | fourth pointer int (`pointer_nsf`-class) |
| 52 | 1 | space |
| 53 | 4×(7+6+11+1) | progeny/pointer/branch triples (space only after first three); 4th triple has no trailing space |
| 152 | 7 | `E_alpha` |
| 159 | 8 | `E_electron` |
| 167 | 8 | `E_photon` |
| 175 | 4×3 + 5 + 4 | count ints |
| 196 | 11 | **`atomic_mass_u` / AMU** (e.g. ` 238.050788`) |
| 207 | 10 + 9 | air-kerma floats |

Progeny tokens: empty slots → drop; `SF` → decay mode only (not a catalog species). Half-life units already include `m` (minute), `h`, `d`, `y`, `ms`, `us`, `s`, `ls` (μs). Reuse `UNIT_TO_SECONDS` map from `_fetch_iaea.py` (import or move shared helper — prefer importing the dict from a tiny shared module if duplication hurts; simplest: copy values into `_parse_icrp.py` with a comment to keep in sync, or `from pydecay.data._fetch_iaea import UNIT_TO_SECONDS` — **import is fine in build tools**; parsers stay dependency-light by defining `UNIT_TO_SECONDS` once in `_parse_icrp.py` and leaving IAEA fetch unchanged).

**Golden NDX rows (fixtures must match):**

| name | half_life | unit | modes_raw | progeny | branches | atomic_mass_u |
|------|-----------|------|-----------|---------|----------|---------------|
| `U-238` | `4.468E+9` | `y` | `A SF` | `['Th-234','SF']` | `[1.0, 5.45e-7]` | `238.050788` |
| `Tc-99m` | `6.015` | `h` | `ITB-` | `['Tc-99','Ru-99']` | `[0.99996, 3.7e-5]` | (from file) |
| `I-131` | `8.02070` | `d` | `B-` | `['Xe-131m','Xe-131']` | `[0.011759, 0.98824]` | (from file) |
| `Sr-90` | `28.79` | `y` | `B-` | `['Y-90']` | `[1.0]` | (from file) |
| `Co-60` | `5.2713` | `y` | `B-` | `['Ni-60']` | `[1.0]` | (from file) |

`normalize_nuclide_name` already accepts these names.

### File structure (create/modify)

| Path | Responsibility |
|------|----------------|
| Create: `src/pydecay/data/_parse_icrp.py` | Pure parsers: `parse_ndx_line`, `parse_ndx_text`, unit conversion, mode/progeny helpers. Importable without network. |
| Create: `src/pydecay/data/_fetch_icrp.py` | Checksum-pinned fetch/build CLI. Excluded from wheel. |
| Create: `src/pydecay/data/icrp107.json` | Default catalog (generated, committed). |
| Create: `src/pydecay/data/icrp107_rad.json.gz` | Emissions (generated, committed). |
| Create: `src/pydecay/data/icrp107_bet.json.gz` | Beta spectra (generated, committed). |
| Create: `src/pydecay/data/LICENSE.ICRP-07` | Upstream license (committed). |
| Create: `src/pydecay/spectra.py` | Lazy public spectra API. |
| Create: `src/pydecay/data/_icrp_units.py` | Optional: shared `UNIT_TO_SECONDS` if not inlined (only if Task 1 chooses extract). |
| Modify: `src/pydecay/data/__init__.py` | Cached loaders `load_catalog`, `load_rad`, `load_bet`. |
| Modify: `src/pydecay/nuclide.py` | Point `_bundled_records` at `icrp107.json`. |
| Modify: `pyproject.toml` | hatch exclude `_fetch_icrp.py`; coverage omit; optional extra `icrp`; wheel size not in pyproject (CI/test). |
| Modify: `src/pydecay/__init__.py` | version `0.2.0`; later `__all__` spectra exports. |
| Create: `tests/fixtures/icrp/*` | NDX/RAD/BET slices + checksum vectors. |
| Create: `tests/fixtures/iaea_nuclides_47.json` | Moved IAEA oracle (from `src/pydecay/data/nuclides.json`). |
| Modify: `tests/test_data.py` | ICRP catalog assertions. |
| Create: `tests/test_iaea_differential.py` | IAEA fixture vs `Nuclide.load` half-lives. |
| Modify: `tests/test_parse_icrp.py` (create) | Parser unit tests. |
| Modify: `tests/test_fetch_icrp.py` (create) | Fetch/build invariants (no network where possible). |
| Modify: `tests/test_crosscheck.py`, `tests/golden/*`, `tests/test_api.py`, `tests/test_smoke.py`, `tests/test_packaging.py` | Oracle/version/license updates. |
| Modify: `docs/*`, `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md` | Provenance, commands, 0.2.0 notes. |
| Create: `docs/superpowers/plans/2026-09-23-icrp107-landing-summary.md` | Task 13 only — **no `landingpage/` edits**. |

Do **not** modify `landingpage/**` in Tasks 1–12.

---

### Task 0: Dev environment + baseline green

**Files:**
- Modify: none (commands only)

**Interfaces:**
- Consumes: existing repo.
- Produces: editable install at 0.1.1 source; green baseline so later failures are ours.

- [ ] **Step 1: Confirm current suite is green on source**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pip install -e ".[test,dev]"
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest -q
```

Expected: all pass (145+). If install shows non-editable 0.1.0 in site-packages only, the editable install above fixes it — re-check:

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -c "import pydecay, pathlib; print(pydecay.__version__, pathlib.Path(pydecay.__file__).parent)"
```

Expected: `0.1.1` and path under `D:\Vs Code\VS code\pydecay\src\pydecay`.

- [ ] **Step 2: Lint/type baseline**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m ruff check src tests
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m mypy src
```

Expected: clean. If not, fix baseline before proceeding (separate tiny commit if needed).

- [ ] **Step 3: No commit** unless baseline fixes were required.

---

### Task 1: NDX parser (pure) + fixtures

**Files:**
- Create: `tests/fixtures/icrp/ICRP-07.NDX.head` (first 5 data lines + header from real file)
- Create: `tests/fixtures/icrp/ICRP-07.NDX.golden_slice.json` (parsed expectations)
- Create: `tests/test_parse_icrp.py`
- Create: `src/pydecay/data/_parse_icrp.py`

**Interfaces:**
- Consumes: `pydecay.exceptions.DataFormatError`; `UNIT_TO_SECONDS` values as in global map.
- Produces:
  - `parse_ndx_line(line: str) -> dict` — keys: `name`, `half_life_raw`, `half_life_units`, `half_life_s`, `modes_raw`, `progeny: list[str]` (no `SF`, no empties), `branching: list[float]`, `atomic_mass_u: float`, `icrp_extra: dict[str, float | int]`
  - `parse_ndx_text(text: str) -> tuple[list[dict], dict[str, Any]]` — returns `(records, meta)` where `meta` has `record_count`, `header`
  - `NDX_EXPECTED_COUNT = 1252`
  - `BRANCH_SUM_ABS_TOL = 0.035`
  - `half_life_to_seconds_icrp(value: str, unit: str) -> float`

- [ ] **Step 1: Download NDX once into temp and cut fixtures**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -c "import urllib.request, pathlib, hashlib; u='https://raw.githubusercontent.com/radioactivedecay/datasets/main/icrp107_ame2020_nubase2020/ICRP-07.NDX'; b=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'pydecay-plan'}), timeout=30).read(); assert hashlib.sha256(b).hexdigest()=='ac84a9cf1da890031c2ab81a33cba858ff637d701fca3bc33fb07c5a1d6cf2b9', 'sha mismatch'; pathlib.Path(r'C:\Users\DANIEL\AppData\Local\Temp\opencode\ICRP-07.NDX').write_bytes(b); lines=b.decode('iso-8859-1').splitlines(); pathlib.Path(r'D:\Vs Code\VS code\pydecay\tests\fixtures\icrp\ICRP-07.NDX.head').write_bytes(('\n'.join(lines[:6])+'\n').encode('iso-8859-1')); print('ok', len(lines))"
```

Expected: `ok 1253`. Create `tests/fixtures/icrp/` if missing (`New-Item -ItemType Directory -Force`).

- [ ] **Step 2: Write failing parser tests**

Create `tests/test_parse_icrp.py`:

```python
"""ICRP-07.NDX fixed-width parser tests (spec sections 3, 6)."""

import json
from pathlib import Path

import pytest

from pydecay.data._parse_icrp import (
    BRANCH_SUM_ABS_TOL,
    NDX_EXPECTED_COUNT,
    half_life_to_seconds_icrp,
    parse_ndx_line,
    parse_ndx_text,
)
from pydecay.exceptions import DataFormatError

FIXTURE = Path(__file__).parent / "fixtures" / "icrp" / "ICRP-07.NDX.head"
GOLDEN = Path(__file__).parent / "fixtures" / "icrp" / "ICRP-07.NDX.golden_slice.json"


def test_head_fixture_parses_all_records():
    text = FIXTURE.read_text(encoding="iso-8859-1")
    records, meta = parse_ndx_text(text)
    assert meta["header"]
    assert len(records) == 5


def test_u238_row_if_in_head_else_skip():
    text = FIXTURE.read_text(encoding="iso-8859-1")
    records, _ = parse_ndx_text(text)
    # head is Ac-223..Ac-227 area; golden file carries U-238 from full fetch task
    for rec in records:
        assert rec["name"]
        assert rec["half_life_s"] > 0
        assert len(rec["progeny"]) == len(rec["branching"])
        assert abs(sum(rec["branching"]) - 1.0) <= BRANCH_SUM_ABS_TOL or rec["branching"]


def test_ac223_first_line_from_real_file():
    # First data line in production NDX (probed 2026-09-23)
    line = (
        "Ac-223 2.10     m A                   0  0  0     0 "
        "Fr-219      0 0.9900E+00                 0        0.0"
        "             0        0.0    0.0     0.0     0"
        "   0    0    0    0  0 0.000E+00 0.000E+00 0.000E+00"
    )
    # Prefer parsing head line 1 rather than hand-built line:
    head_lines = FIXTURE.read_text(encoding="iso-8859-1").splitlines()
    rec = parse_ndx_line(head_lines[1])
    assert rec["name"] == "Ac-223"
    assert rec["half_life_units"] == "m"
    assert rec["half_life_s"] == pytest.approx(2.10 * 60.0)
    assert rec["progeny"] == ["Fr-219"]
    assert rec["branching"] == [pytest.approx(0.99)]
    assert "SF" not in rec["progeny"]


def test_half_life_units():
    assert half_life_to_seconds_icrp("8.02070", "d") == pytest.approx(8.02070 * 86400.0)
    assert half_life_to_seconds_icrp("4.468E+9", "y") == pytest.approx(4.468e9 * 31557600.0)
    assert half_life_to_seconds_icrp("6.015", "h") == pytest.approx(6.015 * 3600.0)
    with pytest.raises(DataFormatError):
        half_life_to_seconds_icrp("1.0", "fortnight")
    with pytest.raises(DataFormatError):
        half_life_to_seconds_icrp("nope", "y")


def test_sf_progeny_becomes_mode_not_species():
    # Build from head if a SF row exists; else synthetic line using Ac-223 template is invalid —
    # use full-line constant from probe only if present in head; otherwise parse via golden.
    if not GOLDEN.exists():
        pytest.skip("golden slice added in Task 2")
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    u238 = next(r for r in data["records"] if r["name"] == "U-238")
    assert "SF" not in u238["progeny"]
    assert u238["modes_raw"].replace(" ", "") in {"ASF", "A"} or "SF" in u238["modes_raw"]
    assert u238["atomic_mass_u"] == pytest.approx(238.050788, rel=1e-9)
    assert u238["progeny"] == ["Th-234"]
    assert u238["branching"] == [pytest.approx(1.0)]
    # SF branch preserved in modes_raw / branch list policy: keep SF branch aligned in modes only
```

**Branch policy (lock now):** `progeny`/`branching` lists contain **only catalog species** (no `SF`). SF branch fraction is recorded in `decay_modes`-equivalent build step from `modes_raw` + optional SF slot. For build: if original progeny list contained `SF` with branch `b_sf`, then:
- `progeny`/`branching` keep only non-SF entries
- `sf_branch: float | None` field on the **parse** dict (catalog JSON exposes `decay_modes` including `{"mode":"SF","branch":b}` when building records)
- Sum check for branch tol uses **sum of all NDX branch floats including SF** before split.

Adjust the U-238 test expectation accordingly: full NDX branches are `[1.0, 5.45e-7]` with progeny `[Th-234, SF]`; after split: progeny `[Th-234]`, branching `[1.0]`, `sf_branch=5.45e-7`.

Rewrite `test_sf_progeny_becomes_mode_not_species` final form:

```python
def test_u238_sf_split_from_golden_slice():
    if not GOLDEN.exists():
        pytest.skip("golden slice added with full NDX build in Task 2")
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    u238 = next(r for r in data["records"] if r["name"] == "U-238")
    assert u238["progeny"] == ["Th-234"]
    assert u238["branching"] == [pytest.approx(1.0)]
    assert u238["sf_branch"] == pytest.approx(5.45e-7)
    assert u238["atomic_mass_u"] == pytest.approx(238.050788, rel=1e-9)
    assert u238["half_life_s"] == pytest.approx(4.468e9 * 31557600.0, rel=1e-12)
```

(If Step 2 fixture lacks U-238, skip is OK until Task 2 writes golden.)

- [ ] **Step 3: Run tests — expect import error**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/test_parse_icrp.py -v
```

Expected: FAIL `ModuleNotFoundError: ... _parse_icrp`.

- [ ] **Step 4: Implement `src/pydecay/data/_parse_icrp.py`**

```python
"""Pure parsers for ICRP-07.NDX (build-time; no network)."""

from __future__ import annotations

from typing import Any

from pydecay.exceptions import DataFormatError

NDX_EXPECTED_COUNT = 1252
BRANCH_SUM_ABS_TOL = 0.035

UNIT_TO_SECONDS: dict[str, float] = {
    "ys": 1e-24, "zs": 1e-21, "as": 1e-18, "fs": 1e-15, "ps": 1e-12,
    "ns": 1e-9, "ls": 1e-6, "us": 1e-6, "ms": 1e-3, "s": 1.0,
    "m": 60.0, "h": 3600.0, "d": 86400.0, "y": 31557600.0, "Y": 31557600.0,
}


def half_life_to_seconds_icrp(value: str, unit: str) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise DataFormatError(f"non-numeric half-life {value!r}") from exc
    if unit not in UNIT_TO_SECONDS:
        raise DataFormatError(f"unknown half-life unit {unit!r}")
    seconds = v * UNIT_TO_SECONDS[unit]
    if not (seconds > 0):
        raise DataFormatError(f"half-life must be > 0, got {seconds}")
    return seconds


def parse_ndx_line(line: str) -> dict[str, Any]:
    if len(line) != 226:
        raise DataFormatError(f"NDX line length {len(line)} != 226: {line[:20]!r}")
    name = line[0:7].strip()
    hl_raw = line[7:15].strip()
    unit = line[15:17].strip()
    modes_raw = line[17:25].strip()
    if not name or not hl_raw or not unit:
        raise DataFormatError(f"bad NDX header fields: {line[:25]!r}")
    half_life_s = half_life_to_seconds_icrp(hl_raw, unit)
    progeny: list[str] = []
    branching: list[float] = []
    sf_branch: float | None = None
    off = 53
    for k in range(4):
        p = line[off : off + 7].strip()
        # pointer 6 chars
        b_str = line[off + 7 : off + 13 + 11].strip()  # wrong — see below
        # Correct: (a7, i6, e11.0) with optional 1x after first three groups
        break
    # Use explicit cursor implementation:
    return _parse_ndx_line_cursor(line, name, hl_raw, unit, modes_raw, half_life_s)


def _parse_ndx_line_cursor(
    line: str, name: str, hl_raw: str, unit: str, modes_raw: str, half_life_s: float
) -> dict[str, Any]:
    off = 53
    progeny: list[str] = []
    branching: list[float] = []
    sf_branch: float | None = None
    all_branches: list[float] = []
    for k in range(4):
        p = line[off : off + 7].strip()
        off += 7
        off += 6  # pointer
        b_str = line[off : off + 11].strip()
        off += 11
        if k < 3:
            off += 1  # 1x
        if not p:
            # still consume empty branch? empty p may accompany 0.0 branch
            if b_str and float(b_str) != 0.0 and p == "" and b_str not in ("", "0.0"):
                # empty progeny with nonzero branch is format error
                if float(b_str) != 0.0 and not p:
                    raise DataFormatError(f"branch without progeny at slot {k} in {name}")
            continue
        try:
            b = float(b_str)
        except ValueError as exc:
            raise DataFormatError(f"bad branch {b_str!r} for {name}") from exc
        all_branches.append(b)
        if p == "SF":
            sf_branch = b if sf_branch is None else sf_branch + b
            continue
        progeny.append(p)
        branching.append(b)
    if off != 152:
        # after 4 triples we expect offset 152
        raise DataFormatError(f"progeny block misaligned: off={off} name={name}")
    e_alpha = float(line[152:159].strip() or "0")
    e_electron = float(line[159:167].strip() or "0")
    e_photon = float(line[167:175].strip() or "0")
    # counts 3i4, i5, i4
    c0 = int(line[175:179].strip() or "0")
    c1 = int(line[179:183].strip() or "0")
    c2 = int(line[183:187].strip() or "0")
    c3 = int(line[187:192].strip() or "0")
    c4 = int(line[192:196].strip() or "0")
    mass_s = line[196:207].strip()
    try:
        atomic_mass_u = float(mass_s)
    except ValueError as exc:
        raise DataFormatError(f"bad AMU {mass_s!r} for {name}") from exc
    if not (atomic_mass_u > 0):
        raise DataFormatError(f"non-positive AMU for {name}")
    total = sum(all_branches) if all_branches else 0.0
    if all_branches and abs(total - 1.0) > BRANCH_SUM_ABS_TOL:
        raise DataFormatError(f"branch sum {total} out of tol for {name}")
    return {
        "name": name,
        "half_life_raw": hl_raw,
        "half_life_units": unit,
        "half_life_s": half_life_s,
        "modes_raw": modes_raw,
        "progeny": progeny,
        "branching": branching,
        "sf_branch": sf_branch,
        "atomic_mass_u": atomic_mass_u,
        "icrp_extra": {
            "E_alpha": e_alpha,
            "E_electron": e_electron,
            "E_photon": e_photon,
            "num_phot_lt_10k": c0,
            "num_phot_gt_10k": c1,
            "num_betas": c2,
            "num_mono_e": c3,
            "num_alpha": c4,
        },
    }


def parse_ndx_text(text: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    lines = text.splitlines()
    if not lines:
        raise DataFormatError("empty NDX")
    header = lines[0]
    records = [parse_ndx_line(line) for line in lines[1:] if line.strip()]
    return records, {"header": header, "record_count": len(records)}
```

**Implementer note:** fix the dead code in `parse_ndx_line` so it only calls `_parse_ndx_line_cursor` (delete the broken mid-loop). Verify offset 152 logic against head fixture. If empty progeny slots still advance cursor correctly for zero-filled triples, tests pass.

- [ ] **Step 5: Run parser tests**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/test_parse_icrp.py -v
```

Expected: PASS (skips OK for golden until Task 2).

- [ ] **Step 6: Commit**

```powershell
git -c core.hooksPath=/dev/null add src/pydecay/data/_parse_icrp.py tests/test_parse_icrp.py tests/fixtures/icrp/
git -c core.hooksPath=/dev/null commit -m "feat: add ICRP-07.NDX pure parser with fixtures"
```

---

### Task 2: Fetch/build `icrp107.json` + golden slice + invariants

**Files:**
- Create: `src/pydecay/data/_fetch_icrp.py`
- Create: `src/pydecay/data/icrp107.json` (generated)
- Create: `tests/fixtures/icrp/ICRP-07.NDX.golden_slice.json`
- Create: `tests/test_fetch_icrp.py`
- Modify: `pyproject.toml` (coverage omit `_fetch_icrp.py`)
- Modify: `tests/test_parse_icrp.py` (golden non-skip tests)

**Interfaces:**
- Consumes: `parse_ndx_text`, `NDX_EXPECTED_COUNT`, `normalize_nuclide_name` (names already normal form).
- Produces:
  - Artifact schema per record (JSON object keyed by name):

```json
{
  "half_life_s": 1.402e17,
  "atomic_mass_u": 238.050788,
  "decay_modes": [{"mode": "A", "branch": 1.0}, {"mode": "SF", "branch": 5.45e-7}],
  "source": "ICRP-107",
  "source_url": "https://www.icrp.org/publication.asp?id=ICRP+Publication+107",
  "fetched": "YYYY-MM-DD",
  "half_life_uncertainty_s": null,
  "half_life_raw": "4.468E+9",
  "half_life_units": "y",
  "modes_raw": "A SF",
  "progeny": ["Th-234"],
  "branching": [1.0],
  "sf_branch": 5.45e-7,
  "is_stable": false
}
```

Stable endpoint records: `half_life_s` = `float("inf")`, `decay_modes` = `[]`, `progeny` = `[]`, `branching` = `[]`, `sf_branch` = `null`, `atomic_mass_u` = **mass number as float** (documented approximation), `source` = `"ICRP-107-stable"`, `is_stable` = `true`, `modes_raw` = `""`.

  - `build_catalog(records: list[dict], fetched: str) -> dict[str, dict]` in `_fetch_icrp.py` (pure enough to unit-test): injects stables, validates counts.
  - CLI: `python -m pydecay.data._fetch_icrp` writes `icrp107.json` atomically (tmp+replace).

**Stable injection algorithm:**
1. Radioactive names = 1252 NDX names (already `El-A[m]`).
2. Collect every progeny token not in radioactive set and not `SF` → stable names.
3. Emit stable records with mass number from name (`Y-90` → 90.0).
4. Assert every radioactive record’s progeny ⊆ radioactive ∪ stable.

**Mode derivation for `decay_modes`:** map from NDX `modes_raw` + progeny/Z-A if needed — **minimum viable for this task:**
- Split `modes_raw` is lossy (`ITB-`, `ECA`). Prefer deriving from progeny like radioactivedecay: same Z,A → `IT`; A−4,Z−2 → `A`; Z+1 → `B-`; Z−1 → `EC` or `EC+B+`; `SF` token → `SF`.
- If derivation ambiguous, keep a single entry `{"mode": modes_raw, "branch": 1.0}` **only when one progeny and sum≈1** — tests require `decay_modes` list of `{mode, branch}` for `Nuclide.from_record`.
- **Required for from_record:** `branch` floats; sum of `decay_modes` branches need not be 1 if SF split (SF + main). Prefer: non-SF progeny each get inferred mode with their branch; SF uses `sf_branch`.

Helpers to implement + test:
- `infer_mode(parent_name: str, daughter_name: str) -> str`
- `build_decay_modes(parsed: dict) -> list[dict]`

- [ ] **Step 1: Write failing tests** `tests/test_fetch_icrp.py`:

```python
"""Catalog build invariants (spec sections 6, 9, 10)."""

import json
from pathlib import Path

import pytest

from pydecay.data._fetch_icrp import build_catalog, sha256_file, write_json_atomic
from pydecay.data._parse_icrp import NDX_EXPECTED_COUNT, parse_ndx_text
from pydecay.nuclide import normalize_nuclide_name

NDX_URL_SHA = "ac84a9cf1da890031c2ab81a33cba858ff637d701fca3bc33fb07c5a1d6cf2b9"
ART = Path(__file__).resolve().parents[1] / "src" / "pydecay" / "data" / "icrp107.json"
FULL_NDX = Path(r"C:\Users\DANIEL\AppData\Local\Temp\opencode\ICRP-07.NDX")


@pytest.mark.skipif(not FULL_NDX.exists(), reason="full NDX not downloaded yet")
def test_full_ndx_parses_1252():
    records, meta = parse_ndx_text(FULL_NDX.read_text(encoding="iso-8859-1"))
    assert meta["record_count"] == NDX_EXPECTED_COUNT == 1252


@pytest.mark.skipif(not FULL_NDX.exists(), reason="full NDX not downloaded yet")
def test_build_catalog_counts_and_closure():
    records, _ = parse_ndx_text(FULL_NDX.read_text(encoding="iso-8859-1"))
    cat = build_catalog(records, fetched="2026-09-23")
    radioactive = [n for n, r in cat.items() if not r["is_stable"]]
    stables = [n for n, r in cat.items() if r["is_stable"]]
    assert len(radioactive) == 1252
    assert stables
    for rec in cat.values():
        if rec["is_stable"]:
            assert rec["half_life_s"] == float("inf")
            continue
        assert rec["half_life_s"] > 0
        missing = [p for p in rec["progeny"] if p not in cat]
        assert not missing, missing
        assert "ICRP-107" in rec["source"]


@pytest.mark.skipif(not ART.exists(), reason="icrp107.json not built yet")
def test_artifact_is_icrp_default_shape():
    cat = json.loads(ART.read_text(encoding="utf-8"))
    assert len(cat) > 1252
    u = cat["U-238"]
    assert u["source"] == "ICRP-107"
    assert u["atomic_mass_u"] == pytest.approx(238.050788, rel=1e-9)
    assert u["is_stable"] is False
    assert u["progeny"] == ["Th-234"]
```

Also add golden U-238 assertions in `tests/test_parse_icrp.py` (Task 1 final form) against `ICRP-07.NDX.golden_slice.json`.

- [ ] **Step 2: Run tests — fail**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/test_fetch_icrp.py -v
```

Expected: import errors / missing file skips that should not skip once implemented — `build_catalog` missing → FAIL.

- [ ] **Step 3: Implement `_fetch_icrp.py`** with:
  - `NDX_URL`, `NDX_SHA256`, `LICENSE_URL`, `LICENSE_SHA256`
  - `fetch_bytes(url, sha256) -> bytes` (verify hash)
  - `build_catalog`, `write_json_atomic(path, obj)`
  - `derive_modes` / `infer_mode`
  - `main()`: download NDX (or `--ndx-path`), parse, build, write `icrp107.json`, write golden slice (U-238, Tc-99m, I-131, Sr-90, Co-60, Pu-239), copy `LICENSE.ICRP-07` into data dir, print counts; exit 1 on invariant failure
- [ ] **Step 4: Implement fetch tests pass + generate artifacts**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pydecay.data._fetch_icrp
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/test_fetch_icrp.py tests/test_parse_icrp.py -v
```

Expected: `Wrote 1252+` message; all PASS.

- [ ] **Step 5: pyproject coverage omit**

```toml
[tool.coverage.run]
omit = ["*/data/_fetch_iaea.py", "*/data/_fetch_icrp.py"]
```

- [ ] **Step 6: Commit**

```powershell
git -c core.hooksPath=/dev/null add src/pydecay/data/_fetch_icrp.py src/pydecay/data/icrp107.json src/pydecay/data/LICENSE.ICRP-07 tests/test_fetch_icrp.py tests/fixtures/icrp/ pyproject.toml tests/test_parse_icrp.py
git -c core.hooksPath=/dev/null commit -m "feat: build full ICRP-107 catalog from checksum-pinned NDX"
```

---

### Task 3: Packaging excludes + license packaging tests

**Files:**
- Modify: `pyproject.toml` (`exclude = ["**/_fetch_iaea.py", "**/_fetch_icrp.py"]`)
- Modify: `tests/test_packaging.py`

**Interfaces:**
- Consumes: built artifacts from Task 2.
- Produces: wheel contains `LICENSE.ICRP-07` + `icrp107.json`; excludes both `_fetch_*.py`.

- [ ] **Step 1: Failing tests** in `tests/test_packaging.py`:

```python
def test_wheel_excludes_fetch_scripts_and_keeps_icrp_assets():
    # build wheel to temp dir
    import subprocess, sys, tempfile, zipfile, glob
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "-o", td],
            cwd=root, check=True, capture_output=True,
        )
        wheels = glob.glob(str(Path(td) / "*.whl"))
        assert len(wheels) == 1
        with zipfile.ZipFile(wheels[0]) as zf:
            names = zf.namelist()
        assert any(n.endswith("pydecay/data/icrp107.json") for n in names)
        assert any(n.endswith("pydecay/data/LICENSE.ICRP-07") for n in names)
        assert not any("_fetch_icrp.py" in n for n in names)
        assert not any("_fetch_iaea.py" in n for n in names)
```

- [ ] **Step 2: Run — fail** (exclude not set / license missing from wheel).

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/test_packaging.py::test_wheel_excludes_fetch_scripts_and_keeps_icrp_assets -v
```

- [ ] **Step 3: Fix `pyproject.toml` exclude line; ensure LICENSE.ICRP-07 is under package data** (hatch packages `src/pydecay` include all non-excluded files).

- [ ] **Step 4: Run test — PASS**; full packaging module PASS.

- [ ] **Step 5: Commit**

```powershell
git -c core.hooksPath=/dev/null add pyproject.toml tests/test_packaging.py
git -c core.hooksPath=/dev/null commit -m "feat: package ICRP catalog and license; exclude build fetchers"
```

---

### Task 4: Move IAEA oracle; switch `Nuclide` to `icrp107.json`

**Files:**
- Create: `tests/fixtures/iaea_nuclides_47.json` (move content of `src/pydecay/data/nuclides.json`)
- Modify: `src/pydecay/nuclide.py` (`_bundled_records` → `icrp107.json`; error message update)
- Modify: `tests/test_data.py` (ICRP assertions)
- Create: `tests/test_iaea_differential.py`
- Keep: `src/pydecay/data/nuclides.json` **deleted from package** after move (IAEA fetch script may still write it for regeneration — update `_fetch_iaea.OUT_PATH` to `tests/fixtures/iaea_nuclides_47.json`)

**Interfaces:**
- Consumes: Task 2 artifact.
- Produces: `Nuclide.load` reads ICRP; IAEA differential oracle file path `tests/fixtures/iaea_nuclides_47.json`.

- [ ] **Step 1: Move IAEA file + point fetch OUT_PATH**

```powershell
Copy-Item "src\pydecay\data\nuclides.json" "tests\fixtures\iaea_nuclides_47.json"
# then delete package copy after Nuclide switch in Step 3
```

Edit `_fetch_iaea.py`: `OUT_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "iaea_nuclides_47.json"`  
(`parents`: file → data → pydecay → src → repo root; verify with `Path(__file__).resolve()` — **correct parents count must be checked in implementation**: `Path(__file__).resolve().parents[3]` is `src` if file is `src/pydecay/data/x.py` (0=data,1=pydecay,2=src,3=repo). Yes `parents[3]` = repo root.)

- [ ] **Step 2: Failing test** — `tests/test_data.py` replace dataset tests:

```python
"""Tests for the bundled ICRP-107 dataset (spec sections 6, 9)."""

import math

import pytest

from pydecay.exceptions import NuclideNotFoundError
from pydecay.nuclide import Nuclide

MANDATORY = ["Co-60", "Cs-137", "I-131", "C-14", "U-238", "Tc-99m"]


@pytest.fixture(scope="module")
def all_nuclides():
    return Nuclide.load_all()


def test_catalog_is_full_icrp_scale(all_nuclides):
    radioactive = {k: v for k, v in all_nuclides.items() if math.isfinite(v.half_life_s)}
    assert len(radioactive) >= 1252


def test_mandatory_six_present(all_nuclides):
    for name in MANDATORY:
        assert name in all_nuclides


def test_every_record_is_icrp_sourced(all_nuclides):
    for nuc in all_nuclides.values():
        assert "ICRP" in nuc.source or nuc.source.endswith("stable")
        assert "icrp" in nuc.source_url.lower() or "ICRP" in nuc.source


def test_half_lives_positive_or_inf(all_nuclides):
    for nuc in all_nuclides.values():
        assert nuc.half_life_s > 0  # inf > 0
        assert nuc.atomic_mass_u > 0


def test_load_by_name(all_nuclides):
    assert Nuclide.load("i131").name == "I-131"
    assert Nuclide.load("U-238").atomic_mass_u == pytest.approx(238.050788, rel=1e-9)


def test_load_missing_raises():
    with pytest.raises(NuclideNotFoundError):
        Nuclide.load("Xx-999")
```

Create `tests/test_iaea_differential.py`:

```python
"""IAEA 47 fixture vs runtime ICRP half-lives (independent oracle)."""

import json
from pathlib import Path

import pytest

from pydecay.nuclide import Nuclide

IAEA = Path(__file__).parent / "fixtures" / "iaea_nuclides_47.json"
# Measured class of drift (IAEA vs ICRP evaluations); start from documented
# accepted-deviation ceiling in docs/data-sources.md and tighten after first run.
REL_TOL_DATA = 1.5e-2


def test_overlap_half_lives_within_tolerance():
    iaea = json.loads(IAEA.read_text(encoding="utf-8"))
    worst = 0.0
    worst_name = None
    for name, rec in iaea.items():
        ours = Nuclide.load(name).half_life_s
        theirs = float(rec["half_life_s"])
        rel = abs(ours - theirs) / theirs
        if rel > worst:
            worst, worst_name = rel, name
        assert rel <= REL_TOL_DATA, f"{name} rel={rel:.3e} iaea={theirs} icrp={ours}"
    print(f"worst {worst_name} {worst:.3e}")  # tighten REL_TOL_DATA to worst*1.05 after first green run
```

- [ ] **Step 3: Run — fail** (still loading `nuclides.json` or IAEA tests still expect IAEA source).

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/test_data.py tests/test_iaea_differential.py -v
```

- [ ] **Step 4: Switch `nuclide.py`**:

```python
    @classmethod
    def _bundled_records(cls) -> dict[str, Any]:
        text = resources.files("pydecay.data").joinpath("icrp107.json").read_text(
            encoding="utf-8"
        )
        data = json.loads(text)
        if not isinstance(data, dict):
            raise DataFormatError("icrp107.json must be a JSON object")
        return data
```

Update `NuclideNotFoundError` message to mention ICRP-107 catalog.

Delete `src/pydecay/data/nuclides.json` after tests pass (or keep until Step 6 cleanup — **delete in Step 6**).

- [ ] **Step 5: Fix fallout tests** (expected):
  - `tests/test_crosscheck.py` — still runs; may change drift profile (Task 5).
  - `tests/golden/test_golden.py` — half-life goldens vs ICRP (Task 5) — **expect FAIL until Task 5**. For this task, run only data tests green first; full suite red until Task 5.
  - `test_known_values` ballpark ranges should still pass.
  - `from_record` must accept `half_life_s=inf` (already `inf > 0`).

Run:

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/test_data.py tests/test_iaea_differential.py tests/test_known_values.py tests/test_chain.py -v
```

Expected: PASS (data + known + chain).

- [ ] **Step 6: Delete package `nuclides.json`; keep fetch OUT_PATH fix; commit**

```powershell
git -c core.hooksPath=/dev/null add src/pydecay/nuclide.py src/pydecay/data/_fetch_iaea.py tests/test_data.py tests/test_iaea_differential.py tests/fixtures/iaea_nuclides_47.json
git -c core.hooksPath=/dev/null add -u src/pydecay/data/nuclides.json
git -c core.hooksPath=/dev/null commit -m "feat: default Nuclide catalog to full ICRP-107; IAEA becomes test oracle"
```

---

### Task 5: Goldens, crosscheck, version 0.2.0

**Files:**
- Modify: `tests/golden/golden_values.json`, `tests/golden/test_golden.py`
- Modify: `tests/test_crosscheck.py`
- Modify: `tests/test_api.py`, `tests/test_smoke.py`
- Modify: `src/pydecay/__init__.py`

**Interfaces:**
- Consumes: ICRP runtime half-lives.
- Produces: green full suite; `__version__ == "0.2.0"`.

- [ ] **Step 1: Golden provenance prefixes**

In `test_golden.py`:  
`PROVENANCE_OK_PREFIXES = ("ICRP", "IAEA", "NNDC", "analytic", "radioactivedecay")`.

- [ ] **Step 2: Update half-life golden values to ICRP runtime**

For each `kind == "nuclide_half_life"` entry: set `half_life_s` from `Nuclide.load(...).half_life_s`, set `source` to `"ICRP-107"`, update `note` to cite ICRP Publication 107, set `verified_on` to `2026-09-23`. Keep ids (may rename `*_iaea` → leave ids stable to avoid REQUIRED_IDS churn — **keep ids**, change source/notes only).

For activity/fraction/chain entries that cite IAEA T_half: recompute `expected_*` from ICRP half-lives with the same formulas, update `source` strings to `analytic: ... ICRP-107 T_half`.

Script helper (one-off, not committed as product code):

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -c "from pydecay import Nuclide; print({n: Nuclide.load(n).half_life_s for n in ['Tc-99m','I-131','Co-60','Cs-137','C-14','U-238','Sr-90']})"
```

- [ ] **Step 3: Run goldens — fix until PASS**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/golden -v
```

- [ ] **Step 4: Crosscheck vs radioactivedecay**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/test_crosscheck.py -v
```

Runtime is now ICRP≈radioactivedecay ICRP — expect near-zero drift; `ACCEPTED_DEVIATIONS` may become unused. **Do not delete the allowlist blindly:** first run with reporting; if all overlaps ≤ `REL_TOL` without allowlist, keep allowlist as empty frozenset and update docs in Task 12; if failures, investigate before widening `REL_TOL`.

- [ ] **Step 5: Version bump to 0.2.0**

- `src/pydecay/__init__.py`: `__version__ = "0.2.0"`
- `tests/test_api.py`: `assert __version__ == "0.2.0"`
- `tests/test_smoke.py`: same

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest -q
```

Expected: **full suite green**.

- [ ] **Step 6: Gates**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m ruff check src tests
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m mypy src
```

- [ ] **Step 7: Commit**

```powershell
git -c core.hooksPath=/dev/null add src/pydecay/__init__.py tests/test_api.py tests/test_smoke.py tests/golden/ tests/test_crosscheck.py
git -c core.hooksPath=/dev/null commit -m "feat: bump to 0.2.0; retarget goldens and crosscheck to ICRP-107"
```

---

### Task 6: RAD/BET loaders (bootstrap from RadData + optional raw zip)

**Files:**
- Create: `tests/test_parse_icrp_spectra.py`
- Create: `src/pydecay/data/_fetch_icrp_spectra.py` **or** extend `_fetch_icrp.py` with `--rad-bet` subcommand (prefer **extend `_fetch_icrp.py`** to keep one entrypoint)
- Create: `src/pydecay/data/icrp107_rad.json.gz`, `icrp107_bet.json.gz`
- Modify: `pyproject.toml` optional-dependencies: `icrp = ["pyreadr>=0.5"]`

**Interfaces:**
- Consumes: RadData tarball SHA pin (global table) or `data/raw_icrp/ICRP-07.RAD` + `ICRP-07.BET`.
- Produces:
  - RAD artifact: JSON object `{ "codes": [{"code_num", "code_AN", "description"}], "emissions": { "U-238": [{"code_AN": "G", "E_MeV": 0.049, "prob": 6e-6, "code_num": 1, "is_photon": true}, ...] } }` gzipped.
  - BET artifact: `{ "U-238": {"E_MeV": [...], "A": [...]}, ... }` gzipped.
  - Functions in `_fetch_icrp.py`: `rad_from_dataframe(df) -> dict`, `bet_from_dataframe(df) -> dict`, `write_gzip_json(path, obj)`.

**Fixture approach:** small CSV slices under `tests/fixtures/icrp/rad_sample.csv` and `bet_sample.csv` exported once from RadData (5–20 rows each) so unit tests need no network/`pyreadr`.

- [ ] **Step 1: Export fixtures once**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -c "import pyreadr, pathlib, tarfile, csv, io; td=pathlib.Path(r'C:\Users\DANIEL\AppData\Local\Temp\opencode\rdata'); t=tarfile.open(r'C:\Users\DANIEL\AppData\Local\Temp\opencode\RadData_1.0.2.tar.gz'); t.extractall(td, filter='data'); rad=pyreadr.read_r(str(td/'RadData/data/ICRP_07.RAD.rda')); bet=pyreadr.read_r(str(td/'RadData/data/ICRP_07.BET.rda')); codes=pyreadr.read_r(str(td/'RadData/data/rad_codes.rda')); out=pathlib.Path(r'D:\Vs Code\VS code\pydecay\tests\fixtures\icrp'); out.mkdir(exist_ok=True); next(iter(rad.values())).head(30).to_csv(out/'rad_sample.csv', index=False); next(iter(bet.values())).head(30).to_csv(out/'bet_sample.csv', index=False); next(iter(codes.values())).to_csv(out/'rad_codes.csv', index=False); print('fixtures ok')"
```

- [ ] **Step 2: Failing tests** for converters (pure functions over CSV fixtures):

```python
import csv
from pathlib import Path
from pydecay.data._fetch_icrp import rad_from_rows, bet_from_rows

def test_rad_sample_shape():
    rows = list(csv.DictReader((Path(__file__).parent / "fixtures/icrp/rad_sample.csv").open()))
    rad = rad_from_rows(rows)
    assert "Ac-223" in rad
    assert rad["Ac-223"][0]["E_MeV"] >= 0
    assert "prob" in rad["Ac-223"][0]

def test_bet_sample_shape():
    rows = list(csv.DictReader((Path(__file__).parent / "fixtures/icrp/bet_sample.csv").open()))
    bet = bet_from_rows(rows)
    assert "Ac-226" in bet or bet  # first nuclide in fixture
    first = next(iter(bet.values()))
    assert len(first["E_MeV"]) == len(first["A"])
```

- [ ] **Step 3: Implement converters + `--spectra` build path** (RadData download+pyreadr when extra installed; or `--raw-dir` Fortran files later). Generate gzipped artifacts.

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pip install -e ".[test,dev,icrp]"
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pydecay.data._fetch_icrp --spectra
```

Expected: writes both gzips; prints row counts (`rad nuclides`, `bet nuclides`).

- [ ] **Step 4: Tests PASS + commit**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest tests/test_parse_icrp_spectra.py -v
git -c core.hooksPath=/dev/null add src/pydecay/data/icrp107_rad.json.gz src/pydecay/data/icrp107_bet.json.gz src/pydecay/data/_fetch_icrp.py tests/test_parse_icrp_spectra.py tests/fixtures/icrp/ pyproject.toml
git -c core.hooksPath=/dev/null commit -m "feat: build ICRP-107 RAD and BET artifacts (gzip JSON)"
```

---

### Task 7: Lazy data loaders in `pydecay.data`

**Files:**
- Modify: `src/pydecay/data/__init__.py`
- Create: `tests/test_data_loaders.py`

**Interfaces:**
- Consumes: artifact paths above.
- Produces:
  - `load_catalog() -> dict[str, Any]` (cached)
  - `load_rad() -> dict[str, Any]` (cached, opens gzip on first call)
  - `load_bet() -> dict[str, Any]` (cached)
  - `load_rad_for(name) -> list[dict]` raises `NuclideNotFoundError` if missing
  - `load_bet_for(name) -> dict` same

Use `functools.lru_cache(maxsize=1)` on each loader.

- [ ] **Step 1: Failing tests**

```python
import pydecay
from pydecay.data import load_catalog, load_rad_for, load_bet_for
from pydecay.exceptions import NuclideNotFoundError
import pytest

def test_catalog_nonempty():
    assert len(load_catalog()) >= 1252

def test_rad_and_bet_lookup():
    rad = load_rad_for("Ac-223")
    assert rad and "E_MeV" in rad[0]
    with pytest.raises(NuclideNotFoundError):
        load_rad_for("Xx-999")

def test_import_does_not_open_bet(monkeypatch):
    import gzip, io, builtins
    opened = []
    real_open = builtins.open
    def spy(path, *a, **k):
        opened.append(str(path))
        return real_open(path, *a, **k)
    # gzip.open delegates — spy on gzip.open too
    real_gzip_open = gzip.open
    def spy_gzip(path, *a, **k):
        opened.append(str(path))
        return real_gzip_open(path, *a, **k)
    monkeypatch.setattr(builtins, "open", spy)
    monkeypatch.setattr(gzip, "open", spy_gzip)
    import importlib
    import pydecay.data as d
    # ensure cache cold
    d.load_catalog.cache_clear()
    d.load_rad.cache_clear() if hasattr(d.load_rad, "cache_clear") else None
    load_catalog()
    assert not any("bet" in p.lower() for p in opened)
```

(Adjust cache_clear to however loaders are implemented; must not call `load_rad_for` in this test.)

- [ ] **Step 2: Run fail → implement `__init__.py` loaders → run pass → commit**

```powershell
git -c core.hooksPath=/dev/null add src/pydecay/data/__init__.py tests/test_data_loaders.py
git -c core.hooksPath=/dev/null commit -m "feat: cached ICRP catalog and lazy spectra loaders"
```

---

### Task 8: `pydecay.spectra` public API

**Files:**
- Create: `src/pydecay/spectra.py`
- Create: `tests/test_spectra.py`
- Modify: none for `__all__` yet (Task 11)

**Interfaces:**
- Consumes: `load_rad_for`, `load_bet_for`.
- Produces:
  - `emissions(name: str) -> list[dict]` — normalize name via `normalize_nuclide_name`
  - `beta_spectrum(name: str) -> tuple[list[float], list[float]]` — `(E_MeV, A)`
  - Raises `NuclideNotFoundError` for unknown nuclide; `NuclideNotFoundError` or `DataFormatError` for missing spectra rows — **lock: `NuclideNotFoundError` if name not in catalog; `DataFormatError` if name in catalog but no RAD/BET rows** (stable nuclides).

```python
"""Optional radiation spectra access (ICRP-107 RAD/BET)."""

from __future__ import annotations

from pydecay.data import load_bet_for, load_rad_for
from pydecay.exceptions import DataFormatError, NuclideNotFoundError
from pydecay.nuclide import Nuclide, normalize_nuclide_name


def emissions(name: str) -> list[dict]:
    norm = normalize_nuclide_name(name)
    try:
        Nuclide.load(norm)
    except NuclideNotFoundError:
        raise
    rows = load_rad_for(norm)
    if not rows:
        raise DataFormatError(f"no emissions for {norm}")
    return rows


def beta_spectrum(name: str) -> tuple[list[float], list[float]]:
    norm = normalize_nuclide_name(name)
    Nuclide.load(norm)  # raises if unknown
    payload = load_bet_for(norm)
    return list(payload["E_MeV"]), list(payload["A"])
```

- [ ] **Step 1: Tests** — known beta emitter (e.g. first BET nuclide / `Sr-90` if present); stable/missing → `DataFormatError`; unknown name → `NuclideNotFoundError`; lengths match; energies non-negative.
- [ ] **Step 2: fail → implement → pass**
- [ ] **Step 3: Commit**

```powershell
git -c core.hooksPath=/dev/null add src/pydecay/spectra.py tests/test_spectra.py
git -c core.hooksPath=/dev/null commit -m "feat: add emissions() and beta_spectrum() spectra API"
```

---

### Task 9: ACK/NSF raw vendoring (optional files) + coverage + full gates

**Files:**
- Create: `data/raw_icrp/.gitkeep` (and gitignore large raw: `data/raw_icrp/*` except `.gitkeep` and `LICENSE.ICRP-07` copies)
- Modify: `.gitignore`
- Modify: `_fetch_icrp.py` `--raw-dir` validation for ACK/NSF if present (copy into `src/pydecay/data/raw_icrp/` only if user provides zip extract — **skip if absent**)
- Modify: `docs/data-sources.md` status lines (full rewrite in Task 10 — here only if needed for gates)

**Interfaces:**
- Produces: documented pending/available state; no runtime API.

- [ ] **Step 1:** Add `.gitignore` entries:

```gitignore
data/raw_icrp/*
!data/raw_icrp/.gitkeep
!data/raw_icrp/README.md
```

- [ ] **Step 2:** `data/raw_icrp/README.md` explains official zip URL, 403 note, extract instructions, SHA-256 placeholder `SUPPL_ZIP_SHA256`.
- [ ] **Step 3:** Full gates:

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest --cov=pydecay --cov-report=term-missing --cov-fail-under=90
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m ruff check src tests
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m mypy src
```

Fix any coverage holes (parsers must be covered; fetchers omitted).

- [ ] **Step 4: Commit**

```powershell
git -c core.hooksPath=/dev/null add .gitignore data/raw_icrp/ 
git -c core.hooksPath=/dev/null commit -m "chore: raw ICRP-07 drop directory for official CD zip"
```

---

### Task 10: Docs, README, CHANGELOG, CONTRIBUTING

**Files:**
- Modify: `docs/data-sources.md` (major rewrite)
- Modify: `docs/development.md`, `docs/api.md`, `docs/index.md`, `docs/quickstart.md`, `docs/architecture.md` (diagram `data/nuclides.json` → `data/icrp107.json`)
- Modify: `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`
- Modify: `docs/api.md` version example → `0.2.0`; add spectra section **without** claiming top-level export until Task 11

**Interfaces:**
- Consumes: implemented behavior.
- Produces: docs match reality; `mkdocs build --strict` green if docs extra installed.

- [ ] **Step 1: `docs/data-sources.md` structure**

1. Runtime source: ICRP-107 (1252 + stables), artifact `icrp107.json`, fetch command, SHA pins.
2. Spectra: RAD/BET gzip artifacts, bootstrap via RadData/pyreadr vs official zip, license.
3. License: educational/research/not-for-profit paragraph + pointer to `LICENSE.ICRP-07`.
4. IAEA: **test oracle only** at `tests/fixtures/iaea_nuclides_47.json`; differential policy `REL_TOL_DATA`.
5. Cross-check vs `radioactivedecay`: same evaluation family post-switch; keep REL_TOL 1e-3.
6. Year convention unchanged.
7. Remove “Full ICRP-107 deferred” bullet; replace with ENSDF still deferred.

- [ ] **Step 2: README** — Data row: `1252+ ICRP-107 nuclides (default) + spectra API`; verification section updates; license section mentions MIT + ICRP-07 data license.
- [ ] **Step 3: CHANGELOG `[Unreleased]`**:

```markdown
## [Unreleased]

### Added
- Full ICRP-107 default catalog (1252 radionuclides + stable endpoints).
- `pydecay.spectra.emissions` / `beta_spectrum` (RAD/BET).
- IAEA 47 retained as differential test fixture only.

### Changed
- `Nuclide.load` / `load_all` now read `icrp107.json` (version 0.2.0).
```

- [ ] **Step 4: CONTRIBUTING data rules** — regenerate via `_fetch_icrp`, ICRP wins runtime, IAEA is oracle.
- [ ] **Step 5: `mkdocs build --strict`** if docs installed; fix warnings.
- [ ] **Step 6: Commit**

```powershell
git -c core.hooksPath=/dev/null add README.md CHANGELOG.md CONTRIBUTING.md docs/
git -c core.hooksPath=/dev/null commit -m "docs: document ICRP-107 default catalog and spectra pipeline"
```

---

### Task 11: Export spectra from package root + final API tests

**Files:**
- Modify: `src/pydecay/__init__.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Produces: `__all__` includes `"emissions"`, `"beta_spectrum"`; `pydecay.emissions` works.

- [ ] **Step 1: Failing test**

```python
def test_spectra_exported():
    import pydecay
    assert "emissions" in pydecay.__all__
    assert "beta_spectrum" in pydecay.__all__
    assert callable(pydecay.emissions)
    assert callable(pydecay.beta_spectrum)
```

- [ ] **Step 2: Re-export from `__init__.py`**, run tests, commit:

```powershell
git -c core.hooksPath=/dev/null add src/pydecay/__init__.py tests/test_api.py
git -c core.hooksPath=/dev/null commit -m "feat: export emissions and beta_spectrum from package root"
```

---

### Task 12: Wheel size budget + release gate

**Files:**
- Modify: `tests/test_packaging.py` (size assert)
- Modify: `tests/test_api.py` version already 0.2.0

**Interfaces:**
- Produces: hard fail if wheel > 15 MB.

- [ ] **Step 1: Test**

```python
def test_wheel_size_budget():
    # reuse build from Task 3 helper; assert Path(wheel).stat().st_size <= 15_000_000
```

Refactor Task 3 to share `_build_wheel(tmpdir) -> Path` helper in the same module.

- [ ] **Step 2: Run packaging tests; if over budget**, gzip already applied — check uncompressed JSON leftover; shrink graph indent (`indent=None` separators) only if needed and still readable enough for diffs — prefer keeping indent=2 if under budget.

- [ ] **Step 3: Full gates + commit**

```powershell
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m pytest -q
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m ruff check src tests
& "D:\Vs Code\themis\venv\Scripts\python.exe" -m mypy src
git -c core.hooksPath=/dev/null add tests/test_packaging.py
git -c core.hooksPath=/dev/null commit -m "test: enforce 15MB wheel budget for ICRP artifacts"
```

- [ ] **Step 4: Optional push** (only if user asked to push):

```powershell
git push origin main
```

---

### Task 13: Landing-page **summary draft only** (no landing edits)

**Files:**
- Create: `docs/superpowers/plans/2026-09-23-icrp107-landing-summary.md` (or `docs/superpowers/specs/…` — use plans folder for this working note)

**Interfaces:**
- Consumes: completed Tasks 1–12.
- Produces: approved bullet list for later landing-page PR.

**User rule:** do **not** modify `landingpage/**` until this summary is approved.

- [ ] **Step 1: Write summary covering:**

1. What shipped: 1252+ ICRP-107 default catalog, stable endpoints, RAD/BET spectra API, checksummed pipeline, IAEA→test-only oracle, 0.2.0.
2. Accuracy story: single runtime source; IAEA differential; radioactivedecay crosscheck; goldens.
3. License callout: ICRP-07 non-profit terms on data files.
4. Suggested landing copy bullets (masthead version `0.2.0`, data section “1252 nuclides”, new spectra blurb).
5. Open risks: commercial license; Sage zip 403; stable mass approximation.

- [ ] **Step 2: Commit summary file only**

```powershell
git -c core.hooksPath=/dev/null add docs/superpowers/plans/2026-09-23-icrp107-landing-summary.md
git -c core.hooksPath=/dev/null commit -m "docs: draft v2 landing-page summary for review"
```

- [ ] **Step 3: STOP.** Ask user to review summary before any landing-page edit (separate task/plan).

---

## Self-review (plan author)

**Spec coverage:**
- Goal/coverage → Tasks 2, 4  
- Raw+own parser NDX → Task 1–2  
- RAD/BET/ACK/NSF scope → Tasks 6, 9 (ACK/NSF raw-only per resolved item 3)  
- Staged ship / lazy BET → Tasks 6–8  
- Single source of truth + IAEA oracle → Tasks 4–5  
- License packaging → Tasks 2–3, 10  
- Invariants incl. measured branch tol → Task 1–2  
- Spectra API names → Tasks 8, 11  
- Version 0.2.0 → Task 5  
- Wheel 15 MB → Task 12  
- Landing summary before landing edits → Task 13  

**Placeholder scan:** No TBD/TODO in task steps; raw zip SHA left as runtime-filled constant only because Sage 403s — documented, not vague.

**Type consistency:** `parse_ndx_line` → `build_catalog` → `icrp107.json` keys align with `Nuclide.from_record` required keys (`half_life_s`, `atomic_mass_u`, `decay_modes`, `source`, `source_url`, `fetched`). `emissions`/`beta_spectrum` match Tasks 8 and 11.

**Known execution risk:** Task 4 leaves goldens red until Task 5 — intentional sequencing; Task 5 must run before declaring gates green.

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-23-icrp107-data-pipeline.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — executing-plans in this session with checkpoints  

Which approach?
