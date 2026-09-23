"""Tests for solver dispatch, Bateman, expm, and stability regressions."""

import numpy as np
import pytest
from scipy.linalg import expm

from pydecay._solver import DEGENERATE_EPS, bateman_closed_form, solve, use_bateman
from pydecay.exceptions import ChainDefinitionError, InvalidTimeError, PyDecayError
from pydecay.graph import DecayGraph


def _expm_reference(graph, n0, t_s):
    return expm(graph.generator() * t_s) @ np.asarray(n0, dtype=np.float64)


def test_single_species_matches_exponential():
    g = DecayGraph.linear([0.693])
    out = solve(g, [1.0], 1.0)
    assert out[0] == pytest.approx(np.exp(-0.693), rel=1e-12)


def test_t_zero_returns_copy():
    g = DecayGraph.linear([1.0, 2.0])
    n0 = [5.0, 0.0]
    out = solve(g, n0, 0.0)
    np.testing.assert_array_equal(out, n0)
    out[0] = -1.0
    assert n0[0] == 5.0  # copy, not alias


def test_dispatch_bateman_only_for_well_separated_parent_only():
    well = DecayGraph.linear([1.0, 0.001])
    assert use_bateman(well, [1.0, 0.0]) is True
    assert use_bateman(well, [1.0, 0.5]) is False  # nonzero daughter IC
    almost = DecayGraph.linear([0.7, 0.7 * (1 + 1e-12)])
    assert use_bateman(almost, [1.0, 0.0]) is False  # near-degenerate
    branched = DecayGraph.branching(
        (1.0, 1.0), ((0.0, 0.8), (0.0, 0.0)), names=["P", "D"]
    )
    assert use_bateman(branched, [1.0, 0.0]) is False


def test_bateman_agrees_with_expm_well_separated():
    lambdas = [1.0, 0.01, 0.0002]
    g = DecayGraph.linear(lambdas)
    n0 = [1.0e9, 0.0, 0.0]
    for t in (0.5, 10.0, 100.0):
        b = solve(g, n0, t)
        e = _expm_reference(g, n0, t)
        np.testing.assert_allclose(b, e, rtol=1e-10, atol=1e-20)


def test_daughter_ingrowth_matrix_orientation():
    """Daughter must grow from zero — catches a transposed G."""
    g = DecayGraph.linear([1.0, 0.5, 0.1])
    out = solve(g, [1.0, 0.0, 0.0], 5.0)
    assert out[1] > 0.0
    assert out[2] > 0.0


def test_spec_2_3_near_degenerate_is_finite():
    """lambda = 0.6931 / 0.6932 must not produce NaN or divergence (spec 2.3)."""
    g = DecayGraph.linear([0.6931, 0.6932])
    out = solve(g, [1.0, 0.0], 1.0)
    assert np.all(np.isfinite(out))
    ref = _expm_reference(g, [1.0, 0.0], 1.0)
    np.testing.assert_allclose(out, ref, rtol=1e-8, atol=1e-15)
    assert out[0] == pytest.approx(np.exp(-0.6931), rel=1e-6)


def test_exactly_degenerate_is_finite():
    g = DecayGraph.linear([0.693, 0.693])
    assert use_bateman(g, [1.0, 0.0]) is False
    out = solve(g, [1.0, 0.0], 2.0)
    assert np.all(np.isfinite(out))
    ref = _expm_reference(g, [1.0, 0.0], 2.0)
    np.testing.assert_allclose(out, ref, rtol=1e-10, atol=1e-15)


def test_near_defective_expm_conserves_atoms():
    """Regression: single-shot expm loses atoms on a near-defective generator.

    Falsifier from property test_linear_chain_conservation: lam_parent=1.0,
    lam_mid=0.9999999999999999, t=4.0, n0=1.0 returned sum ~1.020487.
    """
    g = DecayGraph.linear([1.0, 0.9999999999999999, 0.0])
    assert use_bateman(g, [1.0, 0.0, 0.0]) is False
    out = solve(g, [1.0, 0.0, 0.0], 4.0)
    assert out.sum() == pytest.approx(1.0, rel=1e-9)
    assert np.all(out >= -1e-9)


def test_conservation_linear_chain_to_stable():
    g = DecayGraph.linear([1.0, 0.0], names=["A", "stable"])
    out = solve(g, [3.0, 0.0], 10.0)
    assert out.sum() == pytest.approx(3.0, rel=1e-12)


def test_branching_conservation_when_fractions_sum_to_one():
    fractions = ((0.0, 0.6, 0.4), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    g = DecayGraph.branching((2.0, 0.0, 0.0), fractions, names=["P", "D1", "D2"])
    out = solve(g, [10.0, 0.0, 0.0], 8.0)
    assert out.sum() == pytest.approx(10.0, rel=1e-10)
    assert out[1] > 0 and out[2] > 0


def test_branching_partial_sum_decays_to_untracked_sink():
    fractions = ((0.0, 0.5), (0.0, 0.0))
    g = DecayGraph.branching((1.0, 0.1), fractions, names=["P", "D"])
    out = solve(g, [1.0, 0.0], 50.0)
    assert 0.0 < out.sum() <= 1.0 + 1e-12


def test_validations():
    g = DecayGraph.linear([1.0, 2.0])
    with pytest.raises(ChainDefinitionError):
        solve(g, [1.0], 1.0)
    with pytest.raises(PyDecayError):
        solve(g, [-1.0, 0.0], 1.0)
    with pytest.raises(InvalidTimeError):
        solve(g, [1.0, 0.0], -0.5)


def test_eps_override_is_respected():
    g = DecayGraph.linear([1.0, 0.001])
    assert use_bateman(g, [1.0, 0.0], eps=1e3) is False
    assert DEGENERATE_EPS == 1e-8


def test_bateman_direct_call_parent_only_formula():
    out = bateman_closed_form([1.0, 0.5], 100.0, 1.0)
    assert out[0] == pytest.approx(100.0 * np.exp(-1.0), rel=1e-12)
    l1, l2, t, n0 = 1.0, 0.5, 1.0, 100.0
    expected2 = n0 * l1 / (l1 - l2) * (np.exp(-l2 * t) - np.exp(-l1 * t))
    assert out[1] == pytest.approx(expected2, rel=1e-12)
