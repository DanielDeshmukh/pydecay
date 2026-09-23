"""Tests for Nuclide record validation and properties."""

import json
import math
from pathlib import Path

import pint
import pytest

from pydecay.exceptions import DataFormatError, InvalidTimeError, UnitError
from pydecay.nuclide import DecayMode, Nuclide, normalize_nuclide_name
from pydecay.units import ureg

ICRP_ART = Path(__file__).resolve().parents[1] / "src" / "pydecay" / "data" / "icrp107.json"
SECOND_ISOMERS = ("Bi-212n", "Eu-152n", "Ir-190n", "Ir-192n", "Sb-124n", "Tb-156n")

GOOD_RECORD = {
    "half_life_s": 692256.0,
    "atomic_mass_u": 130.9061,
    "decay_modes": [{"mode": "beta-minus", "branch": 1.0}],
    "source": "SYNTHETIC TEST RECORD - not real data",
    "source_url": "https://example.invalid/fixture",
    "fetched": "2026-01-01",
    "half_life_uncertainty_s": None,
}


def test_normalize_name():
    assert normalize_nuclide_name("i-131") == "I-131"
    assert normalize_nuclide_name("I131") == "I-131"
    assert normalize_nuclide_name("Tc-99m") == "Tc-99m"
    assert normalize_nuclide_name("tc99m") == "Tc-99m"
    with pytest.raises(DataFormatError):
        normalize_nuclide_name("not a nuclide")


def test_normalize_name_accepts_n_suffix():
    assert normalize_nuclide_name("Bi-212n") == "Bi-212n"
    assert normalize_nuclide_name("bi-212n") == "Bi-212n"
    assert normalize_nuclide_name("Bi-212N") == "Bi-212n"
    assert normalize_nuclide_name("bi212n") == "Bi-212n"
    assert normalize_nuclide_name("Tc-99m") == "Tc-99m"
    with pytest.raises(DataFormatError):
        normalize_nuclide_name("Bi-212x")


def test_from_record_ok():
    nuc = Nuclide.from_record("I-131", GOOD_RECORD)
    assert nuc.name == "I-131"
    assert nuc.half_life_s == 692256.0
    assert nuc.decay_modes == (DecayMode(mode="beta-minus", branch=1.0),)
    assert nuc.source.startswith("SYNTHETIC")
    assert nuc.half_life_uncertainty_s is None


@pytest.mark.skipif(not ICRP_ART.exists(), reason="icrp107.json not built yet")
def test_from_record_second_isomers_from_icrp_catalog():
    cat = json.loads(ICRP_ART.read_text(encoding="utf-8"))
    for name in SECOND_ISOMERS:
        assert name in cat, name
        nuc = Nuclide.from_record(name, cat[name])
        assert nuc.name == name
        assert nuc.half_life_s > 0
        assert nuc.decay_modes


def test_from_record_missing_key():
    rec = {k: v for k, v in GOOD_RECORD.items() if k != "source_url"}
    with pytest.raises(DataFormatError, match="source_url"):
        Nuclide.from_record("I-131", rec)


def test_from_record_bad_half_life():
    with pytest.raises(DataFormatError):
        Nuclide.from_record("X-1", {**GOOD_RECORD, "half_life_s": -5.0})
    with pytest.raises(DataFormatError):
        Nuclide.from_record("X-1", {**GOOD_RECORD, "half_life_s": "soon"})


def test_from_record_bad_decay_modes():
    with pytest.raises(DataFormatError):
        Nuclide.from_record("X-1", {**GOOD_RECORD, "decay_modes": "beta"})
    with pytest.raises(DataFormatError):
        Nuclide.from_record("X-1", {**GOOD_RECORD, "decay_modes": [{"mode": "x"}]})


def test_lambda_and_half_life_properties():
    nuc = Nuclide.from_record("I-131", GOOD_RECORD)
    assert nuc.lambda_ == pytest.approx(math.log(2) / 692256.0)
    assert isinstance(nuc.half_life, pint.Quantity)
    assert nuc.half_life.to("second").magnitude == pytest.approx(692256.0)


def test_activity_mirrors_n_and_decays():
    nuc = Nuclide.from_record("I-131", GOOD_RECORD)
    a_plain = nuc.activity(1.0e6, t=0.0)
    assert isinstance(a_plain, float)
    assert a_plain == pytest.approx(nuc.lambda_ * 1.0e6)
    a_t = nuc.activity(1.0e6, t=nuc.half_life_s)
    assert a_t == pytest.approx(a_plain * 0.5, rel=1e-12)
    a_q = nuc.activity(1.0e6 * ureg.atom)
    assert isinstance(a_q, pint.Quantity)
    with pytest.raises(UnitError):
        nuc.activity(1.0 * ureg.meter)
    with pytest.raises(InvalidTimeError):
        nuc.activity(1.0, t=-1.0)
