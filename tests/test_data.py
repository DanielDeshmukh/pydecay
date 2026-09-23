"""Tests for the bundled ICRP-107 dataset (spec sections 6, 9)."""

import math

import pytest

from pydecay.exceptions import NuclideNotFoundError
from pydecay.nuclide import Nuclide

MANDATORY = ["Co-60", "Cs-137", "I-131", "C-14", "U-238", "Tc-99m"]


@pytest.fixture(scope="module")
def all_nuclides():
    return Nuclide.load_all()


def test_catalog_is_full_icrp_scale(all_nuclides):
    radioactive = {k: v for k, v in all_nuclides.items() if math.isfinite(v.half_life_s)}
    assert len(radioactive) >= 1252


def test_mandatory_six_present(all_nuclides):
    for name in MANDATORY:
        assert name in all_nuclides


def test_every_record_is_icrp_sourced(all_nuclides):
    for nuc in all_nuclides.values():
        assert "ICRP" in nuc.source or nuc.source.endswith("stable")
        assert "icrp" in nuc.source_url.lower() or "ICRP" in nuc.source


def test_half_lives_positive_or_inf(all_nuclides):
    for nuc in all_nuclides.values():
        assert nuc.half_life_s > 0  # inf > 0
        assert nuc.atomic_mass_u > 0


def test_load_by_name(all_nuclides):
    assert Nuclide.load("i131").name == "I-131"
    assert Nuclide.load("U-238").atomic_mass_u == pytest.approx(238.050788, rel=1e-9)


def test_load_missing_raises():
    with pytest.raises(NuclideNotFoundError):
        Nuclide.load("Xx-999")
