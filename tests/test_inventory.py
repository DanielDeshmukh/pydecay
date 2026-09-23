"""Tests for Inventory construction, closure, decay, and accessors."""

import math

import pint
import pytest

from pydecay import inventory as inventory_mod
from pydecay.exceptions import (
    ChainDefinitionError,
    DataFormatError,
    InvalidTimeError,
    NuclideNotFoundError,
    UnitError,
)
from pydecay.inventory import Inventory
from pydecay.nuclide import Nuclide, normalize_nuclide_name
from pydecay.units import AVOGADRO_PER_MOL, CI_IN_BQ, ureg


def test_construct_default_bq_single():
    nuc = Nuclide.load("Co-60")
    inv = Inventory({"Co-60": 1.0e6})
    assert inv.units == "Bq"
    assert inv.seeds == ("Co-60",)
    assert inv.numbers()["Co-60"] == pytest.approx(1.0e6 / nuc.lambda_, rel=1e-12)


def test_construct_units_atoms():
    inv = Inventory({"Co-60": 42.0}, units="atoms")
    assert inv.numbers()["Co-60"] == 42.0
    inv2 = Inventory({"Co-60": 42.0}, units="atom")
    assert inv2.numbers()["Co-60"] == 42.0


def test_construct_units_ci():
    nuc = Nuclide.load("Co-60")
    inv = Inventory({"Co-60": 1.0}, units="Ci")
    assert inv.numbers()["Co-60"] == pytest.approx(CI_IN_BQ / nuc.lambda_, rel=1e-12)


def test_construct_units_grams_one_atom():
    nuc = Nuclide.load("Co-60")
    one_atom_g = nuc.atomic_mass_u / AVOGADRO_PER_MOL
    inv = Inventory({"Co-60": one_atom_g}, units="g")
    assert inv.numbers()["Co-60"] == pytest.approx(1.0, rel=1e-9)
    inv2 = Inventory({"Co-60": one_atom_g}, units="gram")
    assert inv2.numbers()["Co-60"] == pytest.approx(1.0, rel=1e-9)


def test_construct_quantity_bq_mirrors_kind():
    nuc = Nuclide.load("Co-60")
    inv = Inventory({"Co-60": 1.0e6 * ureg.becquerel}, units="Bq")
    nums = inv.numbers()
    assert isinstance(nums["Co-60"], pint.Quantity)
    assert nums["Co-60"].to("atom").magnitude == pytest.approx(1.0e6 / nuc.lambda_, rel=1e-12)
    acts = inv.activities()
    assert isinstance(acts["Co-60"], pint.Quantity)
    assert acts["Co-60"].to("becquerel").magnitude == pytest.approx(1.0e6, rel=1e-12)


def test_construct_quantity_mismatched_units_rejected():
    with pytest.raises(UnitError):
        Inventory({"Co-60": 1.0 * ureg.kilogram}, units="Bq")
    with pytest.raises(UnitError):
        Inventory({"Co-60": 1.0 * ureg.becquerel}, units="atoms")


def test_construct_bad_units_string():
    with pytest.raises(UnitError, match="unsupported units"):
        Inventory({"Co-60": 1.0}, units="banana")
    with pytest.raises(UnitError, match="units must be a string"):
        Inventory({"Co-60": 1.0}, units=1)  # type: ignore[arg-type]


def test_construct_negative_amount():
    with pytest.raises(UnitError, match="finite and >= 0"):
        Inventory({"Co-60": -1.0}, units="Bq")


def test_construct_nonfinite_amount():
    with pytest.raises(UnitError, match="finite and >= 0"):
        Inventory({"Co-60": math.inf}, units="Bq")
    with pytest.raises(UnitError, match="finite and >= 0"):
        Inventory({"Co-60": math.nan}, units="atoms")


def test_construct_string_amount_rejected():
    with pytest.raises(UnitError, match="number or Quantity"):
        Inventory({"Co-60": "1e6"}, units="Bq")


def test_construct_unknown_nuclide():
    with pytest.raises(NuclideNotFoundError):
        Inventory({"Xx-999": 1.0}, units="atoms")


def test_construct_bad_name():
    with pytest.raises(DataFormatError):
        Inventory({"not a nuclide": 1.0}, units="atoms")


def test_construct_empty_contents():
    with pytest.raises(ChainDefinitionError, match="at least one"):
        Inventory({}, units="atoms")


def test_construct_duplicate_after_normalize():
    with pytest.raises(ChainDefinitionError, match="duplicate"):
        Inventory({"I-131": 1.0, "i131": 2.0}, units="atoms")


def test_construct_non_mapping_contents():
    with pytest.raises(ChainDefinitionError, match="mapping"):
        Inventory([("I-131", 1.0)], units="atoms")  # type: ignore[arg-type]


def test_construct_non_string_key():
    with pytest.raises(ChainDefinitionError, match="keys"):
        Inventory({1: 1.0}, units="atoms")  # type: ignore[dict-item]


def test_stable_seed_activity_rejected_atoms_ok():
    with pytest.raises(UnitError, match="stable"):
        Inventory({"Pb-206": 1.0e6}, units="Bq")
    inv = Inventory({"Pb-206": 1.0e6}, units="atoms")
    assert inv.numbers()["Pb-206"] == 1.0e6
    assert inv.activities()["Pb-206"] == 0.0


def test_closure_mo99_includes_daughters():
    inv = Inventory({"Mo-99": 1.0e18}, units="atoms")
    assert inv.seeds == ("Mo-99",)
    assert {"Mo-99", "Tc-99m", "Tc-99"} <= set(inv.names)
    assert inv.names[0] == "Mo-99"
    assert inv.n_species == len(inv.names)
    assert inv.numbers()["Tc-99m"] == 0.0
    assert inv.numbers()["Mo-99"] == 1.0e18


def test_closure_i131_diamond_shared_daughter():
    inv = Inventory({"I-131": 1.0e18}, units="atoms")
    assert inv.names == ("I-131", "Xe-131m", "Xe-131")
    assert inv.n_species == 3
    assert inv.names.count("Xe-131") == 1


def test_multi_seed_union_closure():
    inv = Inventory({"Sr-90": 1.0e6, "I-131": 2.0e6}, units="atoms")
    assert inv.seeds == ("Sr-90", "I-131")
    assert {"Sr-90", "Y-90", "Zr-90"} <= set(inv.names)
    assert {"I-131", "Xe-131m", "Xe-131"} <= set(inv.names)
    assert inv.numbers()["Sr-90"] == 1.0e6
    assert inv.numbers()["I-131"] == 2.0e6


def test_decay_is_immutable():
    inv = Inventory({"Co-60": 1.0e18}, units="atoms")
    before = inv.numbers()["Co-60"]
    _ = inv.decay(1.0e9)
    assert inv.numbers()["Co-60"] == before


def test_decay_zero_matches_initial():
    inv = Inventory({"I-131": 1.0e18, "Xe-131m": 5.0}, units="atoms")
    out = inv.decay(0.0).numbers()
    for name, val in inv.numbers().items():
        assert out[name] == pytest.approx(val, rel=0, abs=0)


def test_decay_composition_tolerance():
    inv = Inventory({"I-131": 1.0e18}, units="atoms")
    t1, t2 = 1.0e4, 5.0e4
    direct = inv.decay(t1 + t2).numbers()
    stepwise = inv.decay(t1).decay(t2).numbers()
    for name in direct:
        assert stepwise[name] == pytest.approx(direct[name], rel=1e-9, abs=1e-3)


def test_decay_negative_time_rejected():
    inv = Inventory({"Co-60": 1.0}, units="atoms")
    with pytest.raises(InvalidTimeError):
        inv.decay(-1.0)


def test_decay_preserves_units_and_quantity_kind():
    inv = Inventory({"Co-60": 1.0e6 * ureg.becquerel}, units="Bq")
    out = inv.decay("1 days")
    assert out.units == "Bq"
    assert out.seeds == ("Co-60",)
    nums = out.numbers()
    assert isinstance(nums["Co-60"], pint.Quantity)


def test_ingrowth_tc99m_from_mo99():
    inv = Inventory({"Mo-99": 1.0e18}, units="atoms")
    assert inv.numbers()["Tc-99m"] == 0.0
    hl = Nuclide.load("Mo-99").half_life_s
    mid = inv.decay(0.5 * hl)
    assert mid.numbers()["Tc-99m"] > 0.0
    assert mid.numbers()["Mo-99"] < 1.0e18


def test_ingrowth_xe131_from_i131():
    inv = Inventory({"I-131": 1.0e18}, units="atoms")
    hl = Nuclide.load("I-131").half_life_s
    later = inv.decay(hl)
    assert later.numbers()["Xe-131"] > 0.0
    assert later.numbers()["Xe-131m"] > 0.0
    assert later.numbers()["I-131"] == pytest.approx(5.0e17, rel=1e-9)


def test_decay_conservation_sr90_chain():
    inv = Inventory({"Sr-90": 1.0e6}, units="atoms")
    out = inv.decay(1.0e10).numbers()
    assert sum(out.values()) == pytest.approx(1.0e6, rel=1e-9)
    assert out["Zr-90"] > 0.0


def test_cumulative_decays_zero_time():
    inv = Inventory({"Co-60": 1.0e18}, units="atoms")
    cum = inv.cumulative_decays(0.0)
    assert set(cum) == set(inv.names)
    for val in cum.values():
        assert val == 0.0


def test_cumulative_decays_single_isotope_analytic():
    nuc = Nuclide.load("Co-60")
    n0 = 1.0e18
    inv = Inventory({"Co-60": n0}, units="atoms")
    t = 1.0e6
    cum = inv.cumulative_decays(t)
    expected = n0 * (1.0 - math.exp(-nuc.lambda_ * t))
    assert cum["Co-60"] == pytest.approx(expected, rel=1e-9)
    assert cum["Ni-60"] == 0.0


def test_cumulative_decays_stable_is_zero():
    inv = Inventory({"I-131": 1.0e18}, units="atoms")
    cum = inv.cumulative_decays(1.0e6)
    assert cum["Xe-131"] == 0.0
    assert cum["I-131"] > 0.0
    assert cum["Xe-131m"] >= 0.0


def test_cumulative_decays_matches_number_balance():
    inv = Inventory({"Sr-90": 1.0e12}, units="atoms")
    t = 1.0e9
    before = inv.numbers()
    after = inv.decay(t).numbers()
    cum = inv.cumulative_decays(t)
    # Parent lost exactly the atoms it decayed.
    assert before["Sr-90"] - after["Sr-90"] == pytest.approx(cum["Sr-90"], rel=1e-9)
    # Sr-90 -> Y-90 (branch 1.0): growth of Y-90 equals Sr-90 decays minus Y-90 decays.
    assert after["Y-90"] + cum["Y-90"] == pytest.approx(cum["Sr-90"], rel=1e-9)
    # Y-90 -> Zr-90 (branch 1.0, stable): Zr-90 growth equals Y-90 decays.
    assert after["Zr-90"] == pytest.approx(cum["Y-90"], rel=1e-9)
    assert cum["Zr-90"] == 0.0


def test_cumulative_decays_negative_time_rejected():
    inv = Inventory({"Co-60": 1.0}, units="atoms")
    with pytest.raises(InvalidTimeError):
        inv.cumulative_decays(-1.0)


def test_cumulative_decays_covers_full_closure_and_mirrors_kind():
    inv = Inventory({"I-131": 1.0e18 * ureg.atom}, units="atoms")
    cum = inv.cumulative_decays("1 days")
    assert set(cum) == set(inv.names)
    assert isinstance(cum["I-131"], pint.Quantity)
    assert cum["I-131"].to("atom").magnitude > 0.0


def test_accessors_cover_full_closure():
    inv = Inventory({"I-131": 1.0e18}, units="atoms")
    expected = set(inv.names)
    assert set(inv.numbers()) == expected
    assert set(inv.activities()) == expected
    assert set(inv.masses()) == expected
    assert set(inv.half_lives()) == expected


def test_activity_is_lambda_times_n():
    inv = Inventory({"Co-60": 1.0e18}, units="atoms")
    lam = Nuclide.load("Co-60").lambda_
    assert inv.activities()["Co-60"] == pytest.approx(lam * 1.0e18, rel=1e-15)
    assert inv.total_activity() == pytest.approx(lam * 1.0e18, rel=1e-15)


def test_masses_match_atomic_mass():
    nuc = Nuclide.load("Co-60")
    inv = Inventory({"Co-60": 1.0e18}, units="atoms")
    expected = 1.0e18 * nuc.atomic_mass_u / AVOGADRO_PER_MOL
    assert inv.masses()["Co-60"] == pytest.approx(expected, rel=1e-12)


def test_half_lives_stable_is_inf():
    inv = Inventory({"I-131": 1.0}, units="atoms")
    hl = inv.half_lives()
    assert hl["I-131"] == pytest.approx(Nuclide.load("I-131").half_life_s)
    assert math.isinf(hl["Xe-131"])


def test_total_activity_decays_with_parent():
    nuc = Nuclide.load("Co-60")
    inv = Inventory({"Co-60": 1.0e6}, units="Bq")
    assert inv.total_activity() == pytest.approx(1.0e6, rel=1e-12)
    assert inv.decay(nuc.half_life_s).total_activity() == pytest.approx(5.0e5, rel=1e-9)


def test_accessors_mirror_quantity_kind():
    inv = Inventory({"Co-60": 1.0e18 * ureg.atom}, units="atoms")
    assert isinstance(inv.numbers()["Co-60"], pint.Quantity)
    assert isinstance(inv.activities()["Co-60"], pint.Quantity)
    assert isinstance(inv.masses()["Co-60"], pint.Quantity)
    assert inv.total_activity() == pytest.approx(
        Nuclide.load("Co-60").lambda_ * 1.0e18, rel=1e-12
    )


def test_plain_accessors_are_floats():
    inv = Inventory({"Co-60": 1.0e18}, units="atoms")
    assert isinstance(inv.numbers()["Co-60"], float)
    assert isinstance(inv.activities()["Co-60"], float)
    assert isinstance(inv.masses()["Co-60"], float)
    assert isinstance(inv.total_activity(), float)


def test_repr_shows_seeds_only():
    inv = Inventory({"I-131": 1.0, "Sr-90": 2.0}, units="atoms")
    text = repr(inv)
    assert "I-131" in text
    assert "Sr-90" in text
    assert "Xe-131" not in text
    assert "Y-90" not in text


def test_seed_key_normalization():
    inv = Inventory({"i131": 1.0e18}, units="atoms")
    assert inv.seeds == ("I-131",)
    assert normalize_nuclide_name("i131") == "I-131"


def test_progeny_cycle_rejected(monkeypatch):
    good = {
        "half_life_s": 1000.0,
        "atomic_mass_u": 100.0,
        "decay_modes": [{"mode": "beta-minus", "branch": 1.0}],
        "source": "SYNTHETIC TEST RECORD - not real data",
        "source_url": "https://example.invalid/fixture",
        "fetched": "2026-01-01",
    }
    records = {
        "X-1": {**good, "progeny": ["X-2"], "branching": [1.0], "is_stable": False},
        "X-2": {**good, "progeny": ["X-1"], "branching": [1.0], "is_stable": False},
    }

    def fake_load(cls, name):
        norm = normalize_nuclide_name(name)
        if norm not in records:
            raise NuclideNotFoundError(norm)
        return cls.from_record(norm, records[norm])

    monkeypatch.setattr(Nuclide, "load", classmethod(fake_load))
    with pytest.raises(ChainDefinitionError, match="cycle"):
        Inventory({"X-1": 1.0}, units="atoms")


def test_max_closure_depth_rejected(monkeypatch):
    monkeypatch.setattr(inventory_mod, "_MAX_CLOSURE_DEPTH", 1)
    with pytest.raises(ChainDefinitionError, match="max depth"):
        Inventory({"Mo-99": 1.0}, units="atoms")
