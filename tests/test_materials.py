"""Material registry and mu(E) interpolation tests."""

import pytest

from pydecay.exceptions import MaterialError
from pydecay.materials import available_materials, material


def test_available_materials_contains_core_set():
    mats = available_materials()
    for name in ("lead", "water", "concrete", "air"):
        assert name in mats


def test_lead_mu_decreases_in_pair_production_valley():
    pb = material("lead")
    mu_1mev = pb.mu(1.0)
    # above ~4 MeV pair production turns up, but between 1 and ~4 mu falls;
    # assert monotone fall 1.0 -> 3.0 MeV (well-established for Pb)
    mu_3mev = pb.mu(3.0)
    assert mu_1mev > mu_3mev


def test_water_mu_approx_known_value():
    # NIST: H2O total mu/rho at 1 MeV ~ 0.0707 cm^2/g (cross-check tolerance 2%)
    water = material("water")
    assert water.mu_over_rho(1.0) == pytest.approx(0.0707, rel=0.02)


def test_energy_out_of_range_raises():
    with pytest.raises(MaterialError):
        material("lead").mu(0.005)
    with pytest.raises(MaterialError):
        material("lead").mu(25.0)


def test_unknown_material_raises():
    with pytest.raises(MaterialError):
        material("unobtanium")


def test_mu_units_are_per_meter():
    # mu = (mu/rho) * rho; water at 1 MeV ~ 0.0707 cm^2/g * 1 g/cm3 = 0.0707 cm^-1
    # = 7.07 m^-1
    water = material("water")
    assert water.mu(1.0) == pytest.approx(7.07, rel=0.03)
