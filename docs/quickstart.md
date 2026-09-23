# Quickstart

## Single isotope

Analytical closed form for one nuclide: `N(t) = N0 * exp(-lambda * t)` with
`lambda = ln2 / T_half`. Inputs may be plain SI floats or pint Quantities /
unit strings.

```python
from pydecay import Nuclide, decayed_activity, remaining_fraction

# 1000 Bq of I-131 after one half-life -> 500 Bq
i131 = Nuclide.load("I-131")
a = decayed_activity(A0=1000.0, half_life=i131.half_life, time=i131.half_life)
print(a)  # 500.0

# Dimensionless fraction after 5 half-lives -> 0.03125
f = remaining_fraction(half_life=i131.half_life, time=5 * i131.half_life)
print(f)  # 0.03125

# Unit strings are accepted on t / half_life
>>> from pydecay import remaining_fraction
>>> remaining_fraction(half_life="8.02 days", time="8.02 days")
0.5
```

`remaining_fraction` is dimensionless and always returns a plain float.
`decayed_atoms` mirrors the kind of `N0`; `decayed_activity` mirrors `A0`.

All times must be `>= 0`; negative time raises `InvalidTimeError`.
Back-calculation is not supported in v2.

## Linear chain

```python
from pydecay import DecayChain

# Explicit lambdas (1/s), parent first; stable daughter has lambda = 0
chain = DecayChain([0.693, 0.0], names=["parent", "stable"])
print(chain.at(t="1 days", n0={"parent": 1e6, "stable": 0.0}))

# Or build from bundled ICRP-107 names, ordered parent -> daughter
chain = DecayChain.from_isotopes(["I-131", "Xe-131"])  # if both are bundled
```

Default initial condition when `n0` is omitted: parent `N0 = 1.0`, all others
0. Solver dispatch (Bateman closed form vs `scipy.linalg.expm`) is automatic;
see [Architecture](architecture.md).

## Branching

Star topology: one parent feeds terminal daughters by fraction. Fractions
sum to at most 1; the remainder is an untracked sink.

```python
from pydecay import DecayChain

b = DecayChain.branching(
    parent="P",
    branches={"D1": 0.6, "D2": 0.3},
    lambdas={"P": 0.7, "D1": 1e-5, "D2": 2e-5},
)
print(b.at(t="1 day"))
print(b.activity(t="1 day"))  # dict species -> Bq
```

## pint in / pint out

```python
import pint

ureg = pint.UnitRegistry()
N0 = 1e6 * ureg.atom
n = decayed_atoms(N0=N0, half_life="8.02 days", time="24 hours")
# n is a pint Quantity in atoms (mirrors N0)
```

Strings on `N0` / `A0` / `n0` raise `UnitError`; use numbers or Quantities
for those arguments. See [Units](units.md).

## Runnable example

A complete script lives at `examples/quickstart.py`. Run it with:

```bash
python examples/quickstart.py
```
