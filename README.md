# pydecay

[![PyPI version](https://img.shields.io/pypi/v/pydecay)](https://pypi.org/project/pydecay/)
[![Python 3.10+](https://img.shields.io/pypi/pyversions/pydecay)](https://pypi.org/project/pydecay/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Radioactive decay mathematics for Python: analytical single-isotope decay,
Bateman decay chains with a matrix-exponential stability guard, branching
topologies, multi-nuclide inventories with automatic progeny ingrowth, ICRP-107
nuclide data (1252+ isotopes), spectra access, and activity unit conversions.

Author: **Daniel Deshmukh** · [github.com/DanielDeshmukh/pydecay](https://github.com/DanielDeshmukh/pydecay)

## Install

```bash
pip install pydecay
```

Requires Python >= 3.10. Runtime dependencies: `numpy`, `scipy`, `pint`.

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

## What is implemented

| Area | Detail | Reference |
|---|---|---|
| Single isotope | `N(t)=N0*exp(-lambda*t)`, `lambda=ln2/T_half`, `A=lambda*N` | Krane ch. 6; BIPM/NIST for units |
| Linear chains | Bateman (1910) closed form when well-separated | Bateman 1910 |
| Stability guard | `scipy.linalg.expm` on the generator matrix for degenerate lambda, branching, or nonzero daughter ICs | spec fix option 2; Cetnar 2006 (deferred optimization) |
| Branching | star topologies with fractions <= 1 (remainder = untracked sink) | general linear ODE system |
| Inventory | multi-nuclide seeds with ICRP-107 progeny closure, immutable `decay`, cumulative decays, linear/log time series | general linear ODE system |
| Data | 1252+ ICRP-107 radionuclides + stable endpoints (default catalog) | ICRP Publication 107 |
| Spectra | `emissions` / `beta_spectrum` (RAD/BET), lazy-loaded | ICRP-107 RAD/BET files |
| Units | seconds / atoms / Bq internally; Bq<->Ci and atoms<->grams at the boundary | NIST SP 811; BIPM SI (N_A exact) |

## Verification

- Worked examples (1000 Bq I-131 -> 500 Bq / 31.25 Bq) asserted against the
  bundled ICRP-107 half-lives in `tests/test_known_values.py`.
- Bateman vs `expm` agreement to 1e-10; degenerate-lambda regression
  (0.6931 / 0.6932) must stay finite (`tests/test_solver.py`).
- Differential cross-check against `radioactivedecay` (ICRP-107):
  report drift, fail past 1e-3 relative (`tests/test_crosscheck.py`).
- IAEA 47-nuclide fixture retained as a differential oracle
  (`tests/test_iaea_differential.py`, `REL_TOL_DATA = 1.5e-2`).

## Documentation

Full guide in [`docs/`](docs/index.md) (MkDocs: `mkdocs serve`).
Architecture + solver dispatch diagrams: [`docs/architecture.md`](docs/architecture.md).
Formula derivations with citations: [`docs/math.md`](docs/math.md).

## Development

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Quality gates: `pytest`,
`ruff check src tests`, `mypy src`, coverage >= 90%, `mkdocs build --strict`.

## License

MIT — see [`LICENSE`](LICENSE). Bundled ICRP-107 data is under
`LICENSE.ICRP-07` (educational / research / not-for-profit terms).
