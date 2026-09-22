"""Spec section 6 worked examples against the bundled IAEA dataset.

Expected values are re-derived from the bundled half-lives themselves —
the reference doc's table is secondary and is NOT the assertion source.
"""

import pytest

from pydecay import Nuclide, decayed_activity, decayed_atoms

MANDATORY_SIX = ["Co-60", "Cs-137", "I-131", "C-14", "U-238", "Tc-99m"]


@pytest.mark.parametrize("name", MANDATORY_SIX)
def test_one_half_life_halves_activity(name):
    nuc = Nuclide.load(name)
    a = decayed_activity(A0=1000.0, half_life=nuc.half_life, time=nuc.half_life)
    assert a == pytest.approx(500.0, rel=1e-12)


@pytest.mark.parametrize("name", MANDATORY_SIX)
def test_five_half_lives_give_2_pow_minus_5(name):
    nuc = Nuclide.load(name)
    a = decayed_activity(A0=1000.0, half_life=nuc.half_life, time=5 * nuc.half_life)
    assert a == pytest.approx(1000.0 * 0.5**5, rel=1e-12)


@pytest.mark.parametrize("name", MANDATORY_SIX)
def test_atoms_halve_over_one_half_life(name):
    nuc = Nuclide.load(name)
    n = decayed_atoms(N0=1.0e9, half_life=nuc.half_life_s, time=nuc.half_life_s)
    assert n == pytest.approx(5.0e8, rel=1e-12)


def test_i131_reference_example_explicit():
    """Spec 6 flagship: 1000 Bq I-131 → 500 Bq after one T½, 31.25 Bq after five."""
    i131 = Nuclide.load("I-131")
    a1 = decayed_activity(A0=1000.0, half_life=i131.half_life, time=i131.half_life)
    a5 = decayed_activity(A0=1000.0, half_life=i131.half_life, time=5 * i131.half_life)
    assert a1 == pytest.approx(500.0, rel=1e-12)
    assert a5 == pytest.approx(31.25, rel=1e-12)


def test_bundled_half_life_order_of_magnitude_sanity():
    """Ballpark check (catches fetch-parser unit-scaling bugs, e.g. years→days)."""
    expectations = {
        "Co-60": (4.0, 6.0, "y"),
        "Cs-137": (28.0, 32.0, "y"),
        "I-131": (7.5, 8.5, "d"),
        "C-14": (5000.0, 6000.0, "y"),
        "U-238": (4.0e9, 5.0e9, "y"),
        "Tc-99m": (5.5, 6.5, "h"),
    }
    unit_s = {"y": 31557600.0, "d": 86400.0, "h": 3600.0}
    for name, (lo, hi, unit) in expectations.items():
        hl = Nuclide.load(name).half_life_s
        assert lo * unit_s[unit] <= hl <= hi * unit_s[unit], f"{name} half-life {hl}s out of range"
