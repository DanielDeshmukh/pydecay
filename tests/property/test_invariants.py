"""Hypothesis invariants: bounds, monotonicity, conservation, solver agreement."""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st
from scipy.linalg import expm

from pydecay import decayed_activity, decayed_atoms, remaining_fraction
from pydecay._solver import solve
from pydecay.graph import DecayGraph
from pydecay.inventory import Inventory
from pydecay.nuclide import Nuclide

finite_positive = st.floats(
    min_value=1e-3, max_value=1e17, allow_nan=False, allow_infinity=False
)

inventory_seed = st.sampled_from(["Co-60", "I-131", "Sr-90", "Mo-99", "Tc-99m"])
inventory_atoms = st.floats(
    min_value=1.0, max_value=1e18, allow_nan=False, allow_infinity=False
)
inventory_t = st.floats(min_value=0.0, max_value=1.0e10, allow_nan=False)


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


@settings(deadline=None, max_examples=40)
@given(name=inventory_seed, n0=inventory_atoms, t=inventory_t)
def test_inventory_decay_nonnegative(name, n0, t):
    inv = Inventory({name: n0}, units="atoms")
    after = inv.decay(t).numbers()
    tol = 1e-9 * max(n0, 1.0)
    assert all(v >= -tol for v in after.values())


@settings(deadline=None, max_examples=30)
@given(name=inventory_seed, n0=inventory_atoms, t=inventory_t)
def test_inventory_decay_immutable(name, n0, t):
    inv = Inventory({name: n0}, units="atoms")
    before = inv.numbers()
    advanced = inv.decay(t)
    assert advanced is not inv
    assert inv.numbers() == before
    assert inv.seeds == (name,)


@settings(deadline=None, max_examples=30)
@given(
    name=inventory_seed,
    n0=inventory_atoms,
    t1=st.floats(min_value=0.0, max_value=5.0e9, allow_nan=False),
    t2=st.floats(min_value=0.0, max_value=5.0e9, allow_nan=False),
)
def test_inventory_decay_composition(name, n0, t1, t2):
    inv = Inventory({name: n0}, units="atoms")
    left = inv.decay(t1).decay(t2).numbers()
    right = inv.decay(t1 + t2).numbers()
    tol = 1e-9 * max(n0, 1.0)
    assert all(abs(left[k] - right[k]) <= tol for k in left)


@settings(deadline=None, max_examples=30)
@given(name=inventory_seed, n0=inventory_atoms)
def test_inventory_decay_t0_identity(name, n0):
    inv = Inventory({name: n0}, units="atoms")
    after = inv.decay(0.0).numbers()
    for key, val in after.items():
        expected = n0 if key == name else 0.0
        assert abs(val - expected) <= 1e-9 * max(n0, 1.0)


@settings(deadline=None, max_examples=40)
@given(name=inventory_seed, n0=inventory_atoms, t=inventory_t)
def test_inventory_parent_activity_monotone(name, n0, t):
    inv = Inventory({name: n0}, units="atoms")
    a0 = inv.activities()[name]
    at = inv.decay(t).activities()[name]
    assert at <= a0 + 1e-9 * max(a0, 1.0)


@settings(deadline=None, max_examples=40)
@given(name=inventory_seed, n0=inventory_atoms, t=inventory_t)
def test_inventory_cumulative_seed_balance(name, n0, t):
    """Seeds have no inflow (DAG): N(t) + cumulative on [0,t] == N0."""
    inv = Inventory({name: n0}, units="atoms")
    remaining = inv.decay(t).numbers()[name]
    cum = inv.cumulative_decays(t)[name]
    assert abs(remaining + float(cum) - n0) <= 1e-9 * max(n0, 1.0)


@settings(deadline=None, max_examples=30)
@given(name=inventory_seed, n0=inventory_atoms, t=inventory_t)
def test_inventory_cumulative_nonnegative(name, n0, t):
    inv = Inventory({name: n0}, units="atoms")
    cum = inv.cumulative_decays(t)
    tol = 1e-9 * max(n0, 1.0)
    assert all(float(v) >= -tol for v in cum.values())


@settings(deadline=None, max_examples=30)
@given(n0=inventory_atoms, t=inventory_t)
def test_inventory_conservation_conservative_chain(n0, t):
    """Sr-90 -> Y-90 -> Zr-90 rows sum to 1: total atoms conserved."""
    inv = Inventory({"Sr-90": n0}, units="atoms")
    after = inv.decay(t).numbers()
    total = sum(after.values())
    assert abs(total - n0) <= 1e-9 * n0


@settings(deadline=None, max_examples=30)
@given(n0=inventory_atoms, t=inventory_t)
def test_inventory_conservation_co60(n0, t):
    """Co-60 -> Ni-60 (100%): total atoms conserved."""
    inv = Inventory({"Co-60": n0}, units="atoms")
    total = sum(inv.decay(t).numbers().values())
    assert abs(total - n0) <= 1e-9 * n0


@settings(deadline=None, max_examples=25)
@given(
    name=inventory_seed,
    n0=inventory_atoms,
    t_end=st.floats(min_value=1.0, max_value=1.0e9, allow_nan=False),
)
def test_inventory_series_endpoints(name, n0, t_end):
    inv = Inventory({name: n0}, units="atoms")
    times, series = inv.decay_time_series(t_end, npoints=7)
    assert times[0] == 0.0
    assert times[-1] == t_end
    start = inv.numbers()
    end = inv.decay(t_end).numbers()
    tol = 1e-9 * max(n0, 1.0)
    for key, vals in series.items():
        assert abs(vals[0] - start[key]) <= tol
        assert abs(vals[-1] - end[key]) <= tol
        assert all(v >= -tol for v in vals)


@settings(deadline=None, max_examples=20)
@given(n0=inventory_atoms)
def test_inventory_half_life_identity_co60(n0):
    """Co-60 parent falls to N0/2 after one half-life (stable Ni-60 daughter)."""
    hl = Nuclide.load("Co-60").half_life_s
    inv = Inventory({"Co-60": n0}, units="atoms")
    parent = inv.decay(hl).numbers()["Co-60"]
    assert abs(parent - n0 / 2.0) <= 1e-9 * (n0 / 2.0)
