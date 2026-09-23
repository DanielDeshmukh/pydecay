# pydecay Trust Hardening — Design Spec

**Date:** 2026-09-23  
**Status:** Approved (design gate)  
**Scope:** v2 sub-project 1 — external validation + numerical robustness  
**Out of scope:** ICRP-107 bulk import, API redesign (Inventory/CLI/plots), differentiation features, SymPy high-precision mode, Trusted Publishing OIDC (later sub-projects)

---

## 1. Problem statement

v1's 117-test suite proves **internal consistency** (our Bateman solver agrees with our λ values; our unit conversions round-trip). It does not yet prove **external correctness** — that our numbers match evaluated nuclear data or an independent implementation. This sub-project closes that gap and hardens the one known numerical failure mode (near-degenerate λ) before anything else builds on the foundation.

**Divergence policy (decided):** when an external cross-check disagrees with pydecay, this sub-project stays open until the divergence is understood and resolved — either a bug fix in pydecay or a documented, justified deviation. No xfail/report-only escape hatch.

---

## 2. Decisions (clarifying Q&A)

| # | Question | Decision |
|---|----------|----------|
| Q1 | Divergence policy | **Fix before done** — resolve or document-with-justification before exit |
| Q2 | Test dependencies | **`radioactivedecay` + `hypothesis` as `[project.optional-dependencies] test` extra** — not installed by plain `pip install pydecay` |
| Q3a | Near-degenerate guard | **expm fallback** (not Cetnar); Cetnar deferred |
| Q3b | SymPy high-precision mode | **Defer** to a later sub-project |
| Q4 | Primary-source T½/λ verification | **Hand-curated golden set** with source URLs + access date; no live NNDC scrape in CI |
| Q5 | Negative time contract | **Keep rejecting** `t < 0` (`InvalidTimeError`); document back-calculation as out of scope for v2 |

---

## 3. Approach

**Approach A — layered test pyramid on the existing suite** (chosen over a single `tests/trust/` mega-module and over a hypothesis-first rewrite of existing tests).

Additive layers; no existing test rewritten. One production code change: near-degenerate guard in `_solver.py`.

### Components

| Path | Action | Purpose |
|------|--------|---------|
| `pyproject.toml` | modify | `[project.optional-dependencies] test = ["pytest", "pytest-cov", "hypothesis", "radioactivedecay>=0.6,<1", ...]` |
| `src/pydecay/_solver.py` | modify | Near-degenerate guard → expm; export `DEGENERATE_EPS` |
| `tests/golden/golden_values.json` | new | Hand-curated verified tuples with provenance |
| `tests/golden/test_golden.py` | new | Parametrized runner over golden entries |
| `tests/crosscheck/test_radioactivedecay.py` | new | Live cross-diff, 3 scenarios |
| `tests/property/test_invariants.py` | new | Hypothesis invariant suite |
| `tests/test_solver.py` | extend | Permanent near-degenerate regression |
| `docs/data-sources.md` | extend | Golden-set provenance + re-verification notes |
| `docs/math.md` | extend | Near-degenerate method switch paragraph |
| `docs/api.md` / `docs/quickstart.md` | extend | Explicit `t >= 0` contract sentence |
| `.github/workflows/ci.yml` | modify | Install `.[test]`; `--cov-fail-under=90` |

**No public API changes.** `pydecay.__all__` remains the same 13 names. Only observable behavior change: near-degenerate chains that previously produced non-finite garbage now return correct finite values via expm (strictly a bug fix).

---

## 4. Golden-values file

### Schema (`tests/golden/golden_values.json`)

```json
{
  "schema_version": 1,
  "verified_on": "YYYY-MM-DD",
  "entries": [
    {
      "id": "co60_halflife_iaea",
      "kind": "nuclide_half_life",
      "nuclide": "Co-60",
      "half_life_s": 1.66344e+08,
      "rel_tol": 1e-4,
      "source": "IAEA Live Chart",
      "source_url": "https://www-nds.iaea.org/relnsd/v0/data?fields=ground_states&nuclides=60co",
      "note": "5.271 years; matches NNDC Wallet Card value"
    }
  ]
}
```

### Entry kinds (runner dispatch)

| `kind` | Required fields | Assertion |
|--------|-----------------|-----------|
| `nuclide_half_life` | `nuclide`, `half_life_s`, `rel_tol` | `Nuclide.load(nuclide).half_life_s` matches within `rel_tol` |
| `single_isotope` | `nuclide` or explicit `half_life_s`, `n0` or `a0`, `t_s`, `expected`, `rel_tol` | `decayed_atoms` / `decayed_activity` matches |
| `chain_atoms` | `chain` spec, `t_s`, `n0`, `expected` dict, `rel_tol` | `DecayChain.at(t)` matches per species |
| `chain_activity` | same as `chain_atoms` but activity | `DecayChain.activity(t)` matches |

### Coverage requirements

Isotopes spanning half-life scales (5–10 minimum):

| Isotope | Scale | Role |
|---------|-------|------|
| Tc-99m | ~6 hours | short / medical |
| I-131 | ~8 days | medium / medical |
| Co-60 | ~5.27 years | industrial (mandated six) |
| Cs-137 | ~30 years | mandated six |
| C-14 | ~5730 years | long / dating |
| U-238 | ~4.47 Gy | geological |

Plus: one synthetic near-degenerate pair (λ₁=0.6931, λ₂=0.6932) and one branching case (P→D1/D2 0.6/0.4).

### Provenance rule

Every entry **must** cite a primary source (IAEA Live Chart, NNDC Wallet Card) **or** `radioactivedecay` version + function used. No bare numbers. Missing `source`/`source_url` (or `source` describing radioactivedecay without version) → runner fails with a clear schema error.

### Access date

`verified_on` records when values were last hand-checked against the live primary source. CI does not re-fetch; it only asserts our bundled data still matches the frozen golden file.

---

## 5. radioactivedecay cross-diff

**Import guard:** `pytest.importorskip("radioactivedecay")` so bare local envs skip; CI installs `.[test]` so cross-diff always runs there.

### Three required scenarios

| Scenario | Setup | Tolerance |
|----------|-------|-----------|
| Single isotope | Co-60, 1e6 Bq, t = 10 years | rel ≤ 1e-6 |
| 3-link chain | linear parent→daughter→granddaughter, parent-only N0, mid-chain t | atom vector rel ≤ 1e-6 per species |
| Branching | synthetic P→D1/D2 (0.6 / 0.4), same t | atom vector rel ≤ 1e-6 per species |

### What is being isolated

**Solver-only cross-diff first:** pass *our* λ values into both solvers (where the foreign API allows explicit λ) so disagreement means a solver bug, not a data-difference. A secondary variant (optional in this pass) can feed each package its own bundled λs to check *our data* against theirs.

Exact `radioactivedecay` call sites (Inventory vs DecayChain public API) are confirmed at implementation time against the pinned version's docs — design assumes a stable public surface for single-species decay and multi-species chains with explicit λ.

### Divergence failure message

On mismatch, print: both values, absolute Δ, relative error, pydecay version, radioactivedecay version, scenario id. Per policy: investigate and fix before this sub-project is done.

---

## 6. Property-based tests (hypothesis)

**Dependency:** `hypothesis` in the `test` extra.

### Invariants

1. **`remaining_fraction` bounds:** ∀ T½ > 0, t ≥ 0 → result ∈ [0, 1]; non-increasing in t.
2. **Parent activity monotonicity:** t2 ≥ t1 ⇒ `decayed_activity(A0, T, t2) ≤ decayed_activity(A0, T, t1)`.
3. **Half-life identity:** `decayed_atoms(N, T, T) ≈ N/2` (rel tol 1e-12) under random T.
4. **Linear-chain conservation:** parent-only start, no branching ⇒ `sum(chain.at(t).values()) ≈ N0` (atoms only transform; total conserved when terminal handling is closed — assert within numerical tol, document if terminal leak model requires adjustment).
5. **Branching non-negativity:** all atom counts ≥ 0 for t ≥ 0.
6. **Solver agreement:** well-separated λs ⇒ Bateman path ≈ expm path (rel ≤ 1e-9).

### Strategy notes

- T½ log-uniform on [1e-3 s, 1e17 s].
- t uniform on [0, 5·T½] for single-isotope draws.
- Chain lengths 2–4; λs sorted when testing separation.
- `deadline=None` on matrix-heavy tests.
- Cap total property-suite runtime to a few seconds.

---

## 7. Near-degenerate λ guard (only production code change)

### Where

`src/pydecay/_solver.py` — `use_bateman(...)` already consults `min_separation`.

### Change

```python
DEGENERATE_EPS = ...  # module-level constant, documented

def use_bateman(...):
    # existing conditions (linear, parent-only IC, separated λ)
    # PLUS: min_separation > DEGENERATE_EPS
    # else → expm path
```

- Promote threshold to a single named constant `DEGENERATE_EPS`.
- **Exact numeric value:** chosen during implementation as the tightest threshold that makes the synthetic near-degenerate case (λ₁=0.6931, λ₂=0.6932) take the expm path while leaving all existing well-separated fixtures (e.g. Sr-90→Y-90) on Bateman. Start from the existing `min_separation` / `eps` usage in `use_bateman` and tighten only as the regression test requires. Document the chosen value in `docs/math.md`.
- **Do not** implement Cetnar reformulation (deferred).
- expm path already handles equal/near-equal λ (matrix exponential is finite); existing degenerate tests must keep passing.

### Permanent regression test

Synthetic chain λ₁=0.6931, λ₂=0.6932, parent-only IC:

- Result all finite (no inf/nan).
- `use_bateman(...)` returns `False` for this input.
- Values match an independent `scipy.linalg.expm` oracle computed in the test (same math, but locks the dispatch decision).

### Docs

One paragraph in `docs/math.md`: when decay constants fall within `DEGENERATE_EPS`, pydecay switches from Bateman closed-form to matrix exponential; results remain correct, only the method differs.

---

## 8. CI and coverage

- Install `.[test]` so golden / property / cross-diff always run in CI.
- `pytest --cov=pydecay --cov-fail-under=90` (v1 measured ~92%; 90% floor allows new test-only files without forcing 100% on assertion helpers).
- No live NNDC/IAEA network calls in CI (golden file is frozen at authoring time).
- Python version matrix: unchanged from v1 (3.10–3.13 as declared in `pyproject.toml`).

---

## 9. Documentation touchpoints

| File | Addition |
|------|----------|
| `docs/data-sources.md` | "Golden values" subsection: what's verified, access date, how to re-verify by hand |
| `docs/math.md` | Near-degenerate method-switch paragraph + `DEGENERATE_EPS` meaning |
| `docs/api.md`, `docs/quickstart.md` | Explicit contract: `t >= 0` required; back-calculation out of scope for v2 |

---

## 10. Error handling

- No new exception types; `__all__` unchanged.
- Cross-diff and golden failures are plain `assert` with rich diagnostic messages (values, Δ, rel error, versions, source ids).
- Golden JSON loaded in tests via a fixture; malformed entries fail with a clear KeyError/AssertionError message — do **not** couple the test loader to public `DataFormatError` (keep test infrastructure independent of the public surface).

---

## 11. Commit sequence (traceability)

Each step is its own commit, in order:

1. `test: add test extra with radioactivedecay and hypothesis`
2. Red: `test: add near-degenerate regression expecting expm fallback` (fails on current code)
3. Green: `feat(solver): guard near-degenerate lambda with expm fallback`
4. `test: add golden values file and runner`
5. `test: add radioactivedecay cross-diff scenarios`
6. `test: add hypothesis invariant suite`
7. `ci: enforce 90% coverage floor`
8. `docs: document golden provenance, degenerate guard, negative-t contract`

(Strict TDD: commits 2 and 3 are red/green split. If a step spans multiple files, still one commit per logical step above.)

---

## 12. Definition of done

- [ ] All three radioactivedecay scenarios match within rel 1e-6 (or divergence resolved under Q1 policy).
- [ ] Golden set present, schema-valid, fully sourced, covering ~hour → Gy half-life span + degenerate + branching cases.
- [ ] Hypothesis suite green, runtime ≲ 10s.
- [ ] Near-degenerate synthetic chain: finite results, `use_bateman == False`, matches expm oracle.
- [ ] Coverage ≥ 90% under `--cov-fail-under=90`.
- [ ] Docs updated (provenance, method switch, `t >= 0` contract).
- [ ] No public API breakage; existing 117 tests still green.
- [ ] Every step landed as its own commit (Section 11).
- [ ] Full suite + ruff + mypy clean before merge.

---

## 13. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| radioactivedecay API differs from assumptions (Inventory vs explicit-λ) | Confirm call sites against pinned version at implementation; solver-only scenario may need thin adapter |
| Near-degenerate expm path slower for large chains | Guard only trips when λs are close — rare in practice; benchmark later (sub-project 5) |
| Golden values drift from future IAEA re-evaluation | `verified_on` + provenance makes drift intentional to update, never silent |
| Property tests flaky/slow in CI | Fixed seeds where needed, `deadline=None`, example caps |
| Coverage floor fails due to new test-only files | Floor at 90% (below current 92%); measure after adding suites |
