"""Hypothesis invariants: bounds, monotonicity, conservation, solver agreement."""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st
from scipy.linalg import expm

from pydecay import decayed_activity, decayed_atoms, remaining_fraction
from pydecay._solver import solve
from pydecay.graph import DecayGraph

finite_positive = st.floats(
    min_value=1e-3, max_value=1e17, allow_nan=False, allow_infinity=False
)


@given(half_life=finite_positive, t=st.floats(min_value=0.0, max_value=1e18, allow_nan=False))
def test_remaining_fraction_bounds(half_life, t):
    f = remaining_fraction(half_life, t)
    assert 0.0 <= f <= 1.0


@given(
    half_life=finite_positive,
    t1=st.floats(min_value=0.0, max_value=1e18, allow_nan=False),
    delta=st.floats(min_value=0.0, max_value=1e18, allow_nan=False),
)
def test_remaining_fraction_monotone(half_life, t1, delta):
    f1 = remaining_fraction(half_life, t1)
    f2 = remaining_fraction(half_life, t1 + delta)
    assert f2 <= f1 + 1e-15


@given(
    a0=st.floats(min_value=0.0, max_value=1e30, allow_nan=False, allow_infinity=False),
    half_life=finite_positive,
    t1=st.floats(min_value=0.0, max_value=1e18, allow_nan=False),
    delta=st.floats(min_value=0.0, max_value=1e18, allow_nan=False),
)
def test_activity_monotone(a0, half_life, t1, delta):
    a1 = decayed_activity(a0, half_life, t1)
    a2 = decayed_activity(a0, half_life, t1 + delta)
    assert a2 <= a1 + 1e-6 * max(a1, 1.0)


@given(
    n0=st.floats(min_value=1.0, max_value=1e20, allow_nan=False),
    half_life=finite_positive,
)
def test_half_life_identity(n0, half_life):
    n = decayed_atoms(n0, half_life, half_life)
    assert abs(n - n0 / 2.0) <= 1e-12 * (n0 / 2.0)


@settings(deadline=None, max_examples=30)
@given(
    lam_parent=st.floats(min_value=1e-6, max_value=1.0),
    lam_mid=st.floats(min_value=1e-6, max_value=1.0),
    t=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
    n0=st.floats(min_value=1.0, max_value=1e12, allow_nan=False),
)
def test_linear_chain_conservation(lam_parent, lam_mid, t, n0):
    """Parent -> mid -> stable (lambda=0): atoms only transform, sum conserved."""
    g = DecayGraph.linear([lam_parent, lam_mid, 0.0])
    out = solve(g, [n0, 0.0, 0.0], t)
    assert abs(out.sum() - n0) <= 1e-9 * n0
    assert np.all(out >= -1e-9 * n0)


@settings(deadline=None, max_examples=30)
@given(
    lam_parent=st.floats(min_value=1e-4, max_value=1.0),
    t=st.floats(min_value=0.0, max_value=50.0, allow_nan=False),
)
def test_branching_nonnegative(lam_parent, t):
    fractions = ((0.0, 0.6, 0.4), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    g = DecayGraph.branching(
        (lam_parent, 10.0 * lam_parent, 20.0 * lam_parent),
        fractions,
        names=["P", "D1", "D2"],
    )
    out = solve(g, [1.0, 0.0, 0.0], t)
    assert np.all(out >= -1e-12)


@settings(deadline=None, max_examples=40)
@given(
    lam1=st.floats(min_value=1e-4, max_value=1.0),
    ratio=st.floats(min_value=100.0, max_value=1e6),
    t=st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
)
def test_bateman_matches_expm_well_separated(lam1, ratio, t):
    lam2 = lam1 / ratio
    g = DecayGraph.linear([lam1, lam2])
    n0 = [1.0e6, 0.0]
    b = solve(g, n0, t)
    e = expm(g.generator() * t) @ np.asarray(n0, dtype=np.float64)
    np.testing.assert_allclose(b, e, rtol=1e-9, atol=1e-9)
