"""Tests for DecayGraph construction and the generator matrix."""

import numpy as np
import pytest

from pydecay.exceptions import ChainDefinitionError
from pydecay.graph import DecayGraph


def test_linear_three_chain_structure():
    g = DecayGraph.linear([0.6, 0.3, 0.1], names=["A", "B", "C"])
    assert g.names == ("A", "B", "C")
    assert not g.is_branched
    assert g.fractions[0][1] == 1.0
    assert g.fractions[1][2] == 1.0
    assert g.fractions[0][2] == 0.0


def test_linear_default_names():
    g = DecayGraph.linear([1.0, 2.0])
    assert g.names == ("species-1", "species-2")


def test_generator_linear_orientation():
    """dN/dt = G @ N: parent feeds daughter (subdiagonal), not the reverse."""
    g = DecayGraph.linear([2.0, 5.0])
    G = g.generator()
    assert G[0, 0] == pytest.approx(-2.0)
    assert G[1, 1] == pytest.approx(-5.0)
    assert G[1, 0] == pytest.approx(2.0)
    assert G[0, 1] == pytest.approx(0.0)


def test_generator_branching_rows():
    fractions = ((0.0, 0.6, 0.3), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    g = DecayGraph.branching((1.0, 0.5, 0.25), fractions, names=["P", "D1", "D2"])
    assert g.is_branched
    G = g.generator()
    assert G[0, 0] == pytest.approx(-1.0)
    assert G[1, 0] == pytest.approx(0.6)
    assert G[2, 0] == pytest.approx(0.3)


def test_stable_terminal_lambda_zero_allowed():
    g = DecayGraph.linear([1.0, 0.0], names=["A", "stable"])
    assert g.lambdas[1] == 0.0


def test_lambda_zero_on_nonterminal_rejected():
    fractions = ((1.0, 0.0), (0.0, 0.0))
    with pytest.raises(ChainDefinitionError, match="terminal"):
        DecayGraph.branching((0.0, 1.0), fractions)


def test_negative_lambda_rejected():
    with pytest.raises(ChainDefinitionError):
        DecayGraph.linear([-1.0])


def test_branching_fraction_sum_over_one_rejected():
    with pytest.raises(ChainDefinitionError, match="sum"):
        DecayGraph.branching(
            (1.0, 1.0, 1.0),
            ((0.0, 0.7, 0.7), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
        )


def test_mismatched_lengths_rejected():
    with pytest.raises(ChainDefinitionError):
        DecayGraph.linear([1.0], names=["A", "B"])


def test_empty_rejected():
    with pytest.raises(ChainDefinitionError):
        DecayGraph.linear([])


def test_min_separation():
    assert DecayGraph.linear([0.6931, 0.6932]).min_separation() == pytest.approx(1e-4)
    assert DecayGraph.linear([5.0]).min_separation() == float("inf")


def test_generator_dtype_and_shape():
    g = DecayGraph.linear([1.0, 2.0, 3.0])
    G = g.generator()
    assert G.shape == (3, 3)
    assert G.dtype == np.float64
    assert np.all(np.diag(G) <= 0)
