"""Tests for the DecayChain domain object (spec sections 2 and 5)."""

import math

import pint
import pytest

from pydecay.chain import DecayChain
from pydecay.exceptions import ChainDefinitionError, InvalidTimeError, NuclideNotFoundError
from pydecay.nuclide import Nuclide
from pydecay.units import ureg


def test_explicit_linear_chain_floats():
    chain = DecayChain([0.6931, 0.6932], names=["A", "B"])
    assert chain.names == ("A", "B")
    out = chain.at(t=1.0)
    assert set(out) == {"A", "B"}
    assert isinstance(out["A"], float)
    assert out["A"] == pytest.approx(math.exp(-0.6931), rel=1e-6)


def test_t_string_parses_via_pint():
    chain = DecayChain([math.log(2) / 86400.0], names=["day_isotope"])
    out = chain.at(t="1 days")
    assert out["day_isotope"] == pytest.approx(0.5, rel=1e-12)


def test_default_ic_is_parent_only_unit():
    chain = DecayChain([1.0, 0.5], names=["P", "D"])
    assert chain.at(t=0) == {"P": 1.0, "D": 0.0}


def test_n0_mapping_by_name():
    chain = DecayChain([1.0, 0.5], names=["P", "D"])
    out = chain.at(t=0, n0={"P": 42.0, "D": 7.0})
    assert out == {"P": 42.0, "D": 7.0}
    with pytest.raises(ChainDefinitionError, match="unknown"):
        chain.at(t=0, n0={"Nope": 1.0})


def test_pint_inputs_return_pint():
    chain = DecayChain([1.0, 0.5], names=["P", "D"])
    n0 = {"P": 1.0e6 * ureg.atom, "D": 0.0 * ureg.atom}
    out = chain.at(t=1.0 * ureg.second, n0=n0)
    assert isinstance(out["P"], pint.Quantity)
    assert out["P"].dimensionless
    assert out["P"].magnitude > 0


def test_activity_is_lambda_times_n():
    lam = (math.log(2) / 3600.0, 1.0e-4)
    chain = DecayChain(lam, names=["A", "B"])
    n0 = {"A": 1.0e9, "B": 0.0}
    atoms = chain.at(t=100.0, n0=n0)
    acts = chain.activity(t=100.0, n0=n0)
    assert acts["A"] == pytest.approx(lam[0] * atoms["A"], rel=1e-15)


def test_from_isotopes_uses_bundled_data():
    chain = DecayChain.from_isotopes(["Sr-90", "Y-90"])
    assert chain.names == ("Sr-90", "Y-90")
    assert chain.lambdas[0] == pytest.approx(Nuclide.load("Sr-90").lambda_)


def test_from_isotopes_unknown_nuclide():
    with pytest.raises(NuclideNotFoundError):
        DecayChain.from_isotopes(["Xx-999"])


def test_branching_explicit_lambdas():
    chain = DecayChain.branching(
        parent="P",
        branches={"D1": 0.6, "D2": 0.3},
        lambdas={"P": 0.7, "D1": 1.0e-5, "D2": 2.0e-5},
    )
    assert chain.names == ("P", "D1", "D2")
    out = chain.at(t=0.0, n0={"P": 1.0, "D1": 0.0, "D2": 0.0})
    assert out["P"] == 1.0


def test_branching_fraction_sum_over_one_rejected():
    with pytest.raises(ChainDefinitionError):
        DecayChain.branching(
            parent="P",
            branches={"D1": 0.7, "D2": 0.7},
            lambdas={"P": 1.0, "D1": 1.0, "D2": 1.0},
        )


def test_branching_missing_lambda_rejected():
    with pytest.raises(ChainDefinitionError, match="half-life"):
        DecayChain.branching(parent="P", branches={"D1": 0.5}, lambdas={"P": 1.0})


def test_negative_time_rejected():
    chain = DecayChain([1.0], names=["A"])
    with pytest.raises(InvalidTimeError):
        chain.at(t=-1.0)


def test_conservation_through_public_api():
    chain = DecayChain([0.5, 0.0], names=["A", "stable"])
    out = chain.at(t=100.0, n0={"A": 6.0, "stable": 0.0})
    assert out["A"] + out["stable"] == pytest.approx(6.0, rel=1e-12)
