"""Tests for the public convenience API (spec section 5)."""

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
    decayed_activity,
    decayed_atoms,
    remaining_fraction,
)
from pydecay.units import ureg


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
    assert __version__ == "0.1.0"
    assert issubclass(NuclideNotFoundError, PyDecayError)
    assert issubclass(ChainDefinitionError, PyDecayError)


def test_remaining_fraction_generic_pattern():
    """Spec 6 example pattern: after n half-lives, fraction is 2**-n."""
    for n in (1, 2, 5, 10):
        frac = remaining_fraction(half_life="1 days", time=n * 86400.0)
        assert frac == pytest.approx(0.5**n, rel=1e-12)
