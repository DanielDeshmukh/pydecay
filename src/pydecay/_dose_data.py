"""Cached loader for the bundled NIST XCOM mass-attenuation payload.

Also loads the curated gamma dose-coefficient bundle. ``nist_mu.json.gz`` is
built at data-curation time by ``src/pydecay/data/_fetch_nist.py`` (NIST XCOM
text-form responses, raw file SHA-256 pinned). ``dose_coefficients.json`` is
built by ``src/pydecay/data/_curate_dose.py`` (Task-4 locked values). This
module is the single read point so ``pydecay.materials``, ``pydecay.dose`` and
future consumers share one cached payload.
"""

from __future__ import annotations

import gzip
import json
from functools import lru_cache
from importlib import resources
from typing import Any

from pydecay.exceptions import DataFormatError


@lru_cache(maxsize=1)
def load_nist_mu() -> dict[str, Any]:
    """Return the full NIST mu/rho payload, cached.

    Payload shape: ``{"source": ..., "materials": {name: {"density_g_cm3":
    float, "E_MeV": [float, ...], "mu_over_rho": [float, ...]}}}``.

    Returns:
        The parsed payload dict.

    Raises:
        DataFormatError: If the file is missing, corrupt, or not the
            expected object shape.
    """
    try:
        raw = resources.files("pydecay.data").joinpath("nist_mu.json.gz").read_bytes()
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        raise DataFormatError("bundled nist_mu.json.gz not found") from exc
    try:
        data = json.loads(gzip.decompress(raw))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataFormatError("nist_mu.json.gz is corrupt") from exc
    if not isinstance(data, dict) or not isinstance(data.get("materials"), dict):
        raise DataFormatError("nist_mu.json.gz must be a JSON object with a materials object")
    return data


@lru_cache(maxsize=1)
def load_dose_coefficients() -> dict[str, Any]:
    """Return the curated dose-coefficient payload, cached.

    Payload shape: ``{"rows": {nuclide: {"gamma_R_cm2_mCi_h": float, ...
    "source": str}}, "omitted": {nuclide: reason}, "h_star_over_ka":
    {"E_MeV": [...], "factor": [...], "source": str}, ...}``.

    Returns:
        The parsed payload dict.

    Raises:
        DataFormatError: If the file is missing, corrupt, or not the
            expected object shape.
    """
    try:
        raw = resources.files("pydecay.data").joinpath("dose_coefficients.json").read_bytes()
    except (FileNotFoundError, ModuleNotFoundError) as exc:
        raise DataFormatError("bundled dose_coefficients.json not found") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DataFormatError("dose_coefficients.json is corrupt") from exc
    if not isinstance(data, dict) or not isinstance(data.get("rows"), dict):
        raise DataFormatError("dose_coefficients.json must be a JSON object with a rows object")
    ks = data.get("h_star_over_ka")
    if not isinstance(ks, dict) or not isinstance(ks.get("E_MeV"), list):
        raise DataFormatError("dose_coefficients.json must include an h_star_over_ka object")
    return data
