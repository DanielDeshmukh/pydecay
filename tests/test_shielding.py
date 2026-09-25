"""Narrow-beam shielding identities and multi-layer composition."""

import math

import pytest

from pydecay.exceptions import MaterialError
from pydecay.shielding import (
    hvl,
    hvl_slab,
    multilayer_transmit,
    transmit,
    transmit_slab,
    tvl,
    tvl_slab,
)


def test_transmit_zero_thickness_is_identity():
    assert transmit(100.0, 1.0, 0.0) == pytest.approx(100.0)


def test_hvl_halves_exactly():
    mu = 2.0
    assert transmit(100.0, mu, hvl(mu)) == pytest.approx(50.0)


def test_tvl_tenths_exactly():
    mu = 3.5
    assert transmit(100.0, mu, tvl(mu)) == pytest.approx(10.0)


def test_hvl_tvl_relationship():
    # TVL = ln10/ln2 * HVL ~ 3.3219 HVL
    mu = 4.2
    assert tvl(mu) / hvl(mu) == pytest.approx(math.log(10) / math.log(2))


def test_slab_wrappers_exist_and_obey_ratio():
    # plan ships hvl_slab/tvl_slab without direct tests; assert they are
    # positive finite and keep the same TVL/HVL ratio as the mu-based pair
    h = hvl_slab("lead", 1.25)
    t = tvl_slab("lead", 1.25)
    assert math.isfinite(h) and h > 0.0
    assert t / h == pytest.approx(math.log(10) / math.log(2))


def test_multilayer_equals_single_combined_mu():
    # pure attenuation: product of exps == exp of sum
    # identity checked with raw transmit composition:
    mu_w = 7.0  # synthetic for identity test via transmit, not materials
    a = transmit(1.0, mu_w, 0.5)
    b = transmit(a, 500.0, 0.01)
    assert b == pytest.approx(math.exp(-(mu_w * 0.5 + 500.0 * 0.01)))


def test_multilayer_real_materials_order_independent():
    e = 1.25
    one = multilayer_transmit(1.0, [("lead", 0.01), ("water", 0.5)], e)
    two = multilayer_transmit(1.0, [("water", 0.5), ("lead", 0.01)], e)
    assert one == pytest.approx(two)


def test_transmit_slab_lead_co60_energy_reduces_intensity():
    i0 = 1.0
    out = transmit_slab(i0, "lead", 0.01, 1.25)
    assert 0.0 < out < 1.0


def test_buildup_reserved():
    with pytest.raises(NotImplementedError):
        transmit(1.0, 1.0, 0.1, buildup=2.0)


def test_negative_mu_rejected():
    with pytest.raises(ValueError):
        hvl(0.0)
    with pytest.raises(ValueError):
        hvl(-1.0)


def test_unknown_material_propagates():
    with pytest.raises(MaterialError):
        transmit_slab(1.0, "unobtanium", 0.1, 1.0)
