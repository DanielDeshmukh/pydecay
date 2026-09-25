"""Shielding material registry with NIST-backed ``mu(E)`` interpolation.

Mass attenuation coefficients ``mu/rho`` (cm^2/g, total with coherent
scattering) are bundled from the NIST XCOM photon cross-sections database
(https://physics.nist.gov/PhysRefData/Xcom/html/xcom1.html) for seven
materials across 45 log-spaced energies spanning 0.01-20 MeV; see
``src/pydecay/data/_fetch_nist.py`` for endpoint details, composition
sources (NIST X-Ray Mass Attenuation Coefficients, Table 2) and the
SHA-256-pinned raw responses. Densities (g/cm^3, metadata only - ``mu/rho``
itself is density independent) are stored with the payload: lead 11.35,
iron 7.87, water 1.00, concrete 2.30, aluminum 2.699, air 1.205e-3
(20 C, 1 atm), polyethylene 0.94.

Interpolation is linear in ``(log E, log mu/rho)``; exact node hits return
the table values. Energies outside the table span raise
:class:`~pydecay.exceptions.MaterialError` (no silent clamping).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import numpy as np

from pydecay._dose_data import load_nist_mu
from pydecay.exceptions import DataFormatError, MaterialError


class Material:
    """A shielding material with interpolated photon attenuation.

    Attributes:
        name: Normalized (lowercase) material name.
        density_g_cm3: Density in g/cm^3 from the bundled payload.
    """

    __slots__ = ("_e_max", "_e_min", "_log_e", "_log_mu", "density_g_cm3", "name")

    def __init__(
        self,
        name: str,
        density_g_cm3: float,
        energies: list[float],
        mus: list[float],
    ) -> None:
        """Build a material from raw table rows (validated eagerly).

        Args:
            name: Normalized material name.
            density_g_cm3: Density in g/cm^3.
            energies: Table energies in MeV (strictly increasing).
            mus: Table ``mu/rho`` values in cm^2/g (positive, finite).

        Raises:
            DataFormatError: On length, ordering, or value violations.
        """
        if len(energies) != len(mus) or not energies:
            raise DataFormatError(
                f"material {name!r}: E_MeV/mu_over_rho must be equal-length non-empty lists"
            )
        if (
            not isinstance(density_g_cm3, float)
            or not np.isfinite(density_g_cm3)
            or density_g_cm3 <= 0
        ):
            raise DataFormatError(
                f"material {name!r}: density_g_cm3 must be finite and > 0"
            )
        log_e = np.log(np.asarray(energies, dtype=float))
        log_mu = np.log(np.asarray(mus, dtype=float))
        if np.any(np.diff(log_e) <= 0):
            raise DataFormatError(
                f"material {name!r}: energies must be strictly increasing"
            )
        if not np.all(np.isfinite(log_mu)):
            raise DataFormatError(
                f"material {name!r}: mu_over_rho values must be positive and finite"
            )
        self.name = name
        self.density_g_cm3 = density_g_cm3
        self._log_e = log_e
        self._log_mu = log_mu
        self._e_min = float(energies[0])
        self._e_max = float(energies[-1])

    def mu_over_rho(self, energy_MeV: float) -> float:
        """Return ``mu/rho`` in cm^2/g at ``energy_MeV`` via log-log interpolation.

        Args:
            energy_MeV: Photon energy in MeV; must lie within the table span.

        Returns:
            Mass attenuation coefficient in cm^2/g.

        Raises:
            MaterialError: If ``energy_MeV`` is outside the table span or
                not a finite number.
        """
        try:
            energy = float(energy_MeV)
        except (TypeError, ValueError) as exc:
            raise MaterialError(f"energy must be a number, got {energy_MeV!r}") from exc
        if not np.isfinite(energy) or energy < self._e_min or energy > self._e_max:
            raise MaterialError(
                f"{self.name}: energy {energy!r} MeV outside table range "
                f"[{self._e_min}, {self._e_max}] MeV"
            )
        return float(np.exp(np.interp(np.log(energy), self._log_e, self._log_mu)))

    def mu(self, energy_MeV: float) -> float:
        """Return the linear attenuation coefficient ``mu`` in m^-1.

        Converts ``mu/rho`` (cm^2/g) times density (g/cm^3) to SI: the
        cm^-1 result is multiplied by 100.

        Args:
            energy_MeV: Photon energy in MeV within the table span.

        Returns:
            Linear attenuation coefficient in m^-1.

        Raises:
            MaterialError: If the energy is outside the table span.
        """
        return self.mu_over_rho(energy_MeV) * self.density_g_cm3 * 100.0


@lru_cache(maxsize=1)
def _registry() -> dict[str, Material]:
    """Build the lowercase-name registry from the bundled payload, cached."""
    payload = load_nist_mu()
    materials: dict[str, Any] = payload["materials"]
    registry: dict[str, Material] = {}
    for raw_name, entry in materials.items():
        try:
            registry[raw_name.lower()] = Material(
                name=raw_name.lower(),
                density_g_cm3=float(entry["density_g_cm3"]),
                energies=list(entry["E_MeV"]),
                mus=list(entry["mu_over_rho"]),
            )
        except KeyError as exc:
            raise DataFormatError(f"material {raw_name!r} missing key {exc}") from exc
    return registry


def available_materials() -> tuple[str, ...]:
    """Return the sorted tuple of registered material names."""
    return tuple(sorted(_registry()))


def material(name: str) -> Material:
    """Look up a shielding material by case-insensitive name.

    Args:
        name: Material name, e.g. ``"lead"`` or ``"Water"``.

    Returns:
        The registered :class:`Material`.

    Raises:
        MaterialError: If ``name`` is not a registered material.
    """
    try:
        normalized = name.lower()
    except AttributeError as exc:
        raise MaterialError(f"material name must be a string, got {name!r}") from exc
    found = _registry().get(normalized)
    if found is None:
        raise MaterialError(
            f"unknown material {name!r}; available: {', '.join(available_materials())}"
        )
    return found
