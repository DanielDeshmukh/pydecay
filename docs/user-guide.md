# User guide

A plain-language tour of **every public function** pydecay gives you.
If you have never done nuclear math before, start here.

---

## 0. Install (30 seconds)

```bash
pip install pydecay
```

You need Python 3.10 or newer. That's it — NumPy, SciPy, and Pint come with it.

```python
import pydecay
print(pydecay.__version__)  # "0.5.1"
```

---

## 1. The three "how much is left?" functions

These answer the most common question: **after some time, what remains?**

### `decayed_activity(A0, half_life, time)`

**Use case:** "I started with 1000 becquerels of I-131. How active is it after 8 days?"

```python
from pydecay import decayed_activity

# Half-life of I-131 is about 8.02 days
# After exactly one half-life, activity halves: 1000 -> 500
remaining = decayed_activity(A0=1000.0, half_life="8.02 days", time="8.02 days")
print(remaining)  # 500.0  (units: Bq)
```

| Argument | What you give it | Example |
|---|---|---|
| `A0` | Starting activity (Bq if plain number) | `1000.0` |
| `half_life` | How long until half decays | `"8.02 days"` or a number in seconds |
| `time` | How much time has passed | `"24 hours"` |

**Rule of thumb:** after 1 half-life → 50%, after 2 → 25%, after 5 → 3.125%.

---

### `decayed_atoms(N0, half_life, time)`

**Use case:** "I have 1 million atoms. How many are left after a day?"

```python
from pydecay import decayed_atoms

left = decayed_atoms(N0=1_000_000, half_life="8.02 days", time="24 hours")
print(left)  # ~917,000 atoms (approximate mental check)
```

Same idea as `decayed_activity`, but you track **atoms** instead of activity.

---

### `remaining_fraction(half_life, time)`

**Use case:** "What *percent* of anything with this half-life is left?"
No starting amount needed — it's a pure ratio.

```python
from pydecay import remaining_fraction

# After 5 half-lives, 1/32 = 3.125% remains
frac = remaining_fraction(half_life="8.02 days", time=5 * 8.02 * 86400)
print(frac)  # 0.03125  (always a plain float, 0–1)
```

Multiply any starting number by this fraction to get what's left:

```python
start = 1000.0
print(start * remaining_fraction(half_life="8.02 days", time="8.02 days"))  # 500.0
```

---

## 2. Look up a nuclide: `Nuclide`

**Use case:** "What is the half-life of I-131? Where did this number come from?"

```python
from pydecay import Nuclide

i131 = Nuclide.load("I-131")

print(i131.half_life)       # pint Quantity, e.g. "8.02 days" in seconds
print(i131.half_life_s)     # plain seconds: 692988.48
print(i131.lambda_)         # decay constant (1/s)
print(i131.atomic_mass_u)   # mass in atomic mass units
print(i131.source)          # provenance, e.g. "ICRP-107"
```

| Member | What it is |
|---|---|
| `Nuclide.load(name)` | Load one by name (`"I-131"`, `"Co-60"`, `"Tc-99m"`) |
| `Nuclide.load_all()` | Dict of **all** bundled records (1252 radionuclides + 246 stable endpoints = 1498) |
| `.half_life` / `.half_life_s` | Half-life (Quantity or seconds) |
| `.lambda_` | Decay constant λ = ln2 / half-life (`0.0` if stable) |
| `.activity(N, t=...)` | Activity of N atoms after time t |
| `.decay_modes` | Decay modes + branch fractions |
| `.source` / `.source_url` / `.fetched` | Where the data came from |

**Bundled catalog:** 1252 radionuclides + 246 stable endpoints = **1498 records**, all from ICRP-107.

```python
# List a few names
for name in list(Nuclide.load_all())[:5]:
    print(name)
```

The catalog also carries the decay graph: `progeny`, `branching`,
`is_stable`, and `sf_branch` describe where each nuclide goes.

If the name doesn't exist: raises `NuclideNotFoundError`.

---

## 3. Multi-nuclide inventory: `Inventory`

**Use case:** "I have Mo-99. Track Tc-99m and everything else that grows in."

You list **seeds**; pydecay walks the ICRP-107 progeny graph and builds one
joint decay system (daughters included, down to stable).

```python
from pydecay import Inventory

# Plain numbers are Bq by default
inv = Inventory({"Mo-99": 1e6})
print(inv.seeds)        # ('Mo-99',)
print(inv.names)        # Mo-99, Tc-99m, Tc-99, ... (full closure)
print(inv.n_species)

# Advance time — returns a NEW inventory (never mutates inv)
after = inv.decay("8.02 days")
print(after.activities())   # dict species -> Bq (or Quantities if you started with them)
print(after.numbers())      # atom counts
print(inv.total_activity()) # sum of activities, always a plain float in Bq
```

### Units on the constructor

```python
Inventory({"Co-60": 1e6})                    # Bq (default)
Inventory({"Co-60": 1e6}, units="Ci")
Inventory({"Co-60": 1e18}, units="atoms")
Inventory({"Co-60": 1.0}, units="g")
```

Stable nuclides cannot take activity units — use `units="atoms"` for them.

### Cumulative decays and time series

```python
# How many atoms of each species decayed during [0, t]?
cum = inv.cumulative_decays("1 day")
# stable species report 0.0

# Atom-number curves for plotting / export
t_seconds, series = inv.decay_time_series("8 days", npoints=101)
# series["Mo-99"] is a list of plain floats, one per time point

# Log time axis (e.g. many half-lives)
t_log, series_log = inv.decay_time_series(
    "1e6 seconds", npoints=200, time_scale="log", t_start=1.0
)
```

| Method | Returns |
|---|---|
| `.decay(t)` | New `Inventory` at time `t` |
| `.cumulative_decays(t)` | Atoms decayed on `[0, t]` per species |
| `.decay_time_series(t_end, ...)` | `(list[float] seconds, dict[str, list[float]])` atom counts |
| `.numbers()` / `.activities()` / `.masses()` | Current state dicts |
| `.total_activity()` | Sum of activities (Bq, always `float`) |
| `.half_lives()` | Half-life (s) per species (`inf` if stable) |
| `.names` / `.seeds` / `.n_species` / `.units` | Introspection |

**Immutable:** `decay` returns a new object. Negative `t` raises
`InvalidTimeError`; log series need `t_start > 0`. Unknown nuclide names raise
`NuclideNotFoundError`. A progeny cycle (should not exist in ICRP-107) raises
`ChainDefinitionError`.

---

## 4. Chains: `DecayChain`

**Use case:** "Parent decays to daughter, which decays to stable. How much of each at time t?"

### Linear chain (one path)

```python
from pydecay import DecayChain

# Parent (λ=0.693/s) -> stable daughter (λ=0)
chain = DecayChain([0.693, 0.0], names=["parent", "stable"])

# Atom counts after 1 day, start with 1e6 parent atoms
result = chain.at(t="1 days", n0={"parent": 1e6, "stable": 0.0})
print(result)  # {'parent': ..., 'stable': ...}
```

### From real nuclide names

```python
# Uses bundled ICRP-107 half-lives automatically
chain = DecayChain.from_isotopes(["Sr-90", "Y-90"])
print(chain.at(t="1 day", n0={"Sr-90": 1e6, "Y-90": 0.0}))
```

### Activity instead of atoms

```python
print(chain.activity(t="1 day", n0={"Sr-90": 1e6, "Y-90": 0.0}))
# dict of species -> Bq
```

| Method | Returns |
|---|---|
| `.at(t, n0=...)` | Atom counts at time t |
| `.activity(t, n0=...)` | Activity (Bq) at time t |
| `.names` | Tuple of species names |
| `.lambdas` | Tuple of decay constants (1/s) |

**Defaults:** if you omit `n0`, parent starts at `1.0`, everyone else at `0`.

---

## 5. Branching: `DecayChain.branching(...)`

**Use case:** "One parent can go two ways (60% / 30%). Track both daughters."

```python
from pydecay import DecayChain

b = DecayChain.branching(
    parent="P",
    branches={"D1": 0.6, "D2": 0.3},   # fractions; sum <= 1
    lambdas={"P": 0.7, "D1": 1e-5, "D2": 2e-5},
)

print(b.at(t="1 day"))       # atoms of P, D1, D2
print(b.activity(t="1 day")) # Bq of P, D1, D2
```

**Branch rule:** fractions must sum to **at most 1.0**.
If they sum to 0.9, the remaining 10% is an **untracked sink** (leaves the system).

---

## 6. Radiation spectra

### `emissions(name)`

**Use case:** "What radiation lines does Ac-223 emit, and with what probability?"

```python
from pydecay import emissions

rows = emissions("Ac-223")
print(len(rows))   # 480 emission rows
# Each row: energy (MeV), probability, code, ...
```

### `beta_spectrum(name)`

**Use case:** "Plot the beta energy spectrum for Sr-90."

```python
from pydecay import beta_spectrum

energies, amplitudes = beta_spectrum("Sr-90")
print(len(energies))  # 102 energy points
# energies in MeV; amplitudes = relative intensity
```

Both functions **lazy-load** on first call (they don't slow down `import pydecay`).

| Function | Returns | Notes |
|---|---|---|
| `emissions(name)` | `list[dict]` | RAD rows; empty/missing → error |
| `beta_spectrum(name)` | `(list[E_MeV], list[A])` | BET spectrum |

Stable nuclides (no radiation) raise `DataFormatError`.
Unknown names raise `NuclideNotFoundError`.

---

## 7. Errors — what can go wrong (and what you catch)

All errors inherit from `PyDecayError`.

| Exception | When |
|---|---|
| `NuclideNotFoundError` | Typo in nuclide name: `Nuclide.load("Xx-999")` |
| `InvalidTimeError` | Negative or infinite time; log-series bounds ≤ 0 |
| `InvalidHalfLifeError` | Half-life ≤ 0 or NaN in decay helpers (`Nuclide.lambda_` reports 0 for stable) |
| `ChainDefinitionError` | Bad chain, empty/duplicate Inventory seeds, progeny cycle |
| `DataFormatError` | Broken data record, or spectra on a stable nuclide |
| `UnitError` | Bad unit string, or string on `N0` / `A0` / Inventory amount |
| `PyDecayError` | Base class — catch this to catch **everything** above |

```python
from pydecay import Nuclide, NuclideNotFoundError, PyDecayError

try:
    n = Nuclide.load("Xx-999")
except NuclideNotFoundError:
    print("No such nuclide — check the spelling (e.g. I-131, Co-60).")

# Or catch every pydecay error at once:
try:
    ...
except PyDecayError as e:
    print("pydecay said:", e)
```

---

## 8. Units (optional, but nice)

You can pass plain numbers (SI: seconds, Bq, atoms) **or** human strings:

```python
from pydecay import decayed_activity

decayed_activity(A0=1000.0, half_life="8.02 days", time="24 hours")
decayed_activity(A0=1000.0, half_life=692988.48, time=86400.0)  # same, in seconds
```

With Pint Quantities, the output kind mirrors the input:

```python
import pint
from pydecay import decayed_atoms

ureg = pint.UnitRegistry()
N0 = 1e6 * ureg.atom
n = decayed_atoms(N0=N0, half_life="8.02 days", time="24 hours")
# n is still a Quantity in atoms
```

**Don't** pass strings for `N0` or `A0` — use numbers or Quantities
(otherwise you get `UnitError`).

### Promoted helpers (top-level)

Unit converters, decay kernels, and rate helpers are also importable from
the package root (same names as their home submodules `pydecay.units` /
`pydecay.decay` / `pydecay.api`):

```python
from pydecay import (
    to_seconds,
    bq_to_ci,
    ci_to_bq,
    atoms_to_grams,
    grams_to_atoms,
    decay_constant,
    mean_lifetime_s,
    dn_dt,
    da_dt,
    decay_ode_residual,
)

to_seconds("8.02 days")            # seconds as float
bq_to_ci(3.7e10)                   # 1.0
ci_to_bq(1.0)                      # 3.7e10
atoms_to_grams(1e18, 130.9061)     # grams
grams_to_atoms(1.0, 238.0508)      # atom count
decay_constant(8.02 * 86400)       # λ = ln2 / T½  (1/s)
mean_lifetime_s(decay_constant(7.0))  # τ = 1 / λ  (s)
dn_dt(1e6, "8.02 days")            # dN/dt (atoms/s)
da_dt(1000.0, "8.02 days", 0.0)    # dA/dt (Bq/s)
decay_ode_residual(1e6, 8.02 * 86400)  # 0.0 on analytic trajectory
```

### Instantaneous rates and ODE residual (0.5.0)

How fast is it changing *right now*?

```python
from pydecay import dn_dt, da_dt, decay_ode_residual

# dN/dt = -λN  (atoms/s; negative = losing atoms)
dn_dt(1e6, "8.02 days")

# dA/dt = -λ A(t)  (Bq/s at t=0 for 1000 Bq)
da_dt(1000.0, "8.02 days", 0.0)

# ODE residual dN/dt + λN — exactly 0 on an analytic trajectory
assert decay_ode_residual(1e6, 8.02 * 86400) == 0.0

# Check a numerical derivative against the law
h = 1e-4
T = 8.02 * 86400
n_t = 1e6 * 2 ** (-100.0 / T)
n_next = 1e6 * 2 ** (-(100.0 + h) / T)
print(decay_ode_residual(n_t, T, dn_dt_value=(n_next - n_t) / h))  # ~0
```

For multi-nuclide systems, `Inventory.instantaneous_rates()` returns
dN_i/dt for every species from the joint generator (`G @ N`):

```python
from pydecay import Inventory

inv = Inventory({"Mo-99": 1e6}, units="Bq")
print(inv.instantaneous_rates())  # dict species -> atoms/s (or Quantity)
```

### Dose rates and shielding (0.6.0)

How far does a source reach, and how much does a wall stop? Full guides:
[Dose rates](dose.md) and [Shielding](shielding.md).

```python
from pydecay import dose_rate, Inventory
from pydecay import material, hvl_slab, transmit_slab

# 1 MBq of Co-60 at 1 m -> air kerma (Gy/h)
dose_rate(1e6, "Co-60", r_m=1.0)            # 3.07e-7
dose_rate(1e6, "Co-60", r_m=1.0, quantity="ambient")  # Sv/h

# Whole inventory (summed over closure species, kind mirrors r)
Inventory({"Co-60": 1e6, "Cs-137": 1e6}).dose_rate(r="1 m")

# Narrow-beam shielding
hvl_slab("lead", 1.25)                       # 0.0104 m
transmit_slab(1.0, "lead", 0.01, 1.25)      # 0.513 through 1 cm Pb
```

Nuclides without photon coefficients (H-3, C-14, Fe-55, Sr-90, Y-90,
Po-210) raise `DoseDataError`; unknown materials raise `MaterialError`.

---

## 9. Cheat sheet (copy-paste)

```python
from pydecay import (
    Nuclide,
    DecayChain,
    Inventory,
    decayed_activity,
    decayed_atoms,
    remaining_fraction,
    emissions,
    beta_spectrum,
    to_seconds,
    bq_to_ci,
    ci_to_bq,
    atoms_to_grams,
    grams_to_atoms,
    decay_constant,
    mean_lifetime_s,
    dn_dt,
    da_dt,
    decay_ode_residual,
    __version__,
)

# --- version ---
print(__version__)  # "0.5.1"

# --- one isotope ---
i131 = Nuclide.load("I-131")
print(i131.half_life_s)
print(decayed_activity(A0=1000.0, half_life=i131.half_life, time=i131.half_life))  # 500
print(decayed_atoms(N0=1e6, half_life="8.02 days", time="24 hours"))
print(remaining_fraction(half_life="8.02 days", time="8.02 days"))  # 0.5

# --- inventory (auto progeny closure) ---
inv = Inventory({"Mo-99": 1e6}, units="Bq")
print(inv.decay("8.02 days").activities())
print(inv.cumulative_decays("1 day"))
t, series = inv.decay_time_series("8 days", npoints=101)

# --- chain ---
chain = DecayChain.from_isotopes(["Sr-90", "Y-90"])
print(chain.at(t="1 day", n0={"Sr-90": 1e6, "Y-90": 0.0}))

# --- branching ---
b = DecayChain.branching(
    parent="P",
    branches={"D1": 0.6, "D2": 0.3},
    lambdas={"P": 0.7, "D1": 1e-5, "D2": 2e-5},
)
print(b.at(t=1.0))

# --- spectra ---
rows = emissions("Co-60")
E, A = beta_spectrum("Sr-90")
print(len(rows), len(E))
```

---

## 10. Where to go next

| Topic | Page |
|---|---|
| Short runnable scripts | [Quickstart](quickstart.md) |
| Full signatures | [API reference](api.md) |
| The math behind the solvers | [Mathematics](math.md) |
| Bateman vs matrix exponential | [Architecture](architecture.md) |
| Where the numbers come from | [Data sources](data-sources.md) |
| Bq ↔ Ci, atoms ↔ grams | [Units](units.md) |

**One-line summary:**
`decayed_activity` / `decayed_atoms` / `remaining_fraction` answer "how much is left?"
· `Nuclide.load` looks up real half-lives (1252 ICRP-107 radionuclides + 246
stable endpoints = 1498 records)
· `Inventory` tracks a seed mix and every daughter that grows in
· `DecayChain` follows parents and daughters through time
· `emissions` / `beta_spectrum` give you radiation spectra.
