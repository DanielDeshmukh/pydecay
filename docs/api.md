# API reference

Every public symbol re-exported from `pydecay` (`src/pydecay/__init__.py`).
Signatures are the shipped ones; each section has a minimal example.

## Module-level functions

**Time contract:** every public decay function requires `time >= 0`
(finite). Negative time raises `InvalidTimeError`. Back-calculating
earlier activities ("what was it yesterday?") is out of scope for v2.

### `decayed_atoms`

```python
decayed_atoms(N0, half_life, time) -> float | pint.Quantity
```

Atoms remaining after `time`: `N0 * exp(-ln2/T_half * t)`. Mirrors the kind
of `N0`. Strings rejected on `N0` (`UnitError`).

```python
from pydecay import decayed_atoms
decayed_atoms(N0=1e6, half_life="8.02 days", time="24 hours")
```

### `decayed_activity`

```python
decayed_activity(A0, half_life, time) -> float | pint.Quantity
```

Activity after `time`: `A0 * exp(-ln2/T_half * t)`. Plain floats are Bq.
Mirrors the kind of `A0`.

```python
from pydecay import decayed_activity
decayed_activity(A0=1000.0, half_life="8.02 days", time="8.02 days")  # -> 500.0
```

### `remaining_fraction`

```python
remaining_fraction(half_life, time) -> float
```

Dimensionless fraction `N(t)/N0`. **Always returns a plain float.**

```python
from pydecay import remaining_fraction
remaining_fraction(half_life="8.02 days", time="8.02 days")  # -> 0.5
```

## `Nuclide`

Frozen dataclass over one bundled record. All times are SI seconds; atomic
mass is in unified atomic mass units (u).

### Class methods

| Method | Signature | Description |
|---|---|---|
| `Nuclide.load` | `load(name: str) -> Nuclide` | Load by name (e.g. `"I-131"`); raises `NuclideNotFoundError` if absent |
| `Nuclide.load_all` | `load_all() -> dict[str, Nuclide]` | Load every bundled nuclide |
| `Nuclide.from_record` | `from_record(name: str, record: dict) -> Nuclide` | Build + validate from a raw JSON record; raises `DataFormatError` on bad keys/values |

### Properties / methods

| Member | Type | Description |
|---|---|---|
| `lambda_` | `float` (property) | Decay constant in 1/s; `0.0` for stable / infinite half-life |
| `half_life` | `pint.Quantity` (property) | Half-life as a Quantity in seconds |
| `activity(N, t=0)` | `-> float \| Quantity` | `A(t) = lambda * N * exp(-lambda * t)` in Bq, mirroring `N`'s kind |
| `half_life_s` | `float` | Half-life in plain seconds |
| `atomic_mass_u` | `float` | Atomic mass in u |
| `decay_modes` | `tuple[DecayMode, ...]` | Best-effort modes + branch fractions |
| `progeny` | `tuple[str, ...]` | Direct daughter names from the catalog (empty if stable) |
| `branching` | `tuple[float, ...]` | Branch fractions aligned with `progeny` |
| `is_stable` | `bool` | `True` for stable endpoints (λ = 0) |
| `sf_branch` | `float \| None` | Spontaneous-fission branch when present |
| `source`, `source_url`, `fetched` | `str` | Provenance metadata |

```python
from pydecay import Nuclide
i131 = Nuclide.load("I-131")
i131.lambda_          # 1/s
i131.half_life        # pint Quantity (seconds)
i131.activity(N=1e6, t="8.02 days")
i131.progeny          # ("Xe-131m", "Xe-131")
i131.branching        # matching branch fractions
```

## `Inventory`

Immutable multi-nuclide inventory with automatic progeny closure. Seeds are
user amounts; every reachable daughter (down to stable) is included in one
joint decay graph. Construction accepts plain numbers or pint Quantities in
`units` (`"Bq"` default, also `"Ci"`, `"atoms"`, `"g"`). Kind (plain vs
Quantity) is mirrored by accessors and preserved across `decay`.

### Constructor

| Constructor | Description |
|---|---|
| `Inventory(contents, *, units="Bq", eps=1e-8)` | `{"I-131": 1e6}` → seeds + full progeny closure |

### Methods / properties

| Member | Signature | Description |
|---|---|---|
| `.decay` | `decay(t) -> Inventory` | New inventory advanced by `t`; never mutates `self` |
| `.cumulative_decays` | `cumulative_decays(t) -> dict[str, float \| Quantity]` | Atoms that decayed on `[0, t]` per species (stable = 0); mirrors kind |
| `.decay_time_series` | `decay_time_series(t_end, *, npoints=501, time_scale="linear", t_start=0.0) -> tuple[list[float], dict[str, list[float]]]` | Atom-number curves over the closure; plain floats (does not mirror Quantity) |
| `.numbers` | `numbers() -> dict[str, float \| Quantity]` | Atom counts now; mirrors kind |
| `.activities` | `activities() -> dict[str, float \| Quantity]` | Activity (Bq) now; mirrors kind |
| `.masses` | `masses() -> dict[str, float \| Quantity]` | Mass (g) now; mirrors kind |
| `.total_activity` | `total_activity() -> float` | Sum of activities over the closure (always Bq float) |
| `.half_lives` | `half_lives() -> dict[str, float]` | Half-life (s) per species; `inf` for stable |
| `.names` | `tuple[str, ...]` | Species in graph order (seeds first, then BFS progeny) |
| `.n_species` | `int` | Closure size |
| `.seeds` | `tuple[str, ...]` | Normalized constructor seeds |
| `.units` | `str` | Canonical unit label for plain-number amounts |

`time_scale` is `"linear"` or `"log"`; log grids require `t_start > 0` and
`t_end > 0` (`InvalidTimeError`). Negative or reversed time ranges raise
`InvalidTimeError`. `npoints < 2` or an unknown `time_scale` raises
`PyDecayError`. Progeny cycles raise `ChainDefinitionError`.
Catalog branching rows that sum slightly above 1 (ICRP rounding noise,
within 0.035) are renormalized to exactly 1 when building the joint graph.

```python
from pydecay import Inventory
inv = Inventory({"Mo-99": 1e6}, units="Bq")   # pulls in Tc-99m, Tc-99, ...
after = inv.decay("8.02 days")
after.activities()                             # dict species -> Bq
inv.cumulative_decays("1 day")                 # atoms decayed on [0, 1 day]
t, series = inv.decay_time_series("8 days", npoints=101)
```

## `DecayChain`

Linear or star-branched chain. Construction validates topology; evaluation
is lazy per `t`. Solver dispatch (Bateman vs `expm`) is an internal detail.

### Constructors

| Constructor | Description |
|---|---|
| `DecayChain(lambdas, names=None, *, eps=1e-8)` | Linear chain from decay constants (1/s), parent first |
| `DecayChain.from_isotopes(names, *, eps=1e-8)` | Linear chain from bundled nuclide names, parent→daughter |
| `DecayChain.branching(parent, branches, *, lambdas=None, eps=1e-8)` | Star chain: one parent → terminal daughters by fraction |

### Methods / properties

| Member | Signature | Description |
|---|---|---|
| `.at` | `at(t=0, *, n0=None) -> dict[str, float \| Quantity]` | Atom counts of every species at `t`; mirrors `n0` kind |
| `.activity` | `activity(t=0, *, n0=None) -> dict[str, float \| Quantity]` | Activity (Bq) of every species at `t`; mirrors `n0` kind |
| `.names` | `tuple[str, ...]` | Species names in graph order |
| `.lambdas` | `tuple[float, ...]` | Decay constants (1/s), graph order |

Default `n0` when omitted: parent `1.0`, all others `0` (plain floats).
Branching fractions must sum to `[0, 1]`; the remainder is an untracked sink.

```python
from pydecay import DecayChain
chain = DecayChain([0.693, 0.0], names=["parent", "stable"])
chain.at(t="1 days", n0={"parent": 1e6, "stable": 0.0})
```

## Module-level helpers

Promoted unit and decay kernels (same names as their home submodules).

| Function | Signature | Description |
|---|---|---|
| `to_seconds` | `to_seconds(t) -> float` | Parse time (str / Quantity / number) to seconds; `t >= 0` finite |
| `bq_to_ci` | `bq_to_ci(bq: float) -> float` | Becquerels → curies (`/ 3.7e10`) |
| `ci_to_bq` | `ci_to_bq(ci: float) -> float` | Curies → becquerels (`* 3.7e10`) |
| `atoms_to_grams` | `atoms_to_grams(n_atoms, atomic_mass_u) -> float` | Atom count → grams |
| `grams_to_atoms` | `grams_to_atoms(m_g, atomic_mass_u) -> float` | Grams → atom count |
| `decay_constant` | `decay_constant(half_life_s) -> float` | λ = ln2 / T½ (1/s); rejects ≤ 0 / non-finite |
| `mean_lifetime_s` | `mean_lifetime_s(lambda_) -> float` | τ = 1 / λ (s); rejects λ ≤ 0 / non-finite |

```python
from pydecay import bq_to_ci, ci_to_bq, decay_constant, mean_lifetime_s, to_seconds

to_seconds("8.02 days")
bq_to_ci(3.7e10)                 # 1.0
decay_constant(8.02 * 86400)     # 1/s
mean_lifetime_s(decay_constant(8.02 * 86400))
```

## Exception hierarchy

All package-raised errors derive from `PyDecayError`.

| Exception | Trigger |
|---|---|
| `PyDecayError` | Base class; also wraps scipy failures, non-finite solver output (never returns NaN), and invalid `decay_time_series` arguments (`npoints` / `time_scale`) |
| `NuclideNotFoundError` | Unknown isotope name at load time |
| `InvalidHalfLifeError` | λ ≤ 0, NaN, or non-finite half-life / decay constant in `decay` helpers. `Nuclide.lambda_` / `.activity()` do **not** raise for stable nuclides — they report λ = 0 / 0 Bq |
| `InvalidTimeError` | `t < 0` or non-finite time; log-series bounds ≤ 0; reversed or negative `decay_time_series` range |
| `ChainDefinitionError` | Empty chain, length mismatch, branching fractions sum > 1 (beyond catalog noise tol), λ = 0 on a non-terminal species, unknown species in `n0`; also empty/duplicate Inventory seeds, progeny cycle, or closure depth > 256 |
| `DataFormatError` | Bundled JSON record missing required keys or carrying non-parseable values; unparseable nuclide name |
| `UnitError` | Unparseable unit string, dimensionally wrong pint input, or string on `N0` / `A0` / Inventory amount |

```python
from pydecay import PyDecayError, NuclideNotFoundError, UnitError
try:
    Nuclide.load("X-999")
except NuclideNotFoundError:
    ...
```

## `spectra`

Optional radiation spectra access (ICRP-107 RAD/BET). Lazy-loaded on first
call; not read on `import pydecay`.

| Function | Signature | Description |
|---|---|---|
| `emissions` | `emissions(name: str) -> list[dict]` | RAD emission rows (`E_MeV`, `prob`, `code_AN`, …); raises `NuclideNotFoundError` if unknown or no rows |
| `beta_spectrum` | `beta_spectrum(name: str) -> tuple[list[float], list[float]]` | `(E_MeV, A)` beta spectrum; raises `NuclideNotFoundError` / `DataFormatError` if missing |

```python
from pydecay.spectra import emissions, beta_spectrum
rows = emissions("Ac-223")
E, A = beta_spectrum("Ac-226")
```

## Version

```python
import pydecay
pydecay.__version__  # "0.4.0"
```
