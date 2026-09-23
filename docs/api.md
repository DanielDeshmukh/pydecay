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
| `lambda_` | `float` (property) | Decay constant in 1/s |
| `half_life` | `pint.Quantity` (property) | Half-life as a Quantity in seconds |
| `activity(N, t=0)` | `-> float \| Quantity` | `A(t) = lambda * N * exp(-lambda * t)` in Bq, mirroring `N`'s kind |
| `half_life_s` | `float` | Half-life in plain seconds |
| `atomic_mass_u` | `float` | Atomic mass in u |
| `decay_modes` | `tuple[DecayMode, ...]` | Best-effort modes + branch fractions |
| `source`, `source_url`, `fetched` | `str` | Provenance metadata |

```python
from pydecay import Nuclide
i131 = Nuclide.load("I-131")
i131.lambda_          # 1/s
i131.half_life        # pint Quantity (seconds)
i131.activity(N=1e6, t="8.02 days")
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

## Exception hierarchy

All package-raised errors derive from `PyDecayError`.

| Exception | Trigger |
|---|---|
| `PyDecayError` | Base class; also wraps scipy failures and non-finite solver output (never returns NaN) |
| `NuclideNotFoundError` | Unknown isotope name at load time |
| `InvalidHalfLifeError` | λ ≤ 0, NaN, or non-finite half-life / decay constant |
| `InvalidTimeError` | `t < 0` or non-finite time |
| `ChainDefinitionError` | Empty chain, length mismatch, branching fractions sum > 1, λ = 0 on a non-terminal species, unknown species in `n0` |
| `DataFormatError` | Bundled JSON record missing required keys or carrying non-parseable values; unparseable nuclide name |
| `UnitError` | Unparseable unit string, dimensionally wrong pint input, or string on `N0` / `A0` |

```python
from pydecay import PyDecayError, NuclideNotFoundError, UnitError
try:
    Nuclide.load("X-999")
except NuclideNotFoundError:
    ...
```

## Version

```python
import pydecay
pydecay.__version__  # "0.1.1"
```
