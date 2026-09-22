"""Unit handling: the single conversion chokepoint.

Internal canonical units are seconds, atoms, and becquerels as plain floats.
pint appears only here and in other edge modules; parse on the way in,
:func:`mirror_quantity` on the way out.
"""

from __future__ import annotations

import math
from typing import Any

import pint

from pydecay.exceptions import InvalidHalfLifeError, InvalidTimeError, UnitError

ureg = pint.UnitRegistry()
ureg.define("atom = 1")

AVOGADRO_PER_MOL = 6.02214076e23
"""Avogadro constant in 1/mol (exact, 2019 SI redefinition)."""

CI_IN_BQ = 3.7e10
"""1 curie in becquerels (exact, NIST SP 811)."""


def _as_quantity(value: float | int | str | pint.Quantity) -> float | pint.Quantity:
    """Coerce numbers and unit strings to a pint Quantity or keep floats."""
    if isinstance(value, str):
        try:
            return ureg.Quantity(value)
        except (pint.errors.UndefinedUnitError, ValueError) as exc:
            raise UnitError(f"cannot parse quantity from {value!r}") from exc
    return value


def to_float(value: float | int | str | pint.Quantity, unit: str) -> float:
    """Return ``value`` as a canonical float in ``unit``.

    Plain numbers are assumed to already be in ``unit``. Strings and
    Quantities are converted; dimension mismatches raise :class:`UnitError`.
    """
    q = _as_quantity(value)
    if isinstance(q, pint.Quantity):
        try:
            return float(q.to(unit).magnitude)
        except (pint.DimensionalityError, pint.errors.UndefinedUnitError) as exc:
            raise UnitError(f"{value!r} is not a valid {unit}") from exc
    return float(q)


def to_seconds(t: float | int | str | pint.Quantity) -> float:
    """Parse a time into seconds; require finite and >= 0."""
    s = to_float(t, "second")
    if not math.isfinite(s):
        raise InvalidTimeError(f"time must be finite, got {s}")
    if s < 0:
        raise InvalidTimeError(f"time must be >= 0, got {s}")
    return s


def to_half_life_seconds(h: float | int | str | pint.Quantity) -> float:
    """Parse a half-life into seconds; require finite and > 0."""
    s = to_float(h, "second")
    if not math.isfinite(s):
        raise InvalidHalfLifeError(f"half-life must be finite, got {s}")
    if s <= 0:
        raise InvalidHalfLifeError(f"half-life must be > 0, got {s}")
    return s


def mirror_quantity(value: float, like: Any, unit: str) -> float | pint.Quantity:
    """Return ``value`` in the same representation kind as ``like``.

    If ``like`` is a pint Quantity, the result is ``value * ureg(unit)``;
    otherwise a plain float is returned.
    """
    if isinstance(like, pint.Quantity):
        return value * ureg(unit)
    return float(value)


def atoms_to_grams(n_atoms: float, atomic_mass_u: float) -> float:
    """Convert an atom count to grams via the nuclide's atomic mass in u."""
    return float(n_atoms) * float(atomic_mass_u) / AVOGADRO_PER_MOL


def grams_to_atoms(m_g: float, atomic_mass_u: float) -> float:
    """Convert grams to an atom count via the nuclide's atomic mass in u."""
    return float(m_g) * AVOGADRO_PER_MOL / float(atomic_mass_u)


def bq_to_ci(bq: float) -> float:
    """Convert becquerels to curies."""
    return float(bq) / CI_IN_BQ


def ci_to_bq(ci: float) -> float:
    """Convert curies to becquerels."""
    return float(ci) * CI_IN_BQ
