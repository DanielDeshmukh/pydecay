"""Single-isotope analytical decay (spec section 1). Pure SI floats only.

Closed form ``N(t) = N0 * exp(-lambda * t)`` — never numerically integrated.
"""

from __future__ import annotations

import math

from pydecay.exceptions import InvalidHalfLifeError, InvalidTimeError, PyDecayError

LN2 = math.log(2.0)


def _validate_lambda(lambda_: float) -> float:
    """Require a finite positive decay constant."""
    if not math.isfinite(lambda_) or lambda_ <= 0:
        raise InvalidHalfLifeError(f"decay constant must be finite and > 0, got {lambda_}")
    return lambda_


def _validate_time(t_s: float) -> float:
    """Require a finite non-negative time in seconds."""
    if not math.isfinite(t_s):
        raise InvalidTimeError(f"time must be finite, got {t_s}")
    if t_s < 0:
        raise InvalidTimeError(f"time must be >= 0, got {t_s}")
    return t_s


def decay_constant(half_life_s: float) -> float:
    """Return lambda = ln(2) / T_half for a half-life in seconds."""
    if not math.isfinite(half_life_s) or half_life_s <= 0:
        raise InvalidHalfLifeError(f"half-life must be finite and > 0, got {half_life_s}")
    return LN2 / half_life_s


def mean_lifetime_s(lambda_: float) -> float:
    """Return the mean lifetime tau = 1 / lambda in seconds."""
    return 1.0 / _validate_lambda(lambda_)


def remaining_fraction(lambda_: float, t_s: float) -> float:
    """Return N(t)/N0 = exp(-lambda * t)."""
    lam = _validate_lambda(lambda_)
    t = _validate_time(t_s)
    return math.exp(-lam * t)


def remaining_atoms(n0: float, lambda_: float, t_s: float) -> float:
    """Return N(t) = N0 * exp(-lambda * t) for atom count ``n0``."""
    n = float(n0)
    if not math.isfinite(n) or n < 0:
        raise PyDecayError(f"N0 must be finite and >= 0, got {n0}")
    return n * remaining_fraction(lambda_, t_s)


def activity_bq(n_atoms: float, lambda_: float) -> float:
    """Return activity A = lambda * N in becquerels."""
    n = float(n_atoms)
    if not math.isfinite(n) or n < 0:
        raise PyDecayError(f"N must be finite and >= 0, got {n_atoms}")
    return _validate_lambda(lambda_) * n
