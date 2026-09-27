# pydecay Three-Track Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Per user directive: NO subagents — inline execution only.

**Goal:** Grow pydecay from a published v0.6 utility into a defensible product across three identities — education toolkit (Track A), practitioner utility (Track B), transport-lite platform (Track C) — reaching ~100k+ LOC of genuinely useful code/data.

**Architecture:** Three sequenced tracks over a stable core (`src/pydecay`: decay/chain/inventory/dose/shielding). Track A is content + distribution (landing page, notebooks, paper). Track B is the v0.7 physics/UX release (buildup, full XCOM, extended sources, CLI, plotting). Track C is the v0.8–v1.0 platform (Monte Carlo engine, uncertainty, ENSDF ingestion, neutron, interop). Each track ends in a release; tracks are interleaved only at documented points.

**Tech Stack:** Python ≥3.10 (hatchling, numpy, pint, scipy-adjacent pure math), pytest+ruff+mypy+mkdocs, React/Vite/TS landing page, GitHub Actions CI.

**Specs:**
- Prior design: `docs/superpowers/specs/2026-09-24-pydecay-dose-shielding-design.md`
- Prior handoff: `docs/superpowers/plans/2026-09-24-pydecay-dose-shielding-summary.md`
- This roadmap supersedes ad-hoc "100k LOC" chatting with a sequenced, honest plan.

## Global Constraints

- Python gates (every task): `pytest --cov=pydecay --cov-report=term-missing --cov-fail-under=90`, `ruff check src tests`, `mypy` (strict), CI matrix 3.10–3.13.
- Docs gate: `mkdocs build --strict` (docs/** changes).
- Landing gate: `npm run lint` in `landingpage/` (prettier + tsc + vitest + vite build, currently 231 tests).
- Wheel budget: ≤15 MB total wheel (current 4.35 MB). New bundled data must be compressed (`.json.gz`) if it would exceed ~1 MB raw.
- `__all__` in `src/pydecay/__init__.py` is case-sensitive ASCII-sorted, currently 41 names; every new public export updates it + the export-count test.
- Version discipline: bump `__version__` + landing `package.json` + CHANGELOG `[Unreleased]` per track release; PyPI upload token via env vars only, never in repo or chat logs (prior token from 2026-09-26 should be revoked by user).
- Commits: `git -c core.hooksPath=/dev/null commit -m "<type>: <scope> <subject>"`; push only on user request.
- **Vercel deploy only with explicit user go-ahead (user directive: never deploy unasked).**
- Golden-rule: every numeric claim in code/docs traces to a cited source; tests pin goldens.

## Sequencing & LOC Projection

| Phase | Track | Contents | Est. LOC added |
|---|---|---|---:|
| Now → v0.6.1 | A quick wins | A1 decay catalog dropdown, A2 landing deploy (gated) | +3–5k |
| v0.7 | B (core) | B1 buildup, B2 full XCOM, B3 extended sources, B4 CLI, B5 plotting, B6 release | +30–45k |
| v0.7.x | A (depth) | A3 notebooks, A4 docs cookbook, A5 JOSS paper draft | +6–10k |
| v0.8 → v1.0 | C | C1 MC engine, C2 uncertainty, C3 ENSDF parser, C4 neutron, C5 MCNP writer, C6 benchmarks, C7 release | +20–35k |

Baseline: **68,186 LOC** (2026-09-27). Projected end state: **~120–145k** — every line is a feature, dataset, test, or doc someone can use.

---

## Track A — Education / Teaching Toolkit

### Task A1: Wire DECAY dropdown to full ICRP-107 catalog

**Files:**
- Create: `landingpage/scripts/generate_decay_nuclides.py` (committed generator, precedent: temp `gen_landing_data.py`)
- Create: `landingpage/src/data/decayNuclides.ts` (generated; header comment "GENERATED — do not edit")
- Modify: `landingpage/src/data/nuclides.ts` (keep `demoNuclides` for `featuredIsotopes`; re-export or leave)
- Modify: `landingpage/src/App.tsx:408-470` (`DecayPanel` select) — add filter input + searchable `<select>`
- Test: `landingpage/src/data/decayNuclides.test.ts`, `App.test.tsx` (update decay-tab test for filter)

**Interfaces:**
- Consumes: `src/pydecay/data/icrp107.json` (1498 records; fields include name/id, half-life, element symbol/name — read via `Nuclide.load_all()` semantics from `src/pydecay/nuclide.py:167-183`).
- Produces: `export type DecayNuclide = { id: string; element: string; halfLifeDays: number; displayHalfLife: string; timeUnit: "hours" | "days" | "years"; daysPerUnit: number }` and `export const decayNuclides: DecayNuclide[]` (sorted by id); `DemoNuclide` stays structurally identical so `DecayPanel` code at `App.tsx:417` needs only the source swapped.

- [x] **Step 1: Write the failing generator self-check + data test**

`landingpage/src/data/decayNuclides.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { decayNuclides } from "./decayNuclides";

describe("decayNuclides", () => {
  it("contains the full radionuclide catalog (>= 1200)", () => {
    expect(decayNuclides.length).toBeGreaterThanOrEqual(1200);
  });
  it("keeps the four demo nuclides with identical half-lives", () => {
    const i131 = decayNuclides.find((n) => n.id === "I-131");
    expect(i131?.halfLifeDays).toBeCloseTo(8.0228, 4);
    expect(decayNuclides.some((n) => n.id === "Co-60")).toBe(true);
    expect(decayNuclides.some((n) => n.id === "Cs-137")).toBe(true);
    expect(decayNuclides.some((n) => n.id === "Tc-99m")).toBe(true);
  });
  it("derives sensible time units for extremes", () => {
    const tc99m = decayNuclides.find((n) => n.id === "Tc-99m");
    expect(tc99m?.timeUnit).toBe("hours");
    const u238 = decayNuclides.find((n) => n.id === "U-238");
    expect(u238?.timeUnit).toBe("years");
  });
});
```

- [x] **Step 2: Run test to verify it fails**

Run: `npm run test -- decayNuclides` (in `landingpage/`)
Expected: FAIL — module `./decayNuclides` not found.

- [x] **Step 3: Write the committed generator**

`landingpage/scripts/generate_decay_nuclides.py` (run with the project venv `D:\Vs Code\themis\venv\Scripts\python.exe` from repo root; add repo `src/` to `sys.path`):

```python
"""Generate landingpage/src/data/decayNuclides.ts from pydecay's ICRP-107 catalog."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pydecay import Nuclide  # noqa: E402

def time_unit(days: float) -> tuple[str, float, str]:
    if days < 14:
        return "hours", 1 / 24, f"{days * 24:.4g} hours"
    if days < 365.2422 / 2:
        return "days", 1.0, f"{days:.4g} days"
    return "years", 365.2422, f"{days / 365.2422:.4g} years"

def main() -> None:
    rows = []
    for nuclide in Nuclide.load_all().values():
        days = nuclide.half_life_s / 86400.0
        if days <= 0:  # stable endpoints carry no decay curve
            continue
        unit, per_unit, display = time_unit(days)
        rows.append((nuclide.name, nuclide.element_name, days, unit, per_unit, display))
    rows.sort()
    lines = ["// GENERATED by landingpage/scripts/generate_decay_nuclides.py — do not edit.",
             'import type { DemoNuclide } from "./nuclides";', "",
             "export const decayNuclides: DemoNuclide[] = ["]
    for name, element, days, unit, per_unit, display in rows:
        lines += ["  {", f'    id: "{name}",', f'    element: "{element}",',
                  f"    halfLifeDays: {days!r},", f'    displayHalfLife: "{display}",',
                  f'    timeUnit: "{unit}",', f"    daysPerUnit: {per_unit!r},", "  },"]
    lines.append("];")
    out = ROOT / "landingpage" / "src" / "data" / "decayNuclides.ts"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {len(rows)} nuclides -> {out}")

if __name__ == "__main__":
    main()
```

(Adjust attribute names to the real `Nuclide` fields after checking `src/pydecay/nuclide.py` — `half_life_s` exists; element name field must be verified in Step 3a.)

- [x] **Step 3a: Verify Nuclide field names**

Run: `& "D:\Vs Code\themis\venv\Scripts\python.exe" -c "from pydecay import Nuclide; n=Nuclide.load('I-131'); print([a for a in dir(n) if not a.startswith('_')])"`
Expected: confirm element/half-life attribute names; fix generator accordingly.

- [x] **Step 4: Run generator + test to green**

Run: `& "D:\Vs Code\themis\venv\Scripts\python.exe" landingpage/scripts/generate_decay_nuclides.py` then `npm run test -- decayNuclides`
Expected: "wrote N nuclides" (N ≥ 1200), tests PASS.

- [x] **Step 5: Wire DecayPanel to the catalog with a filter**

`App.tsx` DecayPanel changes:

```tsx
import { decayNuclides } from "./data/decayNuclides";
// ...
const [filter, setFilter] = useState("");
const options = decayNuclides.filter((n) =>
  `${n.id} ${n.element}`.toLowerCase().includes(filter.toLowerCase()),
);
const nuclide = options.find((item) => item.id === selectedId) ?? decayNuclides[0];
```

Render a text input (`placeholder="Filter nuclides…"`, `aria-label="Filter nuclides"`) above the `<select>`, options from `options`, keeping `id="nuclide-select"` and existing testids. When the selected id is filtered out, keep showing it (append to `options`) so the select never jumps.

- [x] **Step 6: Update App tests**

In `App.test.tsx` decay tests: add one — type "cs-137" into the filter, expect `<select>` options reduced and Cs-137 still selectable; existing decay-tab test must still pass with I-131 default.

- [x] **Step 7: Gate + commit**

Run: `npm run lint` (in `landingpage/`) — prettier will reformat the generated file; accept.
Commit: `git add landingpage/scripts landingpage/src && git -c core.hooksPath=/dev/null commit -m "feat(landing): decay tab uses full ICRP-107 catalog with filter"`

### Task A2: Deploy landing page (GATED) — push-based auto-deploy

- [x] **Step 1:** Ask user for explicit go-ahead (user directive: never deploy unasked). On yes: deploy via git push to `origin/main` (user: Vercel auto-deploys on push; manual `vercel deploy` not wanted).
- [ ] **Step 2:** Verify live: open deployed URL, smoke-check 3 tabs + `/docs/changelog` shows 0.6.0.
- [ ] **Step 3:** Record URL in `.superpowers/sdd/2026-09-24-pydecay-dose-shielding/progress.md`.

### Task A3: Notebooks (4 tutorials)

**Files:** Create `notebooks/01_decay_basics.ipynb`, `02_inventory_chains.ipynb`, `03_dose_rates.ipynb`, `04_shielding_design.ipynb`; modify `mkdocs.yml` (or README pointer), `pyproject.toml` optional extra `tutorials = ["jupyter", "matplotlib"]`.

Each notebook: (a) concept in 3–5 markdown cells with cited sources, (b) runnable cells using only public API (`Nuclide.load`, `decayed_activity`, `DecayChain`, `dose_rate`, `transmit_slab`), (c) an exercise cell with hidden answer, (d) final cell printing a golden value asserted against `tests/golden/golden_values.json` equivalents.

- [x] Step 1: notebook 01 + smoke test `tests/test_notebooks.py` executing all `.ipynb` via `nbclient` (skip if extra not installed — `pytest.importorskip`).
- [x] Step 2–4: notebooks 02–04, same gate.
- [x] Step 5: gates + commit `docs(tutorials): four executable notebooks with golden asserts`.

Note (2026-09-27): `tutorials` extra also includes `nbclient` + `ipykernel`
(the execution harness needs a kernel; plan listed only jupyter/matplotlib).
README carries the notebook pointer instead of mkdocs.yml (plan allowed
either). Golden file gained 5 analytic dose/shielding entries for
notebooks 03/04 (spec: "asserted against golden_values.json equivalents").

### Task A4: Docs cookbook

**Files:** Create `docs/cookbook.md` (10 recipes: half-life → remaining activity, chain at time t, build a decay series, exposure→kerma→ambient, single-slab HVL sizing, multilayer wall, batch CSV decay table, unit conversions, plot decay curve, catch pydecay errors); modify `mkdocs.yml` nav.
Recipes = problem statement, code block, expected output (verified by running), source citation. Test: `tests/test_docs_recipes.py` extracts every ```python block from `docs/cookbook.md` and execs it (assert no exceptions + pinned outputs). Gate: `mkdocs build --strict` + pytest + commit `docs: cookbook recipes with exec-tested code`.

### Task A5: JOSS paper draft

**Files:** Create `paper/paper.md` + `paper/paper.bib` (JOSS template: summary, statement of need, features table, references — ICRP-107 Pub 107, NIST XCOM, Risoe-M-2322, ICRP-74, RadioactiveDecay cross-check). NOT submitted — draft only, user reviews. Gate: word count ≤1000 prose, all claims cite refs that exist in `paper.bib`; commit `docs(joss): paper draft`.

---

## Track B — Practitioner Utility (v0.7)

### Task B1: Buildup factors (GP / Taylor)

**Files:**
- Create: `src/pydecay/buildup.py` — `taylor_buildup(e: float, mu_over_rho: float, z: float, c: Sequence[float]) -> float`; `gp_buildup(e, a, b, c) -> float`; `buildup_factor(e_mev, material, d_mfp, *, form="taylor") -> float`; data `src/pydecay/data/buildup_gp_taylor.json.gz` (E, a, b, c per material for water/concrete/iron/lead/air at 60–100 keV…10+ MeV, from ANSI/ANS-6.4.3 (Geigy tabulations) — source table transcribed with citation `LICENSE.buildup` note).
- Modify: `src/pydecay/shielding.py` — `transmit_slab(..., buildup=True)` optional kwarg (default `False`, preserving narrow-beam goldens).
- Modify: `src/pydecay/__init__.py` (`buildup_factor` export, `__all__` → 42+), `docs/shielding.md`, CHANGELOG.
- Test: `tests/test_buildup.py` — known Geigy table rows (pin 6+ goldens), identity `buildup → 1.0 as d_mfp → 0`, monotonic increase in d_mfp, parity `transmit_slab(buildup=True) >= narrow_beam`.

- [ ] Step 1: failing goldens test (table row values transcribed with source page number).
- [ ] Step 2: data file + curation script `src/pydecay/data/_fetch_buildup.py` (transcription is manual — script validates schema/ranges, not network).
- [ ] Step 3: implement module to green; ruff/mypy/coverage.
- [ ] Step 4: docs + `__init__` + packaging test update (wheel includes `buildup_gp_taylor.json.gz`).
- [ ] Step 5: commit `feat(shielding): GP/Taylor buildup factors with ANSI/ANS goldens`.

### Task B2: Full XCOM element tables

**Files:**
- Create: `src/pydecay/data/_fetch_xcurate.py` builds `src/pydecay/data/xcom_elements.json.gz` — μ/ρ for **all elements Z=1…92** × the existing 45-point energy grid (0.01–20 MeV, ×1.1892 as in `shieldingTables`), sourced from NIST XCOM (same fetch path as `_fetch_nist.py`, license `LICENSE.nist.txt` extension note), atomic densities recorded per element for density fallback (ρ from periodic-table data where natural density exists, else 1.0 g/cm³ flagged).
- Modify: `src/pydecay/materials.py` — `element_material(symbol_or_z)` returns a material usable by `mu_from_material` / `hvl` / `transmit_slab`; `available_materials()` unchanged (7 named) + new `available_elements()`.
- Modify: landing `landingpage/scripts/` generator + `shieldingTables.ts` material picker gains an element dropdown (Fe, Pb, Cu, H₂O… common ~20 prelisted, full list searchable) — **after** the Python side ships.
- Test: `tests/test_xcom_elements.py` — lead/iron/water μ/ρ at 1 MeV vs existing 7-material table (exact match where overlapping), monotonic in E, Z sweep smoke (all 92 load), wheel budget test.

- [ ] Step 1: failing parity tests vs current `nist_mu` values.
- [ ] Step 2: fetch/curate + gzip; verify wheel ≤15 MB (`python -m build`).
- [ ] Step 3: `element_material()` + exports + docs `materials.md` section.
- [ ] Step 4: full gates + commit `feat(data): full NIST XCOM element μ/ρ tables`.

### Task B3: Extended sources (disk / cylinder / volume)

**Files:** Modify `src/pydecay/dose.py` — `dose_rate_disk(activity_bq, nuclide, radius_m, distance_m, *, quantity=...)` (analytic integration of point-source kernel over disk, closed-form via numerical quadrature with `numpy.trapezoid` on ≤200 nodes, convergence-checked), `dose_rate_cylinder(...)` (length + radius). Geometry factor = point dose × F(reduced distance) cross-checked against published point-vs-disk ratios.
Test: `tests/test_dose_extended.py` — F→1 as r≫R (tol 1e-3), F<1 at contact, golden from a published table (cite: ICRP-74 Appendix or classic JDC point-kernel tabulation), symmetry/monotonicity property tests. Exports + docs + CHANGELOG. Commit `feat(dose): disk and cylinder extended-source rates`.

### Task B4: CLI (`pydecay` entry point)

**Files:**
- Create: `src/pydecay/cli.py` (argparse — no new dependency), `tests/test_cli.py`.
- Modify: `pyproject.toml` → `[project.scripts] pydecay = "pydecay.cli:main"`.

Subcommands (concrete):

```
pydecay decay --nuclide I-131 --activity 1e6 --time 8.02 days [--format table|json|csv]
pydecay chain --isotopes Sr-90 Y-90 --t 30 years --n0 "Sr-90=1e6" [--format json]
pydecay dose --nuclide Co-60 --activity 1e6 --r 1m [--quantity kerma|ambient|exposure]
pydecay shield --material lead --energy 1.25 --thickness 1cm [--buildup] [--multilayer "2cm,concrete+10cm,lead"]
pydecay convert "8.02 days" --to s | bq2ci 3.7e10 | ...
```

Exit codes: 0 ok, 2 bad usage (argparse default), 1 `PyDecayError` (message on stderr, `--verbose` prints traceback).

- [ ] Step 1: failing tests — `main(["decay","--nuclide","I-131","--activity","1e6","--time","8.02","days","--format","json"])` captures stdout, asserts `remaining` ≈ 5e5 (structure decided in test: keys `nuclide, elapsed_s, remaining_bq`).
- [ ] Step 2: implement `cli.py` minimal decay path → green.
- [ ] Step 3: add `chain`, `dose`, `shield`, `convert` with their test vectors (reuse golden values from `tests/golden/golden_values.json` — import JSON in tests, don't retype numbers).
- [ ] Step 4: `--format csv` rows, error-path tests, `pyproject` scripts entry, `docs/cli.md` + mkdocs nav.
- [ ] Step 5: full gates + commit `feat(cli): pydecay command-line entry point`.

### Task B5: Plotting extra

**Files:** Create `src/pydecay/plotting.py` (`plot_decay(curves, *, ax=None)`, `plot_shielding(material, energies, thicknesses)`, returns matplotlib `Axes`; `pyplot` imported lazily inside functions), optional extra `plot = ["matplotlib>=3.7"]` in `pyproject.toml`, `tests/test_plotting.py` (`pytest.importorskip("matplotlib")`, `matplotlib.use("Agg")`, assert artists/labels/numeric data — never pixel compare). Docs `docs/plotting.md`. Commit `feat(plot): optional matplotlib plotting helpers`.

### Task B6: v0.7.0 release

- [ ] CHANGELOG `## [0.7.0]` (Added: buildup, full XCOM, extended sources, CLI, plotting; Changed: landing decay catalog), README feature bullets, version `0.7.0` (`src/pydecay/__init__.py`, landing `package.json`), docs masthead + landing docs changelog entry (same pattern as the 0.6.0 refresh).
- [ ] Gates: pytest ≥90% cov, ruff, mypy, mkdocs strict, `python -m build` + `twine check`, `npm run lint`.
- [ ] Push + tag `v0.7.0` + PyPI upload (token via env, **user runs or explicitly authorizes**) + landing redeploy (gated like A2).

---

## Track C — Transport-lite Platform (v0.8 → v1.0)

### Task C1: Monte Carlo transport engine core

**Files:** Create `src/pydecay/mc/` package: `__init__.py`, `geometry.py` (`Slab`, `Sphere`, `SphereShell` — analytic intersections, no CSG), `source.py` (isotropic point/disk, energy spectrum from `spectra.py`), `physics.py` (photon: photoelectric/Compton/Klein–Nishina sampling using XCOM μ/ρ breakdown — **requires B2 data split by partial cross-section**; secondary electron escape approximated as local energy deposition), `engine.py` (`run(n_histories, *, seed) -> MCResult`), `result.py` (`MCResult`: dose, transmission, uncertainty ±1σ, history count).
API: `from pydecay.mc import run; r = run(100_000, geometry=..., source=..., seed=42)`.

Tests: `tests/mc/test_engine.py` — (a) pure-attenuation limit reproduces `exp(-mu*x)` within 3σ, (b) seed reproducibility (same seed → identical result), (c) variance ∝ 1/N, (d) conservation: deposited + transmitted ≤ emitted. Performance budget: 100k histories slab problem <10 s (vectorized numpy batches; document if unmet).

- [ ] Steps: Step 1 failing seed/attenuation tests → Step 2 geometry+source → Step 3 physics+engine → Step 4 result+docs `docs/monte-carlo.md` → Step 5 gates+commit `feat(mc): photon Monte Carlo engine core`.

### Task C2: Uncertainty propagation

**Files:** Create `src/pydecay/uncertainty.py` — `propagate(fn, samples=10000, seed=None, **param_distributions)` using numpy `default_rng`; half-life/coefficient uncertainties as lognormal σ from ICRP/IAEA stated errors where available (store `half_life_rel_unc` in loader when catalog provides it). `DecayResult` gains `.p05/.p50/.p95`. Tests: known analytic case (pure decay, lognormal T½ → quantiles vs closed form), seed determinism, `samples>=100` validation. Docs + export + commit `feat(uncertainty): sampling-based uncertainty propagation`.

### Task C3: ENSDF/NNDC parser

**Files:** Create `src/pydecay/data/_fetch_ensdf.py` + `_parse_ensdf.py` (target: half-lives + γ intensities for nuclides missing/weak in ICRP-107; network fetch OFF by default like existing `_fetch_*`, fixtures under `tests/fixtures/ensdf/`), loader flag `Nuclide.load(name, source="ICRP-107"|"ENSDF")`. Golden tests vs fixture records with source citation lines. Wheel budget re-check. Commit `feat(data): ENSDF parser as secondary evaluated-data source`.

### Task C4: Neutron dose (ICRP-116)

Mirror B-track dose architecture: `src/pydecay/data/neutron_dose.json.gz` (ICRP-116 conversion coefficients, ambient + effective per particle fluence for monoenergetic grid), `dose_rate_neutron(...)` in `dose.py`, caveats in docstring (fluence-to-dose, no transport), goldens from ICRP-116 tables, docs section. Commit `feat(dose): ICRP-116 neutron ambient/effective conversion`.

### Task C5: MCNP input writer

**Files:** Create `src/pydecay/interop/mcnp.py` — `write_deck(geometry, source, materials, *, title, cards)` emitting valid MCNP6 syntax (CELL/SURFACE/DATA cards, `SDEF`, F4 tallies) for the C1 geometry subset; `tests/test_mcnp_writer.py` snapshot tests (card ordering deterministic, `MCNP` keyword assertions — do NOT require MCNP installed). Docs `docs/interop.md`. Commit `feat(interop): MCNP deck writer for common geometries`.

### Task C6: Benchmark validation suite

**Files:** Create `tests/benchmarks/` — published comparison cases (decay: IAEA/ANS decay benchmark series dose-points; shielding: NCRP-49 style point-kernel cases vs `transmit_slab`+buildup; MC: subcritical/shielding transmission published runs). Each benchmark documents source, expected value, tolerance in a `benchmarks.json`; report in CI as normal tests (skip MC benchmarks if runtime >30 s via marker). Add `docs/validation.md` table auto-generated from `benchmarks.json`. Commit `test(benchmarks): published validation cases`.

### Task C7: v1.0.0 release

Same release discipline as B6 (CHANGELOG, versions, gates, tag, PyPI authorized by user, landing docs refresh, deploy gated). Definition of done: all three identities shipped — tutorials + paper draft (A), v0.7 features (B), MC + uncertainty + validation (C), LOC ≥100k of which data/tests/docs are honestly categorized in the release notes.

---

## Self-Review

1. **Spec coverage:** three identities each have tasks (A: A1–A5; B: B1–B6; C: C1–C7); LOC target addressed by sequencing table; distribution gap (deploy/announce) = A2/A5/B6; "decay dropdown only 4 nuclides" = A1. Vercel gate, token security, wheel budget, coverage floor all in Global Constraints. No spec item lacks a task.
2. **Placeholder scan:** no TBD/TODO; A3–A5/C tasks are task-granular by design (scope check: per-track step-level plans written at track start — A1, B1, B4 carry full step detail now as templates). Field-name verification is an explicit step (A1 Step 3a), not a placeholder.
3. **Type consistency:** `DemoNuclide` reused for `decayNuclides` (A1) matches `nuclides.ts:1-8`; CLI output keys fixed in Step 1; MC API `run(...) -> MCResult` consistent C1→C6; `buildup=True` kwarg on `transmit_slab` referenced identically in B1 and docs.

## Execution Handoff

Plan saved: `docs/superpowers/plans/2026-09-27-pydecay-three-track-roadmap.md`.

Execution options (**inline only** — your no-subagents directive):
- **Inline execution** via `superpowers:executing-plans`, starting with Track A quick wins (A1 → A3 → …), checkpointing after each task with gates + your review.

Pick a starting point: **A1** (decay catalog, unblocks the dropdown complaint), **A2** (deploy — needs your go-ahead), or jump to **B1/B4** (buildup/CLI).
