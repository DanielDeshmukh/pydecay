"""Point-source exposure, air-kerma, and ambient dose rates (pure SI).

Conventions locked by ``tests/test_dose.py`` golden cases:

* ``gamma_R_cm2_mCi_h`` is a true R.cm2.mCi-1.h-1 constant, so
  ``exposure_rate(g, A_Bq, r_cm) = g * (A_Bq / 3.7e7) / r_cm**2``.
* 1 roentgen in air = 8.76e-3 Gy (``R_TO_GY_AIR``).
* ``quantity="ambient"`` multiplies the air-kerma rate by the bundled
  ICRP-74 H*(10)/Ka factor, interpolated at 1.25 MeV (the plan-sanctioned
  default energy for the ambient path; per-nuclide max-gamma interpolation
  is deferred until photon line lists are bundled).

Gamma coefficients come from the curated ``dose_coefficients.json`` bundle
(Task 4); nuclides without photon rows (bucket 1) raise ``DoseDataError``
unless an explicit ``gamma_R_cm2_mCi_h`` override is supplied.
"""

from __future__ import annotations

import math

from pydecay._dose_data import load_dose_coefficients
from pydecay.exceptions import DoseDataError
from pydecay.materials import material

R_TO_GY_AIR = 8.76e-3  # 1 R in air -> Gy (documented conversion)

_BQ_PER_MCI = 3.7e7
_AMBIENT_E_MEV = 1.25


def exposure_rate(gamma_R_cm2_mCi_h: float, activity_Bq: float, r_cm: float) -> float:
    """Return the exposure rate at ``r_cm`` from a point source, in R/h.

    Args:
        gamma_R_cm2_mCi_h: Exposure-rate constant in R.cm2.mCi-1.h-1.
        activity_Bq: Activity in becquerel.
        r_cm: Distance from the point source in centimetres.

    Returns:
        Exposure rate in R/h (inverse-square from the tabulated constant).
    """
    return gamma_R_cm2_mCi_h * (activity_Bq / _BQ_PER_MCI) / (r_cm * r_cm)


def air_kerma_rate(gamma_R_cm2_mCi_h: float, activity_Bq: float, r_cm: float) -> float:
    """Return the air-kerma rate at ``r_cm``, in Gy/h.

    Args:
        gamma_R_cm2_mCi_h: Exposure-rate constant in R.cm2.mCi-1.h-1.
        activity_Bq: Activity in becquerel.
        r_cm: Distance from the point source in centimetres.

    Returns:
        Air-kerma rate in Gy/h (``exposure_rate * R_TO_GY_AIR``).
    """
    return exposure_rate(gamma_R_cm2_mCi_h, activity_Bq, r_cm) * R_TO_GY_AIR


def _h_star_at(energy_mev: float) -> float:
    """Return the bundled H*(10)/Ka factor (Sv/Gy) at ``energy_mev`` (MeV).

    Linear interpolation between tabulated points; clamped at the table ends.
    """
    ks = load_dose_coefficients()["h_star_over_ka"]
    energies: list[float] = ks["E_MeV"]
    factors: list[float] = ks["factor"]
    if energy_mev <= energies[0]:
        return factors[0]
    if energy_mev >= energies[-1]:
        return factors[-1]
    idx = next(i for i in range(1, len(energies)) if energy_mev <= energies[i])
    low_e, high_e = energies[idx - 1], energies[idx]
    low_f, high_f = factors[idx - 1], factors[idx]
    return low_f + (high_f - low_f) * (energy_mev - low_e) / (high_e - low_e)


def dose_rate(
    activity_Bq: float,
    nuclide: str,
    r_m: float = 1.0,
    *,
    quantity: str = "kerma",
    gamma_R_cm2_mCi_h: float | None = None,
    attenuate_in_air: bool = False,
) -> float:
    """Return the point-source dose rate at ``r_m``.

    Args:
        activity_Bq: Activity in becquerel.
        nuclide: Nuclide name looked up in the curated bundle
            (e.g. ``"Co-60"``), ignored when ``gamma_R_cm2_mCi_h`` is given.
        r_m: Distance from the point source in metres.
        quantity: ``"kerma"`` (default, air kerma in Gy/h) or ``"ambient"``
            (ambient dose equivalent in Sv/h).
        gamma_R_cm2_mCi_h: Explicit R.cm2.mCi-1.h-1 override that bypasses
            the table lookup (works for nuclides with no bundled row).
        attenuate_in_air: Multiply by ``exp(-mu_air * r)`` at 1.25 MeV as a
            free-in-air refinement.

    Returns:
        Dose rate in Gy/h (``"kerma"``) or Sv/h (``"ambient"``).

    Raises:
        ValueError: If ``quantity`` is not ``"kerma"`` or ``"ambient"``.
        DoseDataError: If the nuclide has no bundled photon coefficients and
            no explicit override was provided.
    """
    if quantity not in ("kerma", "ambient"):
        raise ValueError(f"quantity must be 'kerma' or 'ambient', got {quantity!r}")
    gamma = gamma_R_cm2_mCi_h
    if gamma is None:
        row = load_dose_coefficients()["rows"].get(nuclide)
        if row is None:
            raise DoseDataError(f"no photon dose coefficients for {nuclide!r}")
        gamma = float(row["gamma_R_cm2_mCi_h"])
    rate = air_kerma_rate(gamma, activity_Bq, r_m * 100.0)
    if attenuate_in_air:
        rate *= math.exp(-material("air").mu(_AMBIENT_E_MEV) * r_m)
    if quantity == "ambient":
        rate *= _h_star_at(_AMBIENT_E_MEV)
    return rate


def h_star_rate(
    activity_Bq: float,
    nuclide: str,
    r_m: float = 1.0,
    *,
    gamma_R_cm2_mCi_h: float | None = None,
    attenuate_in_air: bool = False,
) -> float:
    """Return the ambient dose-equivalent rate at ``r_m``, in Sv/h.

    Args:
        activity_Bq: Activity in becquerel.
        nuclide: Nuclide name looked up in the curated bundle.
        r_m: Distance from the point source in metres.
        gamma_R_cm2_mCi_h: Explicit constant override (see :func:`dose_rate`).
        attenuate_in_air: Apply the ``exp(-mu_air * r)`` refinement.

    Returns:
        Ambient dose-equivalent rate in Sv/h.
    """
    return dose_rate(
        activity_Bq,
        nuclide,
        r_m,
        quantity="ambient",
        gamma_R_cm2_mCi_h=gamma_R_cm2_mCi_h,
        attenuate_in_air=attenuate_in_air,
    )
