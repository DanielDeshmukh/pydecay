"""Bundled data files for pydecay with cached catalog and lazy spectra loaders."""

from __future__ import annotations

import gzip
import json
from functools import lru_cache
from importlib import resources
from typing import Any, cast

from pydecay.exceptions import DataFormatError, NuclideNotFoundError
from pydecay.nuclide import normalize_nuclide_name


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    """Return the full ICRP-107 catalog (nuclide name → record), cached."""
    text = resources.files("pydecay.data").joinpath("icrp107.json").read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise DataFormatError("icrp107.json must be a JSON object")
    return data


@lru_cache(maxsize=1)
def load_rad() -> dict[str, Any]:
    """Return the full RAD payload ``{"codes": [...], "emissions": {...}}``, cached."""
    raw = resources.files("pydecay.data").joinpath("icrp107_rad.json.gz").read_bytes()
    data = json.loads(gzip.decompress(raw))
    if not isinstance(data, dict) or "emissions" not in data:
        raise DataFormatError("icrp107_rad.json.gz must be a JSON object with emissions")
    return data


@lru_cache(maxsize=1)
def load_bet() -> dict[str, Any]:
    """Return the full BET payload ``{name: {"E_MeV": [...], "A": [...]}}, cached."""
    raw = resources.files("pydecay.data").joinpath("icrp107_bet.json.gz").read_bytes()
    data = json.loads(gzip.decompress(raw))
    if not isinstance(data, dict):
        raise DataFormatError("icrp107_bet.json.gz must be a JSON object")
    return data


def load_rad_for(name: str) -> list[dict[str, Any]]:
    """Return RAD emission rows for ``name`` (raises if nuclide unknown or has no rows)."""
    norm = normalize_nuclide_name(name)
    catalog = load_catalog()
    if norm not in catalog:
        raise NuclideNotFoundError(f"nuclide {norm!r} not found in ICRP-107 catalog")
    emissions = load_rad()["emissions"]
    rows = emissions.get(norm)
    if not rows:
        raise NuclideNotFoundError(f"no RAD emissions for {norm!r}")
    return cast("list[dict[str, Any]]", rows)


def load_bet_for(name: str) -> dict[str, list[float]]:
    """Return the BET spectrum dict for ``name`` (raises if nuclide unknown or missing)."""
    norm = normalize_nuclide_name(name)
    catalog = load_catalog()
    if norm not in catalog:
        raise NuclideNotFoundError(f"nuclide {norm!r} not found in ICRP-107 catalog")
    payload = load_bet().get(norm)
    if payload is None:
        raise NuclideNotFoundError(f"no BET spectrum for {norm!r}")
    return cast("dict[str, list[float]]", payload)
