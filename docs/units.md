# Units

## Canonical internal units

All pure kernels (`decay.py`, `graph.py`, `_solver.py`) operate on plain
Python/NumPy floats in:

| Quantity | Unit |
|---|---|
| time | seconds |
| atom count | atoms (dimensionless count) |
| activity | becquerel (Bq) |

## Plain-float convention at the API

When you pass plain numbers (no pint Quantity, no unit string on unit-typed
args):

- `t` is seconds
- `A` is Bq
- `N` is atoms

## pint parsing rules

- Strings are accepted **only** for unit-typed convenience arguments:
  `t` / `time` and `half_life` (e.g. `"8.02 days"`, `"24 hours"`).
- `N0`, `A0`, and `n0` values must be numbers or pint Quantities.
  A string there raises `UnitError` (deliberate: these are primary numeric
  inputs, not unit annotations).
- Dimensionally wrong inputs (e.g. `"5 meters"` as time) raise `UnitError`.
- Negative time raises `InvalidTimeError`; non-positive / non-finite
  half-life raises `InvalidHalfLifeError`.

## Return-kind mirroring rule

Exact wording from the design spec §5: each result mirrors the kind of the
*primary numeric input it derives from* —

- `decayed_atoms` mirrors `N0`
- `decayed_activity` mirrors `A0`
- `Nuclide.activity` and `DecayChain.at` / `.activity` mirror `n0`
  (default: plain floats)
- Quantity in → Quantity out (same kind of unit); float in → float out
- String inputs on `t` / `half_life` never change output kind
- `remaining_fraction` is dimensionless and **always returns float**

## Conversions

| Conversion | Rule |
|---|---|
| Bq ↔ Ci | `1 Ci = 3.7e10 Bq` exact (NIST SP 811) |
| atoms ↔ grams | `N = (mass_g / M) * N_A`, `N_A = 6.02214076e23` exact (2019 SI, BIPM) |
| custom `atom` unit | dimensionless counting unit on the shared pint registry |

Helpers live in `pydecay.units`: `to_seconds`, `to_half_life_seconds`,
`to_float`, `mirror_quantity`, `atoms_to_grams`, `grams_to_atoms`,
`bq_to_ci`, `ci_to_bq`.

## Why not a full units library in the core

Pure kernels stay testable and dependency-light; pint is confined to the
API edge. Every call down into the pure modules passes canonical floats, so
unit handling bugs cannot corrupt the math layer.
