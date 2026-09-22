# pydecay v1 — Design Specification

Date: 2026-09-22
Status: Approved (section-by-section design review)
Ground truth: "Radioactive Decay Package — v1 Technical Reference" (user-provided; formulas cite Bateman 1910, Cetnar 2006, Krane, ICRP-107, NNDC, IAEA, NUBASE 2020, BIPM SI Brochure, NIST SP 811)

## 1. Goals and scope

Build a Python package `pydecay` implementing radioactive decay math:

- **In v1:** single-isotope analytical decay (§1 of the reference); linear unbranched decay chains via Bateman with a numerically stable reformulation; **branching chains** (one parent, multiple daughter paths with branching ratios) and multi-parent systems, solved by matrix exponential; bundled curated nuclide dataset (~40 isotopes); unit conversions (atoms ↔ mass ↔ activity, Bq/Ci).
- **Not in v1:** time-dependent decay constants (no `solve_ivp` path — constant rates make the system LTI, so `expm` is exact); ingrowth from external sources; transport/geometry; full ~3,300-nuclide chart; random/stochastic decay simulation.

Success criterion: all §6 worked examples of the reference doc pass as tests against values sourced from IAEA (not from the doc's table itself), degenerate-λ regression passes without NaN, and outputs diff cleanly against `radioactivedecay` within documented evaluation tolerance.

## 2. Decisions (from design review)

| Decision | Choice |
|---|---|
| Path classification | Architectural (greenfield) |
| Architecture | **Approach A**: layered pure-math core + thin API |
| Dependencies | NumPy + SciPy + **pint** |
| Python floor | **3.10+** |
| Chain scope | **Linear + branching in v1** |
| Nuclide data | **IAEA Live Chart primary**, bundled JSON; radioactivedecay used only in diff tests (report drift, fail only past tolerance) |
| Branching solver | `scipy.linalg.expm` on generator matrix (no `solve_ivp` in v1) |

## 3. Architecture and module layout

```
pydecay/
├── pyproject.toml            # hatchling; deps: numpy, scipy, pint; requires-python >=3.10
├── src/pydecay/
│   ├── __init__.py           # public API re-exports + __version__ only
│   ├── api.py                # pint-aware convenience functions (decayed_atoms, etc.)
│   ├── decay.py              # §1 single-isotope closed form (pure math, SI floats)
│   ├── chain.py              # §2 domain object DecayChain (pint at edges)
│   ├── _solver.py            # float-only kernels: guarded Bateman + expm dispatch
│   ├── graph.py              # species/edge model → generator matrix (branching support)
│   ├── units.py              # §4 conversions at API boundary (pint); internal seconds/Bq/N
│   ├── nuclide.py            # Nuclide dataclass + JSON loader/validation (pint at edges)
│   ├── exceptions.py         # PyDecayError hierarchy
│   └── data/
│       ├── nuclides.json     # bundled IAEA-sourced subset + per-entry source/date metadata
│       └── _fetch_iaea.py    # build-time script (excluded from wheel/API) to regenerate JSON
└── tests/
    ├── test_known_values.py  # §6 worked examples
    ├── test_decay.py         # identities: N(T½)=N₀/2, N(τ)=N₀/e, activity law
    ├── test_chain.py         # Bateman vs expm, degenerate regression, branching conservation
    ├── test_units.py         # Bq↔Ci, mass↔atoms, plain-float vs pint parity
    ├── test_data.py          # schema, metadata completeness, loader errors
    └── test_crosscheck.py    # diff vs radioactivedecay (optional dep; skip if absent)
```

Boundary rules:

- **Pure SI modules** — `decay.py`, `graph.py`, `_solver.py` never import pint: floats/ndarrays in seconds/atoms/Bq only, trivially testable.
- **Pint-at-edge modules** — `units.py`, `nuclide.py`, `chain.py`, `api.py`, `__init__.py` may use pint on their public surface (accepting strings/Quantities, returning Quantities per the mirroring rule in §5); every call down into the pure modules passes canonical floats.
- `data/_fetch_iaea.py` is a build-time tool, excluded from the wheel.

## 4. Core math (from the reference doc — tests are written against these)

### 4.1 Single isotope (decay.py)

- ODE: `dN/dt = −λN`; closed form `N(t) = N₀·e^(−λt)` — implemented as the closed form, never numerically integrated.
- `λ = ln(2)/T½`; `τ = 1/λ = T½/ln(2)`.
- Identities asserted in tests: `N(T½) = N₀/2` exactly; `N(τ) = N₀/e`.
- Activity: `A(t) = λN(t) = A₀·e^(−λt)`; internal unit Bq; `1 Ci = 3.7e10 Bq` (NIST SP 811).

### 4.2 Chains (chain.py + graph.py)

System for linear chain (species 1 → 2 → … → n):

```
dN₁/dt = −λ₁N₁
dNᵢ/dt = λᵢ₋₁Nᵢ₋₁ − λᵢNᵢ    (i = 2..n)
```

Bateman (1910) closed form for parent-only initial condition:

```
Nₙ(t) = N₁₀ · (∏ᵢ₌₁ⁿ⁻¹ λᵢ) · Σₖ₌₁ⁿ [ e^(−λₖt) / ∏ⱼ≠ₖ (λⱼ − λₖ) ]
```

**Stability caveat (critical):** when λᵢ ≈ λⱼ the denominator `(λⱼ − λₖ) → 0` and the naive formula blows up even though the physical answer is finite. Never ship unguarded.

Solver dispatch (internal, automatic — users never choose):

1. Build generator matrix `G` in `graph.py` with the convention `dN/dt = G @ N`: `G[i,i] = −λᵢ`; for each edge j→i (j decays into i) with branching fraction `fⱼᵢ`: `G[i,j] += λⱼ·fⱼᵢ` (destination row, source column — subdiagonal for linear chains). Note: the reference doc's index notation `A[i−1][i] = λᵢ₋₁` is transposed relative to this convention; we use the form verified by the daughter-ingrowth test. Linear unbranched chains are the special case `f = 1`.
2. Path selection:
   - Linear, unbranched, parent-only initial condition (`N₀` nonzero only for species 1), and `min pairwise |λᵢ−λⱼ| ≥ ε·max(λ)` → **Bateman closed form** (fast, exact when well-separated). ε default `1e-8`, overridable per chain.
   - Branching present **or** any degenerate pair (`|λᵢ−λⱼ| < ε·max(λ)`) **or** nonzero initial daughters → `scipy.linalg.expm(G·t) @ N(0)` — bulletproof; this is the required guard for the §2.3 regression case (λ₁ = 0.6931, λ₂ = 0.6932 must be finite, no NaN).
   - This realizes fix option 2 from the reference §2.2 (expm fallback). Cetnar's reformulation (fix option 1) is deferred to a v2 optimization; it changes performance characteristics, not results, once the expm guard is in place.
3. `t = 0` shortcut: return a copy of `N(0)` with no solver call.
4. Branching never touches Bateman — it is a matrix-exponential problem by construction. Constant rates ⇒ LTI ⇒ `expm` is exact; `solve_ivp` is unnecessary in v1.

Conservation invariant (tests): for a closed chain ending in a stable nuclide, `ΣNᵢ(t) = ΣNᵢ(0)`.

`decay.py` stays independent of the chain machinery: single-isotope calls use `N₀·e^(−λt)` directly.

## 5. Public API surface

```python
from pydecay import (
    Nuclide, DecayChain,
    decayed_atoms, decayed_activity, remaining_fraction,
)

# --- data ---
i131 = Nuclide.load("I-131")   # bundled JSON; .half_life (pint, seconds), .lambda_ (1/s),
                                # .decay_modes, .source, .fetched

# --- single isotope (§1): plain numbers or pint Quantities ---
N = decayed_atoms(N0=1e6, half_life="8.02 days", time="24 hours")
A = decayed_activity(A0=1000.0, half_life="8.02 days", time="8.02 days")  # → 500.0
f = remaining_fraction(half_life="8.02 days", time="8.02 days")           # → 0.5 (always float)
A = i131.activity(N=1e6, t="8.02 days")          # Bq or pint

# --- chains (§2) ---
chain = DecayChain.from_isotopes(["U-238", "Th-234", ...])   # linear, from data
chain = DecayChain(lambdas=[0.6931, 0.6932], names=["A", "B"])  # explicit λ's
chain = DecayChain.branching(                                  # branching ratios
    parent="P", branches={"D1": 0.6, "D2": 0.3},
    lambdas={"P": 0.6931, "D1": 1e-5, "D2": 2e-5})  # λ from data when name is known, else required

N_t = chain.at(t="1 day")        # dict: species → atoms (or pint Quantity)
A_t = chain.activity(t="1 day")  # dict: species → Bq
```

API rules:

- **Return-kind mirroring rule (precise):** each result mirrors the kind of the *primary numeric input it derives from* — `decayed_atoms` mirrors `N0`; `decayed_activity` mirrors `A0`; `Nuclide.activity` and `DecayChain.at`/`.activity` mirror `n0` (default: plain floats). Quantity in → Quantity out (same kind of unit); float in → float out. String inputs on unit-typed args (`t`, `half_life`) never change output kind; they parse via pint at the boundary. `remaining_fraction` is dimensionless and **always returns float**.
- Strings accepted for convenience (`"8.02 days"`) via pint's parser, at the public boundary only.
- Internal canonical units: time = seconds (float), atoms = float, activity = Bq (float). Plain-float convention: `t` in seconds, `A` in Bq, `N` in atoms. pint atoms use the package-defined `atom` unit (dimensionless counting unit on the shared registry).
- `DecayChain` computes lazily; solver dispatch is an implementation detail.
- `DecayChain` default initial condition: parent `N₀ = 1.0`, all others 0 (plain floats).
- Branching topology in v1: star (one parent → terminal daughters); linear chains compose only as pure linear.
- `lambda_` / half-life exposed as read-only properties; no mutation API in v1.

## 6. Units (units.py)

Single conversion chokepoint:

- `to_seconds(t)` / inverse; `atoms ↔ grams` using atomic mass from the nuclide record and `Nₐ = 6.02214076e23 /mol` (exact, 2019 SI, BIPM); `Bq ↔ Ci` with `1 Ci = 3.7e10 Bq`.
- pint `Quantity` → canonical float inbound; canonical float → same unit (or pint default: s / atoms / Bq) outbound.
- Units library decision: **pint** (approved), used only at the boundary.

## 7. Nuclide data (data/nuclides.json)

- Source: **IAEA Live Chart of Nuclides** (`nds.iaea.org/relnsd/vcharthtml/VChartHTML.html`), fetched via its JSON API by `data/_fetch_iaea.py` at build time.
- Curated subset: ~40 medically/industrially common isotopes (must include the reference doc's six: Co-60, Cs-137, I-131, C-14, U-238, Tc-99m, plus common chain/dating/imaging members).
- Schema (one record per nuclide; loader requires every key):

```json
{
  "I-131": {
    "half_life_s": 692256.0,
    "atomic_mass_u": 130.9061,
    "decay_modes": [{"mode": "beta-minus", "branch": 1.0}],
    "source": "IAEA Live Chart of Nuclides (nds.iaea.org)",
    "source_url": "https://nds.iaea.org/relnsd/vcharthtml/VChartHTML.html",
    "fetched": "2026-09-22",
    "half_life_uncertainty_s": null
  }
}
```

- Every entry records source, source_url, and fetch date. No hand-typed half-lives.
- Cross-check: `test_crosscheck.py` diffs our half-lives against `radioactivedecay`'s ICRP-107 values — **reports** evaluation drift, **fails** only beyond relative tolerance `1e-3`; skipped entirely if radioactivedecay is not installed (optional test dependency).
- When reference-doc table values disagree with IAEA values, **IAEA wins**; the doc's numbers are treated as secondary.

## 8. Error handling (exceptions.py)

Single hierarchy rooted at `PyDecayError`:

- `NuclideNotFoundError` — unknown isotope name at load time.
- `InvalidHalfLifeError` — λ ≤ 0, NaN, or non-finite in data or API input.
- `InvalidTimeError` — t < 0 (negative time rejected in v1; no "before t=0" ingrowth semantics).
- `ChainDefinitionError` — empty chain, λ list length mismatch, branching fractions summing to > 1 (sum ≤ 1 allowed; remainder = decay to untracked sink, documented), or λ = 0 on a non-terminal species (λ = 0 allowed only for terminal/stable species; λ < 0 always rejected).
- `DataFormatError` — bundled JSON record missing required keys or carrying non-parseable values.
- `UnitError` — unparseable unit string or dimensionally wrong pint input (e.g. `"5 meters"` as time).
- Solvers assert finiteness of outputs; on scipy failure, raise `PyDecayError` wrapping the original error. Never return NaN silently.

## 9. Testing strategy (pytest)

1. `test_known_values.py` — §6 worked examples: I-131 1000 Bq → 500 Bq after one T½; → ≈31.25 Bq after 5 T½ (1000 × 0.5⁵); same pattern for Co-60, Cs-137, C-14, U-238, Tc-99m using **bundled IAEA values** (doc table only cross-referenced).
2. `test_decay.py` — `N(T½)=N₀/2`, `N(τ)=N₀/e` at `rel=1e-12`; `A(t)=λN(t)`; mass↔atom roundtrip.
3. `test_chain.py` — Bateman vs expm agreement on well-separated chains (~1e-10); §2.3 degenerate regression (λ = 0.6931 / 0.6932 → finite, matches expm, no NaN); branching conservation; `t=0` returns input.
4. `test_units.py` — Bq/Ci, s/days/years, plain-float vs pint parity of results.
5. `test_data.py` — every record has source + fetched keys; loader rejects malformed records with the right exception.
6. `test_crosscheck.py` — radioactivedecay diff (report drift, fail past 1e-3 relative), skip-if-absent.

Local quality gate: `pytest`, `ruff check`, `mypy src`.

## 10. Out-of-scope / deferred (v2 candidates)

- Time-dependent rates / external production terms (`solve_ivp` path).
- Full ICRP-107 / ENSDF dataset shipping.
- Stochastic decay simulation; dose calculations; spectrum/energy data beyond decay modes.
- Branched-with-cycles or non-linear systems (not physical for decay, excluded by definition).

## 11. Verification sources (audit trail)

- Formulas: Krane *Introductory Nuclear Physics*; Bateman (1910) Proc. Cambridge Phil. Soc. 15, 423–427; Cetnar (2006) Ann. Nucl. Energy 33, 640–645.
- Data: IAEA Live Chart (primary, bundled); ICRP-107, NNDC ENSDF/Wallet Cards, NUBASE 2020 (cross-reference); radioactivedecay (implementation diff only).
- Constants: BIPM SI Brochure (Nₐ), NIST SP 811 (Ci).
- Any conflict resolves to the primary source (NNDC/IAEA), never to this spec or the reference doc.
