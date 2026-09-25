# pydecay v0.6 — Dose & Shielding — Design Spec

**Date:** 2026-09-24
**Status:** Draft (for review)
**Sub-project:** Roadmap v0.6 — dose, exposure, and shielding
**Builds on:** v1 design (§4 units, §5 inventory), ICRP-107 pipeline (spectra/RAD emissions)

---

## 1. Goal

Add **dose and shielding** capabilities so pydecay answers the next questions after "how much activity is left?":

1. How much **dose rate** does this inventory produce at a distance?
2. How does **half-value layers / concrete thickness** reduce it?
3. How do we go from **activity → exposure/dose** using trusted published coefficients?

Out of scope for v0.6 (later versions):

- Full Monte Carlo transport (v0.9)
- Neutron transport / buildup beyond photon point-kernel (v0.7–0.8)
- Activation & depletion (v0.8)
- Medical isotope production planning (v1.0)
- Geometry beyond point / simple slab / spherical shells (no mesh/MCNP)

Success criterion: every dose/shielding path is validated against published reference tables (ICRP/NIST/authoritative handbook values) with documented tolerances; 90%+ coverage maintained.

---

## 2. Decisions (brainstorm)

| Topic | Decision |
|-------|----------|
| Primary audience | Health physicists, nuclear engineering students, amateur/pilot rad projects |
| Dose model scope | **Photons (γ/X) first**, then beta/charged-particle kerma shortcuts |
| Coefficient source | **Bundled published tables** (ICRP-115/119 external, NIST XCOM attenuation) — no network at runtime |
| Shield materials | Pb, Fe/steel, concrete (standard + heavy), water, air, Al, polyethylene — extensible registry |
| Shield geometry | **Point kernel** (slab HVL/TVL) + **narrow-beam exponential** first; buildup factors added in v0.7 |
| Units policy | Follows existing rule: pint at API edge, canonical SI floats internally (Gy, Sv, m⁻¹, seconds) |
| Data licensing | ICRP tables: cite publication, honor license (likely educational/non-profit posture like ICRP-07). NIST: public domain |
| API shape | Thin functions in `dose.py` + `shielding.py`; domain objects optional later |
| Runtime deps | **No new runtime deps** — reuse numpy/scipy/pint |
| Accuracy non-goals | Not a regulatory tool; document assumptions (point source, air Kerma free-in-air, geometry factors) |

---

## 3. Physics & formulas (ground truth)

### 3.1 Exposure / dose rate from activity

**Classic exposure-rate constant** (handbook values, e.g. ICRP-107/Hickman):

\[
\dot{X} = \Gamma \cdot A
\]

- \(\Gamma\): specific gamma-ray constant (R·cm²·mCi⁻¹·h⁻¹ or equivalent SI)
- \(A\): activity (Bq)
- Result: exposure rate at 1 cm (or scaled by \(1/r^2\))

**Air-kerma / ambient dose equivalent rate** (preferred modern path):

\[
\dot{K}_{air} = \sum_i A_i \cdot \dot{k}_{air,i}(r) \quad\text{or}\quad
\dot{H}^*(10) = \sum_i A_i \cdot \dot{h}^*_{i}(r)
\]

For a **monoenergetic photon point source** in air (narrow-beam / free-in-air):

\[
\dot{K}_{air}(r) = \frac{A \cdot E_\gamma \cdot \mu_{en}/\rho \cdot e^{-\mu r}}{4\pi r^2} \cdot \Phi_{\text{normalize}}
\]

Practical v0.6 path: ship **pre-tabulated dose-rate constants** (Gy·h⁻¹ per Bq at 1 m, or mGy·h⁻¹·MBq⁻¹·m²) for a curated set of common nuclides, plus **energy-dependent kernel** built from bundled μ/ρ tables.

### 3.2 Shielding (narrow-beam)

\[
I = I_0 \, e^{-\mu x}
\]

- \(\mu\): linear attenuation coefficient (m⁻¹), material- and energy-dependent
- **HVL** = ln2 / μ, **TVL** = ln10 / μ
- Multi-layer: product of exponentials (or sum of μᵢxᵢ for pure attenuation)

### 3.3 Buildup (deferred to v0.7, stub API now)

\[
I = B(\mu E, E) \cdot I_0 \, e^{-\mu x}
\]

Taylor / geometric-progression buildup factors — v0.6 records the API shape but raises `NotImplementedError` or ships simple Berger form for a few materials if data allows.

### 3.4 Beta / charged particle (simple shortcuts)

For **beta dose to skin / shallow** from pure beta emitters: use published max-E vs range approximations (Klei & Hoppes or ICRP) — v0.6 ships basic CSDA range + restricted energy-loss estimate; full track structure out of scope.

---

## 4. Architecture & module layout

Follows v1 boundary rules: **pure SI core**, **pint at edge**, data loaders under `data/`.

```
src/pydecay/
├── dose.py                 # NEW — activity → exposure/air-kerma/dose-equivalent rate (pure SI)
├── shielding.py            # NEW — μ, HVL/TVL, multi-layer attenuation (pure SI)
├── materials.py            # NEW — material registry (Pb, concrete, water…) + μ(E) interpolation
├── _dose_data.py           # NEW — loaders for bundled coefficient tables (build-time-friendly)
├── data/
│   ├── dose_coefficients.json      # NEW — per-nuclide Γ / Ṙ tables (curated)
│   ├── nist_mu.json.gz             # NEW — NIST XCOM μ/ρ vs E by material (bundled)
│   ├── nist_mu.csv                 # NEW — human-readable mirror of same data (optional)
│   └── LICENSE.nist.txt            # NEW — NIST public-domain notice
└── (existing api.py gains dose convenience wrappers)
```

**Public re-exports** added to `__init__.py` (pint-aware convenience):

```python
from pydecay.dose import dose_rate, exposure_rate, air_kerma_rate
from pydecay.shielding import hvl, tvl, transmit, multilayer_transmit
from pydecay.materials import material, Material
```

### 4.1 Data flow

```
ICRP-107 RAD emissions (existing) ─┐
                                   ├─► dose.py  ─► Gy/h, Sv/h at r
bundled dose_coefficients.json ────┘

NIST XCOM μ/ρ tables ─► materials.py ─► shielding.py ─► transmitted intensity / HVL
```

### 4.2 Layering rules (unchanged project rule)

- `dose.py`, `shielding.py`, `materials.py` core math: **floats/ndarrays only** (Gy, m⁻¹, seconds) — no pint import.
- Public functions in `api.py` / `__init__.py`: accept pint Quantities & strings via `units.to_float`, return mirrored types.
- `_dose_data.py` + `data/_fetch_*.py` excluded from wheel (hatch exclude list, like ICRP fetchers).

---

## 5. Data sources (research before lock-in)

| Data | Source | License | Ship how |
|------|--------|---------|----------|
| Per-nuclide Γ, Ṙ (common 40–80 isotopes) | ICRP-107/ICRP-115 compendiums, Hickman, Eckerman tables; cross-check vs `radioactivedecay` if it exposes dose data | Cite publication; match ICRP educational posture | `dose_coefficients.json` |
| μ/ρ vs E (0.01–20 MeV) for Pb, Fe, H₂O, concrete, Al, air, poly | **NIST XCOM / NIST TN-1269** (Hubbell & Seltzer) | Public domain (US Gov) | `nist_mu.json.gz` |
| Conversion constants (R↔Gy air, Sv/H* scaling) | ICRP-103/119 conversion factors, NIST | Public / cite | constants in `dose.py` |
| Beta range / max-E relations | ICRP, NIST ESTAR | Cite | `dose.py` helpers |

**Rules (mirroring ICRP pipeline):**

- Values are **checksum-pinned** in build scripts.
- No silent merge of sources — one primary per quantity, differential tests where a second exists.
- Runtime never hits the network.

---

## 6. Public API sketch

### 6.1 Dose

```python
# activity → dose rate at distance (point source, air)
dose_rate(A, nuclide_or_table, r="1 m", *, particle="gamma", medium="air") -> Gy/h
exposure_rate(A, nuclide, r="1 cm") -> R/h            # legacy / handbook compatibility
air_kerma_rate(A, E_MeV, r="1 m") -> Gy/h             # monoenergetic primitive

# inventory-level (composes with existing Inventory)
inventory.dose_rate(r="1 m", *, particle="gamma", geometry="point") -> Gy/h
```

### 6.2 Shielding

```python
hvl(mu=None, *, material=None, energy_MeV=None) -> m      # or from tabulated μ
tvl(mu=None, *, material=None, energy_MeV=None) -> m
transmit(I0, mu, x) -> I                                  # I0 * exp(-mu*x)
transmit_slab(I0, material, thickness, energy_MeV) -> I
multilayer_transmit(I0, layers, energy_MeV) -> I          # [(material, thickness), …]
mu(material, energy_MeV) -> m⁻¹                           # interpolate bundled NIST data
half_value_thickness(material, energy_MeV) -> m
```

### 6.3 Errors

New subclasses of `PyDecayError`:

```python
class DoseDataError(PyDecayError): ...      # missing coefficient for nuclide
class MaterialError(PyDecayError): ...      # unknown material / E out of table range
```

---

## 7. Test plan

| Layer | Tests |
|-------|-------|
| **Known values** | Γ for Co-60, Cs-137, I-131, Tc-99m, Pu-239 etc. vs handbook tables (tolerance documented) |
| **Analytic identities** | transmit(I0, μ, 0)=I0; HVL→exactly half; TVL→exactly 0.1×; multi-layer order-independence for pure attenuation |
| **μ interpolation** | round-trip table E→μ→E; monotonic in E for photoelectric-dominated low E; endpoints clamped or raise |
| **Inventory compose** | sum of single-nuclide dose rates == inventory.dose_rate (linearity) |
| **Units parity** | pint Quantity vs plain float parity for all public dose/shield functions |
| **Cross-check** | vs `radioactivedecay` if it exposes dose/Γ; vs NIST published μ for Pb/H₂O at fixed E |
| **Coverage** | maintain ≥ 90% (existing `fail_under = 90`) |
| **Golden data** | small JSON of expected HVL/TVL for Pb @ 1.25 MeV (Co-60 avg) etc. |

---

## 8. Docs & landing page

- `docs/dose.md` — formulas, coefficient provenance, worked example (Co-60 at 1 m)
- `docs/shielding.md` — HVL/TVL tables, multi-layer example, limitations disclaimer
- User-guide section + API reference entries
- Landing-page playground card (optional v0.6): "Shield thickness" calculator mirroring `hvl`
- CHANGELOG `## [0.6.0]` entry
- README feature bullet

---

## 9. Milestones & rough LOC

| Task | Est. LOC |
|------|----------:|
| NIST μ/ρ fetch + parse + bundle (`_fetch_nist.py`, `materials.py`, data file) | 800–1,200 + data |
| `dose_coefficients.json` curation + loader | 300–500 + data |
| `dose.py` core (exposure, air-kerma, nuclide tables, inventory hook) | 500–800 |
| `shielding.py` (μ, HVL/TVL, transmit, multi-layer) | 300–500 |
| Exceptions + `__init__` / `api.py` re-exports | 50–100 |
| Tests (known values, identities, parity, cross-check) | 1,000–1,500 |
| Docs (`dose.md`, `shielding.md`, api/user-guide updates) | 400–700 |
| **v0.6 total** | **~3.5–5.5k** (+ bundled data) |

---

## 10. Open questions (for review)

1. **Coefficient granularity:** ship full ICRP-115 nuclide set (~100+) or start with ~40 common medical/industrial nuclides?
2. **Buildup:** keep pure narrow-beam in v0.6 and ship buildup in v0.7, or try to include Taylor B for water+Pb now?
3. **Geometry factors:** point source only in v0.6, or add simple disk/inventory extended-source corrections?
4. **Sv vs Gy:** default return `Gy/h` (air kerma) with optional `quantity="H*(10)"` for ambient dose equivalent? Or separate functions?
5. **License file** for NIST data: `LICENSE.nist.txt` verbatim from XCOM page?

---

## 11. Explicit non-goals (v0.6)

- Neutron dose / ICRP-116 neutron factors → v0.7+
- Monte Carlo random histories → v0.9
- Full buildup factor formalism (GP/Taylor tables) → v0.7
- Mesh / lattice geometry, MCNP/SCALE import → post-v1.0
- Regulatory compliance claims — document as educational/research tool
