"""Tests for unit parsing, conversion, and output mirroring."""

import math

import pint
import pytest

from pydecay.exceptions import InvalidHalfLifeError, InvalidTimeError, UnitError
from pydecay.units import (
    AVOGADRO_PER_MOL,
    CI_IN_BQ,
    atoms_to_grams,
    bq_to_ci,
    ci_to_bq,
    grams_to_atoms,
    mirror_quantity,
    to_float,
    to_half_life_seconds,
    to_seconds,
    ureg,
)


def test_to_seconds_plain_float_is_passthrough():
    assert to_seconds(90.0) == 90.0


def test_to_seconds_string():
    assert to_seconds("8.02 days") == pytest.approx(8.02 * 86400.0)
    assert to_seconds("2 hours") == 7200.0


def test_to_seconds_pint_quantity():
    assert to_seconds(2 * ureg.hour) == 7200.0
    assert to_seconds(ureg.Quantity(30, "minute")) == 1800.0


def test_to_seconds_rejects_negative():
    with pytest.raises(InvalidTimeError, match=">= 0"):
        to_seconds(-1.0)


def test_to_seconds_rejects_nonfinite():
    with pytest.raises(InvalidTimeError, match="finite"):
        to_seconds(math.nan)


def test_to_seconds_rejects_wrong_dimension():
    with pytest.raises(UnitError):
        to_seconds(5 * ureg.meter)


def test_to_seconds_rejects_garbage_string():
    with pytest.raises(UnitError):
        to_seconds("not a time")


def test_to_half_life_seconds_rejects_zero_and_negative():
    with pytest.raises(InvalidHalfLifeError):
        to_half_life_seconds(0.0)
    with pytest.raises(InvalidHalfLifeError):
        to_half_life_seconds("0 days")


def test_to_float_dimension_check():
    assert to_float(5.0, "becquerel") == 5.0
    assert to_float(1 * ureg.Ci, "becquerel") == pytest.approx(CI_IN_BQ)
    with pytest.raises(UnitError):
        to_float(1 * ureg.meter, "second")


def test_mirror_quantity_quantity_in_float_out():
    out = mirror_quantity(500.0, 1 * ureg.becquerel, "becquerel")
    assert isinstance(out, pint.Quantity)
    assert out.magnitude == pytest.approx(500.0)
    plain = mirror_quantity(500.0, 1.0, "becquerel")
    assert isinstance(plain, float)
    assert plain == 500.0


def test_atoms_grams_roundtrip():
    mass_u = 130.9061
    n = 1.0e18
    g = atoms_to_grams(n, mass_u)
    assert g == pytest.approx(n * mass_u / AVOGADRO_PER_MOL)
    assert grams_to_atoms(g, mass_u) == pytest.approx(n, rel=1e-12)


def test_ci_bq_exact_conversion():
    assert ci_to_bq(1.0) == 3.7e10
    assert bq_to_ci(3.7e10) == pytest.approx(1.0)
    assert bq_to_ci(ci_to_bq(2.5)) == pytest.approx(2.5)


def test_atom_unit_is_dimensionless_and_named():
    q = 3.0 * ureg.atom
    assert q.dimensionless
    assert to_float(q, "atom") == 3.0
