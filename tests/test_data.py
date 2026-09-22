"""Tests for the bundled IAEA dataset (schema + provenance + mandatory six)."""

import datetime

import pytest

from pydecay.exceptions import NuclideNotFoundError
from pydecay.nuclide import Nuclide

MANDATORY = ["Co-60", "Cs-137", "I-131", "C-14", "U-238", "Tc-99m"]


@pytest.fixture(scope="module")
def all_nuclides():
    return Nuclide.load_all()


def test_dataset_is_nonempty_and_reasonably_sized(all_nuclides):
    assert len(all_nuclides) >= 30


def test_mandatory_six_present(all_nuclides):
    for name in MANDATORY:
        assert name in all_nuclides, f"missing mandatory isotope {name}"


def test_every_record_has_provenance(all_nuclides):
    for nuc in all_nuclides.values():
        assert "IAEA" in nuc.source
        assert "nds.iaea.org" in nuc.source_url
        datetime.date.fromisoformat(nuc.fetched)


def test_every_half_life_positive(all_nuclides):
    for nuc in all_nuclides.values():
        assert nuc.half_life_s > 0
        assert nuc.atomic_mass_u > 0


def test_load_by_name(all_nuclides):
    i131 = Nuclide.load("I-131")
    assert i131.half_life_s == pytest.approx(all_nuclides["I-131"].half_life_s)
    assert Nuclide.load("i131").name == "I-131"


def test_load_missing_raises():
    with pytest.raises(NuclideNotFoundError):
        Nuclide.load("Xx-999")
