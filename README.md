# pydecay

[![PyPI version](https://img.shields.io/pypi/v/pydecay?cacheBust=0.5.1)](https://pypi.org/project/pydecay/)
[![Python 3.10+](https://img.shields.io/pypi/pyversions/pydecay)](https://pypi.org/project/pydecay/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Tests](https://img.shields.io/badge/coverage-%3E%3E90%25-brightgreen)](tests/)

**Radioactive decay mathematics for Python** — analytical single-isotope decay,
Bateman chains with a matrix-exponential stability guard, branching topologies,
multi-nuclide inventories with automatic progeny ingrowth, ICRP-107 nuclide
data (1252 radionuclides + 246 stable endpoints = 1498 records), radiation
spectra, and activity unit conversions.

Author: **Daniel Deshmukh** · [github.com/DanielDeshmukh/pydecay](https://github.com/DanielDeshmukh/pydecay) · [Demo](https://pydecay-model-remains.vercel.app)

---

## Table of contents

- [Install](#install)
- [Quickstart](#quickstart)
- [Feature distribution](#feature-distribution)
  - [1. Single-isotope decay](#1-single-isotope-decay)
  - [2. Nuclide lookup (ICRP-107)](#2-nuclide-lookup-icrp-107)
  - [3. Multi-nuclide inventory](#3-multi-nuclide-inventory)
  - [4. Decay chains](#4-decay-chains)
  - [5. Branching topologies](#5-branching-topologies)
  - [6. Radiation spectra](#6-radiation-spectra)
  - [7. Unit conversions](#7-unit-conversions)
  - [8. Instantaneous rates & ODE residual](#8-instantaneous-rates--ode-residual)
  - [9. Error handling](#9-error-handling)
- [Verification](#verification)
- [Documentation](#documentation)
- [Development](#development)
- [License](#license)

---

## Install

```bash
pip install pydecay
```

Requires **Python ≥ 3.10**. Runtime dependencies: `numpy`, `scipy`, `pint`.

```python
import pydecay
print(pydecay.__version__)  # "0.5.1"
```

---

## Quickstart

```python
from pydecay import Nuclide, DecayChain, Inventory, decayed_activity, remaining_fraction

# Single isotope: 1000 Bq of I-131 after one half-life -> 500 Bq
i131 = Nuclide.load("I-131")
a = decayed_activity(A0=1000.0, half_life=i131.half_life, time=i131.half_life)

# Dimensionless fraction after 5 half-lives -> 0.03125
f = remaining_fraction(half_life=i131.half_life, time=5 * i131.half_life)

# Linear chain (parent -> daughter -> stable), plain floats or pint
chain = DecayChain([0.693, 0.0], names=["parent", "stable"])
print(chain.at(t="1 days", n0={"parent": 1e6, "stable": 0.0}))

# Branching: 60% / 30% to two daughters, remainder untracked
b = DecayChain.branching(
    parent="P",
    branches={"D1": 0.6, "D2": 0.3},
    lambdas={"P": 0.7, "D1": 1e-5, "D2": 2e-5},
)

# Multi-nuclide inventory: seeds only; daughters (Tc-99m, Tc-99, ...) auto-close
inv = Inventory({"Mo-99": 1e6}, units="Bq")
print(inv.decay("8.02 days").activities())
```

---

## Feature distribution

| Area | Detail | Reference |
|---|---|---|
| Single isotope | `N(t)=N0·e^(−λt)`, `λ=ln2/T½`, `A=λN` | Krane ch. 6; BIPM/NIST |
| Linear chains | Bateman (1910) closed form when well-separated | Bateman 1910 |
| Stability guard | `scipy.linalg.expm` on the generator matrix for degenerate λ, branching, or nonzero daughter ICs | Cetnar 2006 |
| Branching | Star topologies with fractions ≤ 1 (remainder = untracked sink) | General linear ODE |
| Inventory | Multi-nuclide seeds with ICRP-107 progeny closure; immutable `decay`; cumulative decays; linear/log time series | General linear ODE |
| Data | 1252 radionuclides + 246 stable endpoints = **1498 records** | ICRP Publication 107 |
| Spectra | `emissions` / `beta_spectrum` (RAD/BET), lazy-loaded | ICRP-107 RAD/BET |
| Units | seconds / atoms / Bq internally; Bq↔Ci and atoms↔grams at the boundary | NIST SP 811; BIPM SI (N_A exact) |
| Rates / ODE | `dn_dt`, `da_dt`, `decay_ode_residual`; `Inventory.instantaneous_rates` via G @ N | dN/dt = −λN |

### 1. Single-isotope decay

Three “how much is left?” functions — activity, atoms, or a pure fraction:

```python
from pydecay import decayed_activity, decayed_atoms, remaining_fraction

# 1000 Bq of I-131 after one half-life -> 500 Bq
decayed_activity(A0=1000.0, half_life="8.02 days", time="8.02 days")   # 500.0

# 1e6 atoms after 24 hours
decayed_atoms(N0=1_000_000, half_life="8.02 days", time="24 hours")

# Dimensionless fraction after 5 half-lives -> 1/32 = 0.03125
remaining_fraction(half_life="8.02 days", time=5 * 8.02 * 86400)       # 0.03125
```

- Inputs accept plain numbers (SI seconds), human strings (`"8.02 days"`), or pint Quantities.
- Output **kind mirrors input**: float in → float out; Quantity in → Quantity out.
- `time` must be finite and `≥ 0` (`InvalidTimeError` otherwise).

### 2. Nuclide lookup (ICRP-107)

```python
from pydecay import Nuclide

i131 = Nuclide.load("I-131")
print(i131.half_life)       # pint Quantity, e.g. 8.02 days (stored in seconds)
print(i131.half_life_s)     # 692988.48
print(i131.lambda_)         # decay constant (1/s)
print(i131.atomic_mass_u)   # mass in u
print(i131.progeny)         # ("Xe-131m", "Xe-131")
print(i131.branching)       # matching branch fractions
print(i131.source)          # "ICRP-107"

# Full catalog: 1252 ICRP-107 radionuclides + 246 stable endpoints = 1498 records
all_nuclides = Nuclide.load_all()
```

Stable endpoints report `lambda_ = 0.0` and `is_stable = True`. Unknown names raise `NuclideNotFoundError`.

### 3. Multi-nuclide inventory

List **seeds** only — pydecay walks the ICRP-107 progeny graph and builds one
joint decay system (daughters included, down to stable):

```python
from pydecay import Inventory

inv = Inventory({"Mo-99": 1e6}, units="Bq")   # pulls in Tc-99m, Tc-99, ...
print(inv.names)          # full closure, graph order
print(inv.n_species)

after = inv.decay("8.02 days")                # NEW inventory (immutable)
print(after.activities())                     # dict species -> Bq
print(after.numbers())                        # atom counts
print(after.masses())                         # grams
print(inv.total_activity())                   # sum of activities (Bq float)

# Cumulative decays on [0, t]
print(inv.cumulative_decays("1 day"))

# Time series for plotting (linear or log)
t_seconds, series = inv.decay_time_series("8 days", npoints=101)
t_log, series_log = inv.decay_time_series(
    "1e6 seconds", npoints=200, time_scale="log", t_start=1.0
)
```

Constructor units: `"Bq"` (default), `"Ci"`, `"atoms"`, `"g"`.
Kind (plain vs pint) is mirrored by all accessors and preserved across `decay`.

### 4. Decay chains

```python
from pydecay import DecayChain

# From raw decay constants (1/s), parent first
chain = DecayChain([0.693, 0.0], names=["parent", "stable"])
print(chain.at(t="1 days", n0={"parent": 1e6, "stable": 0.0}))
print(chain.activity(t="1 days", n0={"parent": 1e6, "stable": 0.0}))

# From real nuclide names (bundled ICRP-107 half-lives)
chain = DecayChain.from_isotopes(["Sr-90", "Y-90"])
print(chain.at(t="1 day", n0={"Sr-90": 1e6, "Y-90": 0.0}))
```

Solver dispatch is internal: Bateman closed form when well-separated, falls
back to `scipy.linalg.expm` for degenerate λ or nonzero daughter ICs.

### 5. Branching topologies

```python
from pydecay import DecayChain

b = DecayChain.branching(
    parent="P",
    branches={"D1": 0.6, "D2": 0.3},   # fractions; sum <= 1
    lambdas={"P": 0.7, "D1": 1e-5, "D2": 2e-5},
)
print(b.at(t="1 day"))        # atoms of P, D1, D2
print(b.activity(t="1 day"))  # Bq of P, D1, D2
```

Fractions must sum to **at most 1.0**; the remainder is an **untracked sink**.

### 6. Radiation spectra

```python
from pydecay import emissions, beta_spectrum

# RAD emission rows (lazy-loaded)
rows = emissions("Ac-223")
# each row: energy (MeV), probability, code, ...

# BET spectrum
energies, amplitudes = beta_spectrum("Sr-90")
# energies in MeV; amplitudes = relative intensity
```

Both functions lazy-load on first call — they do not slow down `import pydecay`.

### 7. Unit conversions

Top-level helpers (same names as `pydecay.units` / `pydecay.decay`):

```python
from pydecay import (
    to_seconds,
    bq_to_ci,
    ci_to_bq,
    atoms_to_grams,
    grams_to_atoms,
    decay_constant,
    mean_lifetime_s,
)

# Time parsing: str | Quantity | number -> seconds
to_seconds("8.02 days")            # 692992.0
to_seconds(3600)                   # 3600.0

# Activity: Bq <-> Ci   (exact factor 1 Ci = 3.7e10 Bq)
bq_to_ci(3.7e10)                   # 1.0
ci_to_bq(1.0)                      # 3.7e10
bq_to_ci(1000.0)                   # 2.7027...e-8

# Mass <-> atoms   (N_A = 6.02214076e23 /mol, exact)
atoms_to_grams(6.02214076e23, 1.0) # ~1.0 g of hydrogen-1-like mass
grams_to_atoms(1.0, 238.0508)      # atoms in 1 g of U-238

# Decay kernels
decay_constant(8.02 * 86400)       # λ = ln2 / T½  (1/s)
mean_lifetime_s(decay_constant(8.02 * 86400))  # τ = 1 / λ  (s)
```

| Conversion | Formula | Exact factor |
|---|---|---|
| Bq → Ci | `bq / 3.7e10` | 1 Ci = 3.7 × 10¹⁰ Bq (exact) |
| Ci → Bq | `ci * 3.7e10` | same |
| atoms → g | `n * m_u / N_A` | N_A = 6.02214076 × 10²³ mol⁻¹ (exact) |
| g → atoms | `m * N_A / m_u` | same |
| time → s | unit table | year = 31557600 s (365.25 d) |
| λ | `ln(2) / T½` | — |
| τ | `1 / λ` | mean lifetime |

Internally pydecay works in **seconds, atoms, and becquerels**; these helpers
are the boundary converters. Pint Quantities are accepted wherever a time or
amount is expected — output kind mirrors input.

### 8. Instantaneous rates & ODE residual

```python
from pydecay import dn_dt, da_dt, decay_ode_residual, Inventory

# dN/dt = -λN  (atoms/s)
dn_dt(1e6, "8.02 days")

# dA/dt = -λ A(t)  (Bq/s)
da_dt(1000.0, "8.02 days", 0.0)

# Residual dN/dt + λN — 0 on an exact analytic trajectory
decay_ode_residual(1e6, 8.02 * 86400)  # 0.0

# Multi-nuclide: joint generator rates for the full closure
inv = Inventory({"Mo-99": 1e6}, units="Bq")
inv.instantaneous_rates()  # dict species -> atoms/s
```

### 9. Error handling

All package-raised errors inherit from `PyDecayError`:

| Exception | When |
|---|---|
| `NuclideNotFoundError` | Typo in nuclide name: `Nuclide.load("Xx-999")` |
| `InvalidTimeError` | Negative or infinite time; log-series bounds ≤ 0 |
| `InvalidHalfLifeError` | Half-life ≤ 0 or NaN in free decay helpers |
| `ChainDefinitionError` | Bad chain, empty/duplicate seeds, progeny cycle |
| `DataFormatError` | Broken data record, or spectra on a stable nuclide |
| `UnitError` | Bad unit string, or string on `N0` / `A0` / Inventory amount |
| `PyDecayError` | Base class — catch this to catch **everything** above |

```python
from pydecay import Nuclide, NuclideNotFoundError, PyDecayError

try:
    n = Nuclide.load("Xx-999")
except NuclideNotFoundError:
    print("No such nuclide — check the spelling (e.g. I-131, Co-60).")

try:
    ...
except PyDecayError as e:
    print("pydecay said:", e)
```

---

## Verification

- Worked examples (1000 Bq I-131 → 500 Bq / 31.25 Bq) asserted against the
  bundled ICRP-107 half-lives in `tests/test_known_values.py`.
- Bateman vs `expm` agreement to 1e-10; degenerate-lambda regression
  (0.6931 / 0.6932) must stay finite (`tests/test_solver.py`).
- Differential cross-check against `radioactivedecay` (ICRP-107): report
  drift, fail past 1e-3 relative (`tests/test_crosscheck.py`).
- IAEA 47-nuclide fixture retained as a differential oracle
  (`tests/test_iaea_differential.py`, `REL_TOL_DATA = 1.5e-2`).
- Hypothesis property invariants for decay laws, chains, and `Inventory`.
- CI coverage floor `--cov-fail-under=90`.

---

## Documentation

| Page | Contents |
|---|---|
| [`docs/index.md`](docs/index.md) | Full guide (MkDocs: `mkdocs serve`) |
| [`docs/user-guide.md`](docs/user-guide.md) | Plain-language tour of every public function |
| [`docs/api.md`](docs/api.md) | Complete API reference with signatures |
| [`docs/architecture.md`](docs/architecture.md) | Solver dispatch diagrams |
| [`docs/math.md`](docs/math.md) | Formula derivations with citations |
| [`docs/units.md`](docs/units.md) | Bq ↔ Ci, atoms ↔ grams, time parsing |
| [`docs/data-sources.md`](docs/data-sources.md) | ICRP-107 provenance |
| [`CHANGELOG.md`](CHANGELOG.md) | Keep a Changelog history |

**One-line summary:** `decayed_activity` / `decayed_atoms` / `remaining_fraction`
answer “how much is left?” · `Nuclide.load` looks up real half-lives (1252
ICRP-107 radionuclides + 246 stable endpoints = 1498 records) · `Inventory`
tracks a seed mix and every daughter that grows in · `DecayChain` follows
parents and daughters through time · `emissions` / `beta_spectrum` give
radiation spectra · unit helpers convert Bq↔Ci, atoms↔grams, and parse times
to seconds.

---

## Development

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

Quality gates (CI):

```bash
pytest --cov-fail-under=90
ruff check src tests
mypy src
mkdocs build --strict
```

Frontend demo (`landingpage/`):

```bash
npm ci
npm run lint   # prettier + typecheck + vitest + build
```

---

## License

MIT — see [`LICENSE`](LICENSE).
Bundled ICRP-107 data is under
[`src/pydecay/data/LICENSE.ICRP-07`](src/pydecay/data/LICENSE.ICRP-07)
(educational / research / not-for-profit terms).
