"""Tests for the public convenience API (spec section 5)."""

import math

import pint
import pytest

from pydecay import (
    ChainDefinitionError,
    InvalidHalfLifeError,
    InvalidTimeError,
    NuclideNotFoundError,
    PyDecayError,
    UnitError,
    __version__,
    atoms_to_grams,
    bq_to_ci,
    ci_to_bq,
    decay_constant,
    decayed_activity,
    decayed_atoms,
    grams_to_atoms,
    mean_lifetime_s,
    remaining_fraction,
    to_seconds,
)
from pydecay.units import AVOGADRO_PER_MOL, CI_IN_BQ, ureg


def test_decayed_atoms_half_life_identity():
    assert decayed_atoms(N0=1.0e6, half_life="10 days", time="10 days") == pytest.approx(
        5.0e5, rel=1e-12
    )


def test_decayed_atoms_mirrors_n0():
    out = decayed_atoms(N0=1.0e6 * ureg.atom, half_life=8.02 * ureg.day, time=24 * ureg.hour)
    assert isinstance(out, pint.Quantity)
    assert out.magnitude < 1.0e6
    plain = decayed_atoms(N0=1.0e6, half_life=8.02 * ureg.day, time=24 * ureg.hour)
    assert isinstance(plain, float)
    assert plain == pytest.approx(out.magnitude)


def test_decayed_atoms_rejects_string_n0():
    with pytest.raises(UnitError):
        decayed_atoms(N0="many", half_life="8 days", time="1 day")


def test_decayed_activity_one_half_life():
    assert decayed_activity(A0=1000.0, half_life="8.02 days", time="8.02 days") == pytest.approx(
        500.0, rel=1e-12
    )


def test_decayed_activity_five_half_lives():
    assert decayed_activity(
        A0=1000.0, half_life="8.02 days", time=5 * 8.02 * 86400.0
    ) == pytest.approx(31.25, rel=1e-12)


def test_decayed_activity_mirrors_a0():
    out = decayed_activity(A0=1000.0 * ureg.becquerel, half_life="8 days", time="8 days")
    assert isinstance(out, pint.Quantity)
    assert out.to("becquerel").magnitude == pytest.approx(500.0, rel=1e-12)


def test_remaining_fraction_always_float():
    f = remaining_fraction(half_life="8.02 days", time="8.02 days")
    assert isinstance(f, float)
    assert f == pytest.approx(0.5, rel=1e-12)
    fq = remaining_fraction(half_life=8.02 * ureg.day, time=8.02 * ureg.day)
    assert isinstance(fq, float)


def test_errors_surface_from_api():
    with pytest.raises(InvalidHalfLifeError):
        decayed_atoms(N0=1.0, half_life="0 days", time="1 day")
    with pytest.raises(InvalidTimeError):
        decayed_atoms(N0=1.0, half_life="8 days", time="-1 day")
    with pytest.raises(UnitError):
        decayed_atoms(N0=1.0, half_life="8 parsecs", time="1 day")


def test_public_exports():
    import pydecay

    for name in pydecay.__all__:
        assert hasattr(pydecay, name)
    assert __version__ == "0.4.0"
    assert issubclass(NuclideNotFoundError, PyDecayError)
    assert issubclass(ChainDefinitionError, PyDecayError)
    assert "Inventory" in pydecay.__all__
    assert pydecay.Inventory is not None


def test_helper_exports_present_and_callable():
    import pydecay

    for name in (
        "to_seconds",
        "bq_to_ci",
        "ci_to_bq",
        "atoms_to_grams",
        "grams_to_atoms",
        "decay_constant",
        "mean_lifetime_s",
    ):
        assert name in pydecay.__all__
        assert hasattr(pydecay, name)
        assert callable(getattr(pydecay, name))


def test_to_seconds_top_level_float_and_string():
    assert to_seconds(90.0) == 90.0
    assert to_seconds("2 hours") == 7200.0


def test_to_seconds_top_level_pint_and_zero():
    assert to_seconds(2 * ureg.hour) == 7200.0
    assert to_seconds(0) == 0.0


def test_to_seconds_top_level_rejects_negative_and_bad_unit():
    with pytest.raises(InvalidTimeError):
        to_seconds(-1.0)
    with pytest.raises(UnitError):
        to_seconds("not a time")


def test_bq_to_ci_top_level_identity_and_zero():
    assert bq_to_ci(CI_IN_BQ) == pytest.approx(1.0)
    assert bq_to_ci(0.0) == 0.0


def test_bq_to_ci_top_level_known_value_and_roundtrip():
    assert bq_to_ci(3.7e9) == pytest.approx(0.1)
    assert bq_to_ci(ci_to_bq(2.5)) == pytest.approx(2.5)


def test_ci_to_bq_top_level_exact_and_zero():
    assert ci_to_bq(1.0) == 3.7e10
    assert ci_to_bq(0.0) == 0.0


def test_ci_to_bq_top_level_fractional_and_inverse():
    assert ci_to_bq(0.1) == pytest.approx(3.7e9)
    assert ci_to_bq(bq_to_ci(1.234e7)) == pytest.approx(1.234e7)


def test_atoms_to_grams_top_level_formula_and_zero():
    n, mass_u = 1.0e18, 130.9061
    assert atoms_to_grams(n, mass_u) == pytest.approx(n * mass_u / AVOGADRO_PER_MOL)
    assert atoms_to_grams(0.0, mass_u) == 0.0


def test_atoms_to_grams_top_level_roundtrip_with_grams_to_atoms():
    mass_u = 55.9349
    g = atoms_to_grams(6.02214076e23, mass_u)
    assert g == pytest.approx(mass_u, rel=1e-12)
    assert grams_to_atoms(g, mass_u) == pytest.approx(6.02214076e23, rel=1e-12)


def test_grams_to_atoms_top_level_inverse_formula():
    mass_u = 238.0508
    m = 1.0
    assert grams_to_atoms(m, mass_u) == pytest.approx(m * AVOGADRO_PER_MOL / mass_u)
    assert grams_to_atoms(0.0, mass_u) == 0.0


def test_decay_constant_top_level_formula():
    assert decay_constant(8.0) == pytest.approx(math.log(2) / 8.0)
    assert decay_constant(1.0) == pytest.approx(math.log(2))


def test_decay_constant_top_level_rejects_bad_half_life():
    with pytest.raises(InvalidHalfLifeError):
        decay_constant(0.0)
    with pytest.raises(InvalidHalfLifeError):
        decay_constant(-1.0)
    with pytest.raises(InvalidHalfLifeError):
        decay_constant(math.nan)


def test_mean_lifetime_s_top_level_reciprocal_identity():
    lam = math.log(2)
    assert mean_lifetime_s(lam) == pytest.approx(1.0 / lam)
    assert mean_lifetime_s(decay_constant(7.0)) == pytest.approx(7.0 / math.log(2))


def test_mean_lifetime_s_top_level_rejects_bad_lambda():
    with pytest.raises(InvalidHalfLifeError):
        mean_lifetime_s(0.0)
    with pytest.raises(InvalidHalfLifeError):
        mean_lifetime_s(-0.5)
    with pytest.raises(InvalidHalfLifeError):
        mean_lifetime_s(math.inf)


def test_inventory_top_level_export():
    from pydecay import Inventory

    inv = Inventory({"Co-60": 1.0e6}, units="Bq")
    assert inv.seeds == ("Co-60",)
    assert "Ni-60" in inv.names


def test_spectra_exported():
    import pydecay

    assert "emissions" in pydecay.__all__
    assert "beta_spectrum" in pydecay.__all__
    assert callable(pydecay.emissions)
    assert callable(pydecay.beta_spectrum)


def test_remaining_fraction_generic_pattern():
    """Spec 6 example pattern: after n half-lives, fraction is 2**-n."""
    for n in (1, 2, 5, 10):
        frac = remaining_fraction(half_life="1 days", time=n * 86400.0)
        assert frac == pytest.approx(0.5**n, rel=1e-12)
