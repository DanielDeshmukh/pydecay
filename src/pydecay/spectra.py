"""Optional radiation spectra access (ICRP-107 RAD/BET)."""

from __future__ import annotations

from typing import Any

from pydecay.data import load_bet_for, load_rad_for
from pydecay.exceptions import DataFormatError, NuclideNotFoundError
from pydecay.nuclide import Nuclide, normalize_nuclide_name


def emissions(name: str) -> list[dict[str, Any]]:
    """Return ICRP-107 RAD emission rows for ``name``.

    Args:
        name: Nuclide name (e.g. ``I-131``, ``Tc-99m``).

    Returns:
        List of emission dicts with ``E_MeV``, ``prob``, ``code_AN``, etc.

    Raises:
        NuclideNotFoundError: If the nuclide is not in the catalog or has no RAD rows.
        DataFormatError: If the name cannot be normalized.
    """
    norm = normalize_nuclide_name(name)
    try:
        Nuclide.load(norm)
    except NuclideNotFoundError:
        raise
    try:
        rows = load_rad_for(norm)
    except NuclideNotFoundError as exc:
        raise DataFormatError(str(exc)) from exc
    if not rows:
        raise DataFormatError(f"no emissions for {norm}")
    return rows


def beta_spectrum(name: str) -> tuple[list[float], list[float]]:
    """Return the ICRP-107 beta spectrum for ``name`` as ``(E_MeV, A)``.

    Args:
        name: Nuclide name (e.g. ``Sr-90``).

    Returns:
        Tuple of energy list (MeV) and amplitude list of equal length.

    Raises:
        NuclideNotFoundError: If the nuclide is not in the catalog.
        DataFormatError: If the name cannot be normalized or no BET rows exist.
    """
    norm = normalize_nuclide_name(name)
    Nuclide.load(norm)  # raises if unknown
    try:
        payload = load_bet_for(norm)
    except NuclideNotFoundError as exc:
        raise DataFormatError(str(exc)) from exc
    return list(payload["E_MeV"]), list(payload["A"])
