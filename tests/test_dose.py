"""Dose rate known-value and behavior tests."""

import json
from pathlib import Path

import pytest

from pydecay import _dose_data
from pydecay.dose import R_TO_GY_AIR, air_kerma_rate, dose_rate, exposure_rate, h_star_rate
from pydecay.exceptions import DoseDataError

GOLDEN = json.loads(
    (Path(__file__).parent / "fixtures" / "dose" / "golden_dose_rates.json").read_text(
        encoding="utf-8"
    )
)


def gamma_lookup(nuclide: str) -> float:
    """Thin helper reading dose_coefficients.json in the test."""
    payload = _dose_data.load_dose_coefficients()
    row = payload["rows"].get(nuclide)
    if row is None:
        raise DoseDataError(f"no gamma row for {nuclide!r} in test helper")
    return float(row["gamma_R_cm2_mCi_h"])


@pytest.mark.parametrize("case", GOLDEN["cases"], ids=lambda c: c["id"])
def test_golden_dose_cases(case):
    if "expected_R_h" in case:
        got = exposure_rate(
            gamma_lookup(case["nuclide"]),
            case["activity_Ci"] * 3.7e10,
            case["r_cm"],
        )
        assert got == pytest.approx(case["expected_R_h"], rel=case["rel_tol"])
    else:
        got = dose_rate(case["activity_Bq"], case["nuclide"], case["r_m"])
        assert got == pytest.approx(case["expected_Gy_h"], rel=case["rel_tol"])


def test_dose_rate_unknown_nuclide_raises():
    with pytest.raises(DoseDataError):
        dose_rate(1e6, "Not-123", 1.0)


def test_dose_rate_override_bypasses_table():
    # explicit gamma works for unknown nuclide
    val = dose_rate(3.7e7, "X-1", 1.0, gamma_R_cm2_mCi_h=1.0)
    assert val > 0


def test_omitted_bucket1_nuclide_raises():
    with pytest.raises(DoseDataError):
        dose_rate(1e6, "H-3", 1.0)


def test_distance_scaling_is_inverse_square():
    a = dose_rate(1e6, "Co-60", 1.0)
    b = dose_rate(1e6, "Co-60", 2.0)
    assert b == pytest.approx(a / 4.0)


def test_quantity_ambient_ge_kerma():
    kerma = dose_rate(1e6, "Co-60", 1.0, quantity="kerma")
    ambient = dose_rate(1e6, "Co-60", 1.0, quantity="ambient")
    assert ambient >= kerma


def test_r_to_gy_constant():
    assert R_TO_GY_AIR == pytest.approx(8.76e-3, rel=1e-3)


def test_air_kerma_rate_scales_exposure():
    exp = exposure_rate(12.987, 3.7e7, 1.0)
    assert air_kerma_rate(12.987, 3.7e7, 1.0) == pytest.approx(exp * R_TO_GY_AIR, rel=1e-12)


def test_h_star_rate_matches_ambient_quantity():
    want = dose_rate(1e6, "Co-60", 1.0, quantity="ambient")
    assert h_star_rate(1e6, "Co-60", 1.0) == pytest.approx(want, rel=1e-12)


def test_attenuate_in_air_reduces_rate():
    free = dose_rate(1e6, "Co-60", 1.0)
    att = dose_rate(1e6, "Co-60", 1.0, attenuate_in_air=True)
    assert 0.0 < att < free


def test_invalid_quantity_raises():
    with pytest.raises(ValueError):
        dose_rate(1e6, "Co-60", 1.0, quantity="air")
