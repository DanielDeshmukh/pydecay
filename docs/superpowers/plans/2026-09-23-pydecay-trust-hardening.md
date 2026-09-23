# Trust Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove pydecay numbers against external truth (golden primary-source values, radioactivedecay solver cross-diffs) and lock mathematical invariants with property tests — before any v2 feature work.

**Architecture:** Additive test layers on the existing suite: a frozen golden-values JSON + parametrized runner, a radioactivedecay *solver-output* cross-diff (three scenarios), and a hypothesis invariant suite. No public API changes. Near-degenerate expm dispatch, half-life differential cross-check, and coverage `fail_under=90` **already exist in v1** — this plan does not rebuild them.

**Tech Stack:** Python ≥3.10; pytest + pytest-cov; hypothesis; radioactivedecay 0.6.x (test extra only); existing numpy/scipy/pint runtime deps.

**Spec:** `docs/superpowers/specs/2026-09-23-pydecay-trust-hardening-design.md` — executors read both. Locked literals below are intentional: tolerances, golden entry ids, and fixture-verified radioactivedecay call sites from the 2026-09-23 probe.

## Global Constraints

- Runtime package deps stay `numpy>=1.23`, `scipy>=1.9`, `pint>=0.20` only — **no** hypothesis/radioactivedecay in `[project] dependencies`.
- `pydecay.__all__` must remain exactly the existing 13 names; no new public exports.
- Divergence policy: **fix before done** — any cross-check failure is investigated and resolved (code fix or documented justified deviation) before this plan is complete.
- Windows + PowerShell 5.1: no `&&` in shell steps; use `; if ($?) { ... }` or separate commands. Prefer `python -m pytest`.
- Git commits: one logical step per commit message listed below; use `-c core.hooksPath=/dev/null` only if hooks block; do not push unless asked.
- Line length 100 (ruff); mypy strict on `src` only; tests may be looser.
- Console output in tests/docs must be ASCII-safe (no `≈`, no raw non-ASCII in assert messages if printed on cp1252).
- **Already done — do not recreate:** `DEGENERATE_EPS` / `use_bateman` guard in `src/pydecay/_solver.py`; near-degenerate tests in `tests/test_solver.py`; `tests/test_crosscheck.py` half-life drift; `radioactivedecay` already in `test` extra; `[tool.coverage.report] fail_under = 90`; `docs/math.md` dispatch table.

### Environment note

Default interpreter is `D:\Vs Code\themis\venv\Scripts\python.exe` (project may have no local `.venv`). All `python` / `pytest` commands below assume that environment with `pip install -e ".[test]"` (or equivalent) so local runs match CI.

### File structure

| Path | Responsibility |
|------|----------------|
| `pyproject.toml` | Add `hypothesis` to `test` extra; tighten `radioactivedecay` pin |
| `tests/golden/golden_values.json` | Frozen, sourced expected tuples |
| `tests/golden/test_golden.py` | Schema validation + parametrized assertions |
| `tests/crosscheck/test_radioactivedecay_solver.py` | Three solver-output scenarios vs radioactivedecay 0.6.1 |
| `tests/property/test_invariants.py` | Hypothesis invariants |
| `.github/workflows/ci.yml` | Explicit `--cov-fail-under=90` on the pytest line |
| `docs/data-sources.md` | Golden-values provenance section |
| `docs/api.md`, `docs/quickstart.md` | Explicit `t >= 0` / no back-calculation contract |
| `docs/CHANGELOG.md` | Note under Unreleased / v2 hardening |

---

### Task 1: Test extra — hypothesis + radioactivedecay pin

**Files:**
- Modify: `pyproject.toml:38-41` (`[project.optional-dependencies]`)

**Interfaces:**
- Consumes: existing `test` extra (already has pytest, pytest-cov, radioactivedecay).
- Produces: `pip install -e ".[test]"` installs `hypothesis>=6` and `radioactivedecay>=0.6,<1` (probe-confirmed 0.6.1 API).

- [ ] **Step 1: Edit the test extra**

Replace the `test = [...]` line with:

```toml
test = [
  "pytest>=7.4",
  "pytest-cov>=4.1",
  "hypothesis>=6",
  "radioactivedecay>=0.6,<1",
]
```

- [ ] **Step 2: Install the extra into the active environment**

Run: `python -m pip install -e ".[test]"`  
Expected: Successfully installed/updated hypothesis and radioactivedecay (0.6.1).

- [ ] **Step 3: Sanity-import both**

Run: `python -c "import hypothesis, radioactivedecay; print(hypothesis.__version__, radioactivedecay.__version__)"`  
Expected: two version numbers, no traceback.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "test: add hypothesis and pin radioactivedecay in test extra"
```

---

### Task 2: Golden values file + runner

**Files:**
- Create: `tests/golden/golden_values.json`
- Create: `tests/golden/test_golden.py`

**Interfaces:**
- Consumes: `pydecay.Nuclide`, `pydecay.decayed_atoms`, `pydecay.decayed_activity`, `pydecay.remaining_fraction`, `pydecay.DecayChain`.
- Produces: JSON schema fields below; tests are plain pytest functions (no new package exports).

**Golden JSON shape (locked):**

```json
{
  "schema_version": 1,
  "verified_on": "2026-09-23",
  "entries": [ { "...": "see entry templates below" } ]
}
```

**Entry templates (locked ids and values — executable without inventing numbers):**

1. **Half-life freezes (kind `nuclide_half_life`)** — one entry per isotope; `half_life_s` must equal the bundled record (IAEA fetch 2026-09-22); `rel_tol`: `1e-12` (exact match to bundle); `source`: `"IAEA Live Chart of Nuclides"`; `source_url`: `"https://www-nds.iaea.org/relnsd/v0/data?fields=ground_states&nuclides=<sym>"` style or the chart HTML URL used in the bundle; `note`: includes fetch date.

| id | nuclide | half_life_s |
|----|---------|-------------|
| `tc99m_halflife_iaea` | Tc-99m | `21625.920000000002` |
| `i131_halflife_iaea` | I-131 | `693377.28` |
| `co60_halflife_iaea` | Co-60 | `166344192.0` |
| `cs137_halflife_iaea` | Cs-137 | `949252608.0` |
| `c14_halflife_iaea` | C-14 | `179878320000.0` |
| `u238_halflife_iaea` | U-238 | `1.409993568e+17` |

2. **Single-isotope activity (kind `single_activity`)** — fields: `nuclide`, `a0_bq`, `t_s`, `expected_bq`, `rel_tol`, provenance fields.

| id | setup | expected_bq | rel_tol |
|----|-------|-------------|---------|
| `co60_activity_10y` | Co-60, a0=`1e6` Bq, t=`10*31557600` s | `268477.54768988496` | `1e-9` |
| `tc99m_activity_6h` | Tc-99m, a0=`500` Bq, t=`6*3600` s | `250.2077812185201` | `1e-9` |

`source` for these: `"analytic: A0*exp(-ln2/T_half*t) with IAEA T_half"`; `source_url` may repeat the IAEA URL; `note` must state formula.

3. **Remaining fraction (kind `remaining_fraction`)** — fields: `nuclide` or `half_life_s`, `t_s`, `expected`, `rel_tol`.

| id | setup | expected | rel_tol |
|----|-------|----------|---------|
| `c14_fraction_5730y` | C-14, t=`5730*31557600` s | `0.49817925166675786` | `1e-9` |
| `u238_fraction_1gy` | U-238, t=`1e9*31557600` s | `0.8562988025248168` | `1e-9` |
| `one_half_life_identity` | any (`half_life_s=1.0`), t=`1.0` | `0.5` | `1e-12` |

4. **Linear chain atoms (kind `chain_atoms`)** — fields: `chain: {"type":"linear","lambdas":[...]}` or isotope names, `t_s`, `n0`, `expected` (dict), `rel_tol`.

| id | setup | expected | rel_tol |
|----|-------|----------|---------|
| `sr90_y90_atoms_30y` | isotopes `["Sr-90","Y-90"]` (bundled λ), n0=`{"Sr-90": 1.0}`, t=`30*31557600` | `{"Sr-90": 0.4871023279204198, "Y-90": 0.00012314011577117917}` | `1e-9` |

5. **Branching atoms (kind `chain_atoms` with explicit lambdas)** — synthetic star; use `DecayChain.branching` with explicit `lambdas`.

| id | setup | expected | rel_tol |
|----|-------|----------|---------|
| `branch_p_d1_d2_10s` | parent `P` lambdas `{P:0.1, D1:0.05, D2:0.02}`, branches `{D1:0.6, D2:0.4}`, t=`10.0`, default n0 parent=1 | `{"P": 0.36787944117144233, "D1": 0.2863814622494293, "D2": 0.2254256559532698}` | `1e-9` |

Note: branching expected values are from the star-topology closed form (feed integral), not from IAEA topology — `source` = `"analytic: star branching closed form"`.

- [ ] **Step 1: Write the failing schema/runner test**

Create `tests/golden/test_golden.py`:

```python
"""Frozen golden values: primary-source half-lives + analytic decay tuples."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pydecay import DecayChain, Nuclide, decayed_activity, remaining_fraction

GOLDEN_PATH = Path(__file__).parent / "golden_values.json"
REQUIRED_ENTRY_KEYS = {"id", "kind", "rel_tol", "source", "note"}
PROVENANCE_OK_PREFIXES = ("IAEA", "NNDC", "analytic", "radioactivedecay")


def _load_golden() -> dict:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def test_golden_file_exists_and_has_schema():
    data = _load_golden()
    assert data["schema_version"] == 1
    assert data["verified_on"]
    assert isinstance(data["entries"], list) and data["entries"]


def test_every_entry_has_required_keys_and_provenance():
    for entry in _load_golden()["entries"]:
        missing = REQUIRED_ENTRY_KEYS - set(entry)
        assert not missing, f"{entry.get('id', '?')} missing {missing}"
        src = entry["source"]
        assert any(src.startswith(p) for p in PROVENANCE_OK_PREFIXES), (
            f"{entry['id']} source must cite IAEA/NNDC/analytic/radioactivedecay, got {src!r}"
        )
        if src.startswith("radioactivedecay"):
            assert "version" in entry["note"].lower() or "0." in entry["note"]


def _ids(kind: str) -> list[str]:
    return [e["id"] for e in _load_golden()["entries"] if e["kind"] == kind]


def _entry(entry_id: str) -> dict:
    for e in _load_golden()["entries"]:
        if e["id"] == entry_id:
            return e
    raise AssertionError(f"missing golden entry {entry_id}")


@pytest.mark.parametrize("entry_id", _ids("nuclide_half_life"))
def test_nuclide_half_life_matches_bundle(entry_id):
    e = _entry(entry_id)
    hl = Nuclide.load(e["nuclide"]).half_life_s
    assert hl == pytest.approx(e["half_life_s"], rel=e["rel_tol"])


@pytest.mark.parametrize("entry_id", _ids("single_activity"))
def test_single_activity(entry_id):
    e = _entry(entry_id)
    got = decayed_activity(e["a0_bq"], Nuclide.load(e["nuclide"]).half_life, e["t_s"])
    assert got == pytest.approx(e["expected_bq"], rel=e["rel_tol"])


@pytest.mark.parametrize("entry_id", _ids("remaining_fraction"))
def test_remaining_fraction(entry_id):
    e = _entry(entry_id)
    if "nuclide" in e:
        hl = Nuclide.load(e["nuclide"]).half_life_s
    else:
        hl = e["half_life_s"]
    got = remaining_fraction(hl, e["t_s"])
    assert got == pytest.approx(e["expected"], rel=e["rel_tol"])


@pytest.mark.parametrize("entry_id", _ids("chain_atoms"))
def test_chain_atoms(entry_id):
    e = _entry(entry_id)
    spec = e["chain"]
    if spec.get("type") == "linear" and "isotopes" in spec:
        chain = DecayChain.from_isotopes(spec["isotopes"])
    elif spec.get("type") == "branching":
        chain = DecayChain.branching(
            spec["parent"],
            spec["branches"],
            lambdas=spec["lambdas"],
        )
    else:
        raise AssertionError(f"unknown chain spec {spec!r}")
    got = chain.at(e["t_s"], n0=e["n0"])
    for name, exp in e["expected"].items():
        assert got[name] == pytest.approx(exp, rel=e["rel_tol"]), (
            f"{entry_id}:{name} got={got[name]!r} expected={exp!r}"
        )
```

- [ ] **Step 2: Run to verify failure (file missing)**

Run: `python -m pytest tests/golden/test_golden.py -v`  
Expected: FAIL / collection error — `golden_values.json` not found.

- [ ] **Step 3: Write `tests/golden/golden_values.json`**

Create the JSON with `schema_version: 1`, `verified_on: "2026-09-23"`, and **all eight entry groups** from the templates above (six half-lives + two activities + three fractions + one linear chain + one branching = thirteen entries total). Copy numeric literals **exactly** as printed in the templates.

Branching entry `chain` object (locked):

```json
{
  "type": "branching",
  "parent": "P",
  "branches": {"D1": 0.6, "D2": 0.4},
  "lambdas": {"P": 0.1, "D1": 0.05, "D2": 0.02}
}
```

- [ ] **Step 4: Run golden suite**

Run: `python -m pytest tests/golden -v`  
Expected: PASS all.

- [ ] **Step 5: Commit**

```bash
git add tests/golden/golden_values.json tests/golden/test_golden.py
git commit -m "test: add golden values file with primary-source provenance"
```

---

### Task 3: radioactivedecay solver-output cross-diff (three scenarios)

**Files:**
- Create: `tests/crosscheck/test_radioactivedecay_solver.py`

**Interfaces:**
- Consumes: `pydecay.decayed_activity`, `pydecay.DecayChain`, `pydecay.Nuclide`; `radioactivedecay.Inventory` (fixture-verified 0.6.1).
- Produces: three pytest tests; module-level `pytest.importorskip("radioactivedecay")`.

**Fixture-verified radioactivedecay 0.6.1 API (do not invent alternates without re-probing):**

```python
from radioactivedecay import Inventory
inv = Inventory({"Co-60": 1e6}, units="Bq")   # contents unit is separate arg
out = inv.decay(10, units="y")                # decay(decay_time: float, units: str)
out.activities()  # dict-like, Bq
out.numbers()     # dict-like, atom counts
```

`Inventory.decay` does **not** accept a unit string as the first positional argument (`decay("10 years")` raises TypeError). Half-life helper already exists in `tests/test_crosscheck.py` as `_rr_half_life_s` — **import it** rather than duplicating:

```python
from tests.test_crosscheck import _rr_half_life_s  # may fail if tests are not a package
```

If `tests` is not importable as a package (no `__init__.py`), **copy** the helper function into this module with a comment `# copied from tests/test_crosscheck.py (Task 11) to avoid package layout change`.

**Year convention (locked):** all cross-diff times pass through `decay(..., units="s")` on the radioactivedecay side and raw seconds on the pydecay side. Never mix `units="y"` with a `* 31557600` second value — radioactivedecay's `year_conv` ≠ Julian year and would inject ~1e-5 relative error, falsely failing `REL_TOL_SOLVER`.

**Tolerance policy (locked):**

| Scenario | λ source | rel tol | Rationale |
|----------|----------|---------|-----------|
| Single isotope activity | **Their** T½ via `_rr_half_life_s("Co-60")` fed into **pydecay** | `1e-6` | Same decay constant both sides → isolates solver |
| Linear 3-species chain atoms | **Their** T½ for Sr-90, Y-90; Zr-90 λ=0 (stable terminal) fed into pydecay `DecayChain` | `1e-6` | Same λs; compare Sr-90/Y-90/Zr-90 atom vectors |
| Branching star | Analytical closed form in-test (radioactivedecay has no custom-λ star API) | `1e-9` | Design allows call-site confirmation at implement time; custom synthetic branches unsupported — analytic oracle is the external formula |

For the single-isotope scenario, also assert **pydecay vs Inventory** when both use *their* T½: pydecay call uses `half_life=_rr_half_life_s("Co-60")`, Inventory uses bundled Co-60 — identical data.

- [ ] **Step 1: Write failing tests**

Create `tests/crosscheck/test_radioactivedecay_solver.py`:

```python
"""Solver-output cross-diff vs radioactivedecay 0.6.1 (design spec sections 4-5).

Half-life *data* drift is covered by tests/test_crosscheck.py.
This module compares *decay results* with matched decay constants.
"""

from __future__ import annotations

import math

import pytest

rr = pytest.importorskip("radioactivedecay", reason="radioactivedecay not installed")
from radioactivedecay import Inventory  # noqa: E402

from pydecay import DecayChain, Nuclide, decayed_activity  # noqa: E402

REL_TOL_SOLVER = 1e-6
REL_TOL_ANALYTIC = 1e-9


def _rr_half_life_s(name: str) -> float:
    """Half-life in seconds from radioactivedecay (copied from test_crosscheck)."""
    nuc = rr.Nuclide(name)
    method = getattr(nuc, "half_life", None)
    if callable(method):
        return float(method(units="s"))
    raise AssertionError(f"cannot locate half-life on radioactivedecay.Nuclide({name})")


def test_single_isotope_activity_matches_inventory():
    """Scenario 1: Co-60, 1e6 Bq, 10 Julian years in seconds — matched T½.

    Both sides use ``units='s'`` so radioactivedecay's year_conv cannot
    inject a ~1e-5 relative error that would falsely fail REL_TOL_SOLVER.
    """
    hl_rr = _rr_half_life_s("Co-60")
    t_s = 10.0 * 31557600.0
    ours = decayed_activity(1.0e6, hl_rr, t_s)
    inv = Inventory({"Co-60": 1.0e6}, units="Bq")
    theirs = float(dict(inv.decay(t_s, units="s").activities())["Co-60"])
    rel = abs(ours - theirs) / theirs
    assert rel <= REL_TOL_SOLVER, (
        f"single Co-60 activity mismatch: ours={ours!r} theirs={theirs!r} "
        f"rel={rel:.3e} hl_rr={hl_rr!r} t_s={t_s!r} "
        f"pydecay={__import__('pydecay').__version__} "
        f"radioactivedecay={rr.__version__}"
    )


def test_linear_chain_atoms_match_inventory():
    """Scenario 2: Sr-90 -> Y-90 -> Zr-90(stable), parent-only, 30 Julian years in s."""
    t_s = 30.0 * 31557600.0
    hl_sr = _rr_half_life_s("Sr-90")
    hl_y = _rr_half_life_s("Y-90")
    chain = DecayChain([math.log(2) / hl_sr, math.log(2) / hl_y, 0.0],
                       names=["Sr-90", "Y-90", "Zr-90"])
    ours = chain.at(t_s, n0={"Sr-90": 1.0, "Y-90": 0.0, "Zr-90": 0.0})
    inv0 = Inventory({"Sr-90": 1.0e6}, units="Bq")
    theirs_parent0 = float(dict(inv0.numbers())["Sr-90"])
    theirs_nums = dict(inv0.decay(t_s, units="s").numbers())
    for name in ("Sr-90", "Y-90", "Zr-90"):
        a = ours[name]  # n0 parent atoms = 1.0
        b = float(theirs_nums.get(name, 0.0)) / theirs_parent0
        denom = b if b > 1e-30 else 1e-30
        rel = abs(a - b) / denom
        assert rel <= REL_TOL_SOLVER, (
            f"chain {name}: ours_frac={a!r} theirs_frac={b!r} rel={rel:.3e} "
            f"t_s={t_s!r} rr={rr.__version__}"
        )


def test_branching_star_matches_closed_form():
    """Scenario 3: synthetic P->D1/D2 star vs Bateman-star closed form.

    radioactivedecay 0.6.1 cannot inject custom lambdas into Inventory;
    external formula is the oracle (design section 5 call-site confirmation).
    """
    lp, ld1, ld2 = 0.1, 0.05, 0.02
    t = 10.0
    chain = DecayChain.branching(
        "P", {"D1": 0.6, "D2": 0.4}, lambdas={"P": lp, "D1": ld1, "D2": ld2}
    )
    got = chain.at(t)

    def daughter_atoms(f: float, lam_p: float, lam_d: float) -> float:
        return f * lam_p / (lam_d - lam_p) * (math.exp(-lam_p * t) - math.exp(-lam_d * t))

    exp_p = math.exp(-lp * t)
    exp_d1 = daughter_atoms(0.6, lp, ld1)
    exp_d2 = daughter_atoms(0.4, lp, ld2)
    for name, exp in (("P", exp_p), ("D1", exp_d1), ("D2", exp_d2)):
        rel = abs(got[name] - exp) / exp
        assert rel <= REL_TOL_ANALYTIC, (
            f"branch {name}: got={got[name]!r} expected={exp!r} rel={rel:.3e}"
        )
```

- [ ] **Step 2: Run to verify failure or pass baseline**

Run: `python -m pytest tests/crosscheck/test_radioactivedecay_solver.py -v`  
Expected: If all three PASS immediately, that is valid (implementation already correct) — still run full file. If single/chain FAIL with rel > 1e-6, proceed to Step 3 investigation (do not loosen tol without a written note in the commit message).

- [ ] **Step 3: Investigate any failure (divergence policy)**

If scenario 1 or 2 fails:
1. Print both half-lives and the exact `t_s` used.
2. Confirm pydecay received `hl_rr` (not bundled IAEA T½).
3. Confirm both sides used `units="s"` (year_conv must not be in play).
4. Check whether Inventory's scipy path and our expm/Bateman disagree beyond 1e-6 for this λ ratio (Sr-90/Y-90 is well separated — should use Bateman on our side).
5. Only after a root cause is identified, adjust code or record a justified deviation in the assert message and `docs/data-sources.md`.

Re-run until green or deviation is documented and accepted.

- [ ] **Step 4: Run the full crosscheck directory**

Run: `python -m pytest tests/crosscheck -v`  
Expected: PASS (including existing half-life drift tests).

- [ ] **Step 5: Commit**

```bash
git add tests/crosscheck/test_radioactivedecay_solver.py
git commit -m "test: add radioactivedecay solver cross-diff for three scenarios"
```

(If Step 3 required a docs edit, include `docs/data-sources.md` in the same commit.)

---

### Task 4: Hypothesis invariant suite

**Files:**
- Create: `tests/property/test_invariants.py`

**Interfaces:**
- Consumes: `pydecay.remaining_fraction`, `pydecay.decayed_activity`, `pydecay.decayed_atoms`, `pydecay.DecayChain`, `pydecay._solver.use_bateman` / `solve`.
- Produces: property tests only; no runtime exports.

**Invariants (locked):**

1. `remaining_fraction(T, t) ∈ [0, 1]` and non-increasing in `t` for fixed `T`.
2. `decayed_activity` non-increasing in `t` for fixed `A0`, `T`.
3. `decayed_atoms(N, T, T) ≈ N/2` rel `1e-12`.
4. Linear chain conservation: parent-only n0, terminal λ=0, sum of atoms ≈ N0 (rel `1e-9`).
5. Branching atom counts all `>= 0`.
6. Well-separated linear chain: `solve` (Bateman path) ≈ expm reference rel `1e-9`.

**Strategies (locked):** half-life log-uniform `[1e-3, 1e17]` seconds; `t` uniform `[0, 5*T]`; chain length 2–4; λs sorted for separation test; `@settings(deadline=None, max_examples=50)` on matrix tests; total suite target **< 10s**.

- [ ] **Step 1: Write failing property tests**

Create `tests/property/test_invariants.py`:

```python
"""Hypothesis invariants: bounds, monotonicity, conservation, solver agreement."""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st
from scipy.linalg import expm

from pydecay import decayed_activity, decayed_atoms, remaining_fraction
from pydecay._solver import solve
from pydecay.graph import DecayGraph

finite_positive = st.floats(
    min_value=1e-3, max_value=1e17, allow_nan=False, allow_infinity=False
)


@given(half_life=finite_positive, t=st.floats(min_value=0.0, max_value=1e18, allow_nan=False))
def test_remaining_fraction_bounds(half_life, t):
    f = remaining_fraction(half_life, t)
    assert 0.0 <= f <= 1.0


@given(
    half_life=finite_positive,
    t1=st.floats(min_value=0.0, max_value=1e18, allow_nan=False),
    delta=st.floats(min_value=0.0, max_value=1e18, allow_nan=False),
)
def test_remaining_fraction_monotone(half_life, t1, delta):
    f1 = remaining_fraction(half_life, t1)
    f2 = remaining_fraction(half_life, t1 + delta)
    assert f2 <= f1 + 1e-15


@given(
    a0=st.floats(min_value=0.0, max_value=1e30, allow_nan=False, allow_infinity=False),
    half_life=finite_positive,
    t1=st.floats(min_value=0.0, max_value=1e18, allow_nan=False),
    delta=st.floats(min_value=0.0, max_value=1e18, allow_nan=False),
)
def test_activity_monotone(a0, half_life, t1, delta):
    a1 = decayed_activity(a0, half_life, t1)
    a2 = decayed_activity(a0, half_life, t1 + delta)
    assert a2 <= a1 + 1e-6 * max(a1, 1.0)


@given(
    n0=st.floats(min_value=1.0, max_value=1e20, allow_nan=False),
    half_life=finite_positive,
)
def test_half_life_identity(n0, half_life):
    n = decayed_atoms(n0, half_life, half_life)
    assert abs(n - n0 / 2.0) <= 1e-12 * (n0 / 2.0)


@settings(deadline=None, max_examples=30)
@given(
    lam_parent=st.floats(min_value=1e-6, max_value=1.0),
    lam_mid=st.floats(min_value=1e-6, max_value=1.0),
    t=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
    n0=st.floats(min_value=1.0, max_value=1e12, allow_nan=False),
)
def test_linear_chain_conservation(lam_parent, lam_mid, t, n0):
    """Parent -> mid -> stable (lambda=0): atoms only transform, sum conserved."""
    g = DecayGraph.linear([lam_parent, lam_mid, 0.0])
    out = solve(g, [n0, 0.0, 0.0], t)
    assert abs(out.sum() - n0) <= 1e-9 * n0
    assert np.all(out >= -1e-9 * n0)


@settings(deadline=None, max_examples=30)
@given(
    lam_parent=st.floats(min_value=1e-4, max_value=1.0),
    t=st.floats(min_value=0.0, max_value=50.0, allow_nan=False),
)
def test_branching_nonnegative(lam_parent, t):
    fractions = ((0.0, 0.6, 0.4), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    g = DecayGraph.branching(
        (lam_parent, 10.0 * lam_parent, 20.0 * lam_parent),
        fractions,
        names=["P", "D1", "D2"],
    )
    out = solve(g, [1.0, 0.0, 0.0], t)
    assert np.all(out >= -1e-12)


@settings(deadline=None, max_examples=40)
@given(
    lam1=st.floats(min_value=1e-4, max_value=1.0),
    ratio=st.floats(min_value=100.0, max_value=1e6),
    t=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
)
def test_bateman_matches_expm_well_separated(lam1, ratio, t):
    lam2 = lam1 / ratio
    g = DecayGraph.linear([lam1, lam2])
    n0 = [1.0e6, 0.0]
    b = solve(g, n0, t)
    e = expm(g.generator() * t) @ np.asarray(n0, dtype=np.float64)
    np.testing.assert_allclose(b, e, rtol=1e-9, atol=1e-18)
```

- [ ] **Step 2: Run property suite**

Run: `python -m pytest tests/property -v --durations=5`  
Expected: PASS; wall time < 10s for this directory.

- [ ] **Step 3: Commit**

```bash
git add tests/property/test_invariants.py
git commit -m "test: add hypothesis invariant suite for decay laws and chains"
```

---

### Task 5: CI coverage flag + docs (contract, provenance, changelog)

**Files:**
- Modify: `.github/workflows/ci.yml:32` (test job pytest line)
- Modify: `docs/data-sources.md` (append golden section)
- Modify: `docs/api.md` (module-level functions intro + InvalidTimeError row context)
- Modify: `docs/quickstart.md` (one contract sentence)
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: Task 2 golden file path and `verified_on`; existing `InvalidTimeError` behavior (v1, unchanged).
- Produces: CI fails under 90% coverage even if pyproject is ignored by an old runner; docs state golden provenance and `t >= 0` contract.

- [ ] **Step 1: Fail CI under coverage floor on the command line**

In `.github/workflows/ci.yml`, change:

```yaml
      - run: pytest --cov=pydecay --cov-report=term-missing
```

to:

```yaml
      - run: pytest --cov=pydecay --cov-report=term-missing --cov-fail-under=90
```

- [ ] **Step 2: Append golden provenance to `docs/data-sources.md`**

Add section:

```markdown
## Golden values

`tests/golden/golden_values.json` freezes externally checked tuples for CI:

- **verified_on** records the last hand-check against the primary source
  (IAEA Live Chart; analytic formulas documented per entry).
- Entry `source` / `source_url` / `note` are mandatory — bare numbers are
  rejected by `tests/golden/test_golden.py`.
- CI never re-fetches NNDC/IAEA; it only asserts the bundle still matches
  the frozen goldens.
- To re-verify: open each `source_url`, compare `half_life_s`, update
  `verified_on` and any changed values in the same commit.
```

- [ ] **Step 3: Document `t >= 0` contract in `docs/api.md`**

Under the “Module-level functions” heading, insert:

```markdown
**Time contract:** every public decay function requires `time >= 0`
(finite). Negative time raises `InvalidTimeError`. Back-calculating
earlier activities (“what was it yesterday?”) is out of scope for v2.
```

- [ ] **Step 4: Document `t >= 0` contract in `docs/quickstart.md`**

After the first decay example paragraph, insert:

```markdown
All times must be `>= 0`; negative time raises `InvalidTimeError`.
Back-calculation is not supported in v2.
```

- [ ] **Step 5: Changelog entry**

In `CHANGELOG.md`, under the existing/unreleased section (create `## [Unreleased]` if missing):

```markdown
### Added
- Golden-values regression suite (`tests/golden/`) with primary-source provenance.
- Solver-output cross-diff vs `radioactivedecay` (single isotope, linear chain, branching).
- Hypothesis invariant tests for decay laws and chains.
- CI coverage floor `--cov-fail-under=90` on the test job.
```

- [ ] **Step 6: Build docs strictly**

Run: `python -m mkdocs build --strict`  
Expected: no warnings/errors (if mkdocs not installed: `python -m pip install -e ".[docs]"` first).

- [ ] **Step 7: Commit**

```bash
git add .github/workflows/ci.yml docs/data-sources.md docs/api.md docs/quickstart.md CHANGELOG.md
git commit -m "ci: enforce coverage floor; docs: golden provenance and t>=0 contract"
```

---

### Task 6: Full gate verification

**Files:** none (verification only).

**Interfaces:**
- Consumes: all prior tasks.
- Produces: green evidence that the plan is done.

- [ ] **Step 1: Full test suite with coverage**

Run: `python -m pytest --cov=pydecay --cov-report=term-missing --cov-fail-under=90`  
Expected: all tests pass (existing 117+ plus golden, crosscheck solver, property); coverage ≥ 90%.

- [ ] **Step 2: Lint and types**

Run: `python -m ruff check src tests`  
Expected: no findings.

Run: `python -m mypy`  
Expected: Success (strict, `src` only).

- [ ] **Step 3: Confirm public API unchanged**

Run: `python -c "import pydecay; assert len(pydecay.__all__)==13; print(pydecay.__version__)"`  
Expected: `13` and `0.1.0`.

- [ ] **Step 4: Confirm near-degenerate + half-life crosscheck still present (regression of v1 hardening)**

Run: `python -m pytest tests/test_solver.py tests/test_crosscheck.py -v`  
Expected: PASS (including `test_spec_2_3_near_degenerate_is_finite`, `test_half_life_drift_within_tolerance`).

- [ ] **Step 5: Final commit if any gate fix was needed**

Only if Steps 1–4 required code/doc fixes:

```bash
git add -A
git commit -m "test: fix issues found during trust hardening gate run"
```

If nothing failed, skip this commit.

---

## Definition of done (maps to spec §12)

- [ ] Golden set present, schema-valid, fully sourced, covering hour → Gy half-lives + degenerate-free analytic chain + branching.
- [ ] Three solver scenarios implemented (third uses analytic oracle — call-site deviation from raw Inventory branching documented in Task 3).
- [ ] Hypothesis suite green, runtime ≲ 10s for `tests/property`.
- [ ] `--cov-fail-under=90` on CI test job; local full run ≥ 90%.
- [ ] Docs: golden provenance, `t >= 0` contract in api + quickstart; math dispatch table already documents `DEGENERATE_EPS` (no change required).
- [ ] No public API breakage; v1 near-degenerate + half-life crosscheck still green.
- [ ] Each task landed as its own commit.
- [ ] ruff + mypy clean.

## Spec coverage checklist (self-review)

| Spec section | Plan task |
|--------------|-----------|
| §2 Q2 test deps | Task 1 |
| §4 golden file + runner | Task 2 |
| §5 cross-diff 3 scenarios | Task 3 |
| §6 property tests | Task 4 |
| §7 near-degenerate guard | **Already in v1** — re-verified in Task 6 Step 4 |
| §8 CI coverage | Task 5 Step 1 + Task 6 |
| §9 docs | Task 5 |
| §10 error handling | Task 2/3 assert messages (no new exceptions) |
| §11 commits | each task ends with commit |
| §12 DoD | Definition of done above |
