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


def test_dn_dt_is_minus_lambda_n():
    lam = decay.decay_constant(10.0)
    assert decay.dn_dt(1.0e6, lam) == pytest.approx(-lam * 1.0e6)
    assert decay.dn_dt(0.0, lam) == 0.0


def test_dn_dt_rejects_bad_n_and_lambda():
    lam = decay.decay_constant(10.0)
    with pytest.raises(PyDecayError):
        decay.dn_dt(-1.0, lam)
    with pytest.raises(InvalidHalfLifeError):
        decay.dn_dt(1.0, 0.0)


def test_da_dt_negative_and_matches_derivative_of_activity():
    lam = decay.decay_constant(10.0)
    a0, t, dt = 1000.0, 3.0, 1e-5
    a_t = a0 * math.exp(-lam * t)
    a_next = a0 * math.exp(-lam * (t + dt))
    assert decay.da_dt(a0, lam, t) == pytest.approx(-lam * a_t)
    assert decay.da_dt(a0, lam, t) == pytest.approx((a_next - a_t) / dt, rel=1e-4)


def test_da_dt_rejects_bad_inputs():
    lam = decay.decay_constant(10.0)
    with pytest.raises(PyDecayError):
        decay.da_dt(-1.0, lam, 0.0)
    with pytest.raises(InvalidTimeError):
        decay.da_dt(1.0, lam, -1.0)


def test_ode_residual_zero_on_analytic_rate_and_nonzero_on_mismatch():
    lam = decay.decay_constant(10.0)
    n = 1.0e6
    assert decay.ode_residual(n, lam) == 0.0
    assert decay.ode_residual(n, lam, -lam * n) == pytest.approx(0.0, abs=1e-9)
    assert decay.ode_residual(n, lam, 0.0) == pytest.approx(lam * n)


def test_ode_residual_rejects_bad_inputs():
    lam = decay.decay_constant(10.0)
    with pytest.raises(PyDecayError):
        decay.ode_residual(-1.0, lam)
    with pytest.raises(InvalidHalfLifeError):
        decay.ode_residual(1.0, 0.0)
    with pytest.raises(PyDecayError):
        decay.ode_residual(1.0, lam, math.nan)
