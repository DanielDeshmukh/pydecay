"""Narrow-beam photon shielding: HVL/TVL, Beer-Lambert transmission, layers.

Attenuation follows the Beer-Lambert law ``I = I0 * exp(-mu * x)`` with
``mu`` from :mod:`pydecay.materials` (NIST XCOM, see that module's
docstring) in m^-1 and thicknesses in m. Half-value and tenth-value
layers are ``ln2/mu`` and ``ln10/mu``. All functions are pure-SI floats
(no pint). Broad-beam buildup factors are deferred to v0.7.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from pydecay.materials import material as _registry_lookup


def _validate_mu(mu: float) -> float:
    """Return ``mu`` if it is finite and positive, else raise ValueError."""
    if not math.isfinite(mu) or mu <= 0:
        raise ValueError(f"mu must be finite and > 0, got {mu!r}")
    return mu


def _validate_x(x: float) -> float:
    """Return ``x`` if it is finite and non-negative, else raise ValueError."""
    if not math.isfinite(x) or x < 0:
        raise ValueError(f"thickness must be finite and >= 0, got {x!r}")
    return x


def mu_from_material(material: str, energy_MeV: float) -> float:
    """Return the linear attenuation coefficient ``mu`` in m^-1.

    Args:
        material: Registered material name (see
            :func:`pydecay.materials.available_materials`).
        energy_MeV: Photon energy in MeV within the table span.

    Returns:
        Linear attenuation coefficient in m^-1.

    Raises:
        MaterialError: If the material name is unknown or the energy is
            outside the table span.
    """
    return _registry_lookup(material).mu(energy_MeV)


def hvl(mu: float) -> float:
    """Return the half-value layer in m: ``ln2 / mu``.

    Args:
        mu: Linear attenuation coefficient in m^-1.

    Returns:
        Thickness that halves intensity, in m.

    Raises:
        ValueError: If ``mu`` is not finite and positive.
    """
    return math.log(2.0) / _validate_mu(mu)


def tvl(mu: float) -> float:
    """Return the tenth-value layer in m: ``ln10 / mu``.

    Args:
        mu: Linear attenuation coefficient in m^-1.

    Returns:
        Thickness that reduces intensity tenfold, in m.

    Raises:
        ValueError: If ``mu`` is not finite and positive.
    """
    return math.log(10.0) / _validate_mu(mu)


def hvl_slab(material: str, energy_MeV: float) -> float:
    """Return the half-value layer in m for a material at an energy.

    Args:
        material: Registered material name.
        energy_MeV: Photon energy in MeV.

    Returns:
        Half-value layer thickness in m.

    Raises:
        MaterialError: If the material or energy is unknown/out of range.
    """
    return hvl(mu_from_material(material, energy_MeV))


def tvl_slab(material: str, energy_MeV: float) -> float:
    """Return the tenth-value layer in m for a material at an energy.

    Args:
        material: Registered material name.
        energy_MeV: Photon energy in MeV.

    Returns:
        Tenth-value layer thickness in m.

    Raises:
        MaterialError: If the material or energy is unknown/out of range.
    """
    return tvl(mu_from_material(material, energy_MeV))


def transmit(I0: float, mu: float, x: float, *, buildup: float | None = None) -> float:
    """Return transmitted intensity via narrow-beam Beer-Lambert law.

    Args:
        I0: Incident intensity (any unit; returned value uses the same).
        mu: Linear attenuation coefficient in m^-1.
        x: Shield thickness in m.
        buildup: Reserved for broad-beam buildup factors (v0.7).

    Returns:
        Transmitted intensity.

    Raises:
        NotImplementedError: If ``buildup`` is not ``None``.
        ValueError: If ``mu`` is not finite and positive or ``x`` is
            negative/non-finite.
    """
    if buildup is not None:
        raise NotImplementedError("buildup factors ship in v0.7")
    _validate_mu(mu)
    _validate_x(x)
    return I0 * math.exp(-mu * x)


def transmit_slab(
    I0: float,
    material: str,
    thickness: float,
    energy_MeV: float,
    *,
    buildup: float | None = None,
) -> float:
    """Return transmitted intensity through a single material slab.

    Args:
        I0: Incident intensity.
        material: Registered material name.
        thickness: Shield thickness in m.
        energy_MeV: Photon energy in MeV.
        buildup: Reserved for broad-beam buildup factors (v0.7).

    Returns:
        Transmitted intensity.

    Raises:
        NotImplementedError: If ``buildup`` is not ``None``.
        MaterialError: If the material or energy is unknown/out of range.
        ValueError: If ``thickness`` is negative/non-finite.
    """
    if buildup is not None:
        raise NotImplementedError("buildup factors ship in v0.7")
    mu = mu_from_material(material, energy_MeV)
    return transmit(I0, mu, _validate_x(thickness))


def multilayer_transmit(
    I0: float,
    layers: Sequence[tuple[str, float]],
    energy_MeV: float,
) -> float:
    """Return transmitted intensity through stacked slabs (product of exps).

    Each layer contributes ``exp(-mu_i * x_i)`` at ``energy_MeV``; layer
    order does not matter for pure attenuation.

    Args:
        I0: Incident intensity.
        layers: ``(material_name, thickness_m)`` pairs in stack order.
        energy_MeV: Photon energy in MeV.

    Returns:
        Transmitted intensity.

    Raises:
        MaterialError: If any material name or the energy is unknown.
        ValueError: If any thickness is negative/non-finite.
    """
    result = I0
    for layer_name, thickness in layers:
        result = transmit_slab(result, layer_name, thickness, energy_MeV)
    return result
