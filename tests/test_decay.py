"""Tests for the single-isotope decay law (spec section 1)."""

import math

import pytest

from pydecay import decay
from pydecay.exceptions import InvalidHalfLifeError, InvalidTimeError, PyDecayError


def test_decay_constant_from_half_life():
    lam = decay.decay_constant(8.0)
    assert lam == pytest.approx(math.log(2) / 8.0)


def test_half_life_identity():
    """N(T_half) == N0 / 2 exactly to tight tolerance (spec 1.2)."""
    t_half = 12.5
    lam = decay.decay_constant(t_half)
    assert decay.remaining_fraction(lam, t_half) == pytest.approx(0.5, rel=1e-12)
    assert decay.remaining_atoms(1.0e9, lam, t_half) == pytest.approx(0.5e9, rel=1e-12)


def test_mean_lifetime_identity():
    """N(tau) == N0 / e (spec 1.2)."""
    t_half = 7.0
    lam = decay.decay_constant(t_half)
    tau = decay.mean_lifetime_s(lam)
    assert tau == pytest.approx(t_half / math.log(2))
    assert decay.remaining_fraction(lam, tau) == pytest.approx(1.0 / math.e, rel=1e-12)


def test_activity_is_lambda_n():
    lam = decay.decay_constant(100.0)
    assert decay.activity_bq(5.0e6, lam) == pytest.approx(lam * 5.0e6)


def test_activity_follows_same_exponential():
    lam = decay.decay_constant(100.0)
    n0, t = 1.0e6, 250.0
    a0 = decay.activity_bq(n0, lam)
    at = decay.activity_bq(decay.remaining_atoms(n0, lam, t), lam)
    assert at == pytest.approx(a0 * math.exp(-lam * t), rel=1e-15)


def test_t_zero_returns_input():
    lam = decay.decay_constant(100.0)
    assert decay.remaining_atoms(12345.0, lam, 0.0) == 12345.0


def test_rejects_bad_half_life():
    with pytest.raises(InvalidHalfLifeError):
        decay.decay_constant(0.0)
    with pytest.raises(InvalidHalfLifeError):
        decay.decay_constant(-3.0)
    with pytest.raises(InvalidHalfLifeError):
        decay.decay_constant(math.nan)


def test_rejects_negative_time():
    lam = decay.decay_constant(100.0)
    with pytest.raises(InvalidTimeError):
        decay.remaining_fraction(lam, -1.0)


def test_rejects_negative_atoms():
    lam = decay.decay_constant(100.0)
    with pytest.raises(PyDecayError):
        decay.remaining_atoms(-1.0, lam, 1.0)
