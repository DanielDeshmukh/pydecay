"""Public convenience functions for single-isotope decay (spec sections 1 and 5)."""

from __future__ import annotations

from typing import Any

from pydecay import decay
from pydecay.exceptions import UnitError
from pydecay.units import mirror_quantity, to_float, to_half_life_seconds, to_seconds


def _canonical_n0(N0: float | Any) -> float:
    """Return N0 as a non-negative float; reject strings."""
    if isinstance(N0, str):
        raise UnitError(f"N0 must be a number or Quantity, got string {N0!r}")
    n = to_float(N0, "atom")
    if not (n >= 0):
        raise UnitError(f"N0 must be >= 0, got {N0!r}")
    return n


def decayed_atoms(
    N0: float | Any,
    half_life: float | str | Any,
    time: float | str | Any,
) -> float | Any:
    """Atoms remaining after ``time``: N0 * exp(-ln2/T_half * t). Mirrors ``N0``."""
    lam = decay.decay_constant(to_half_life_seconds(half_life))
    t_s = to_seconds(time)
    n = decay.remaining_atoms(_canonical_n0(N0), lam, t_s)
    return mirror_quantity(n, N0, "atom")


def decayed_activity(
    A0: float | Any,
    half_life: float | str | Any,
    time: float | str | Any,
) -> float | Any:
    """Activity after ``time``: A0 * exp(-ln2/T_half * t). Plain floats are Bq."""
    if isinstance(A0, str):
        raise UnitError(f"A0 must be a number or Quantity, got string {A0!r}")
    a0 = to_float(A0, "becquerel")
    if not (a0 >= 0):
        raise UnitError(f"A0 must be >= 0, got {A0!r}")
    lam = decay.decay_constant(to_half_life_seconds(half_life))
    t_s = to_seconds(time)
    a = a0 * decay.remaining_fraction(lam, t_s)
    return mirror_quantity(a, A0, "becquerel")


def remaining_fraction(half_life: float | str | Any, time: float | str | Any) -> float:
    """Dimensionless fraction N(t)/N0. Always returns a plain float."""
    lam = decay.decay_constant(to_half_life_seconds(half_life))
    return decay.remaining_fraction(lam, to_seconds(time))


def dn_dt(N: float | Any, half_life: float | str | Any) -> float | Any:
    """Instantaneous atom change dN/dt = -lambda * N (atoms/s). Mirrors ``N``."""
    lam = decay.decay_constant(to_half_life_seconds(half_life))
    n = _canonical_n0(N)
    return mirror_quantity(decay.dn_dt(n, lam), N, "atom/second")


def da_dt(A0: float | Any, half_life: float | str | Any, time: float | str | Any) -> float | Any:
    """Instantaneous activity change dA/dt = -lambda * A(t) (Bq/s). Mirrors ``A0``."""
    if isinstance(A0, str):
        raise UnitError(f"A0 must be a number or Quantity, got string {A0!r}")
    a0 = to_float(A0, "becquerel")
    if not (a0 >= 0):
        raise UnitError(f"A0 must be >= 0, got {A0!r}")
    lam = decay.decay_constant(to_half_life_seconds(half_life))
    t_s = to_seconds(time)
    return mirror_quantity(decay.da_dt(a0, lam, t_s), A0, "becquerel/second")


def decay_ode_residual(
    N: float | Any,
    half_life: float | str | Any,
    *,
    dn_dt_value: float | Any | None = None,
) -> float:
    """ODE residual dN/dt + lambda * N; ~0 when ``dn_dt_value`` satisfies the law.

    Analytic default (``dn_dt_value=None``) yields exactly 0. Pass a numerical
    derivative to check an approximate trajectory. Always returns a plain float.
    """
    lam = decay.decay_constant(to_half_life_seconds(half_life))
    n = _canonical_n0(N)
    rate = None if dn_dt_value is None else to_float(dn_dt_value, "atom/second")
    return decay.ode_residual(n, lam, rate)
