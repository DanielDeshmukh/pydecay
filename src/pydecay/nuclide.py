"""Nuclide data model and bundled-dataset access (spec sections 3/7)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib import resources
from typing import Any

from pydecay import decay
from pydecay.exceptions import DataFormatError, NuclideNotFoundError
from pydecay.units import mirror_quantity, to_float, to_seconds, ureg

_REQUIRED_KEYS = (
    "half_life_s",
    "atomic_mass_u",
    "decay_modes",
    "source",
    "source_url",
    "fetched",
)

_NAME_RE = re.compile(r"^([A-Za-z]{1,2})-?(\d{1,3})([mM]?)$")


def normalize_nuclide_name(name: str) -> str:
    """Normalize a nuclide name to canonical form like ``I-131`` or ``Tc-99m``."""
    m = _NAME_RE.fullmatch(name.strip())
    if m is None:
        raise DataFormatError(f"cannot parse nuclide name {name!r}")
    element = m.group(1)[0].upper() + m.group(1)[1:].lower()
    mass = m.group(2)
    meta = "m" if m.group(3) else ""
    return f"{element}-{mass}{meta}"


@dataclass(frozen=True)
class DecayMode:
    """A decay mode with its branching fraction."""

    mode: str
    branch: float


@dataclass(frozen=True)
class Nuclide:
    """One nuclide record from the bundled dataset.

    All times are SI seconds; atomic mass is in unified atomic mass units (u).
    """

    name: str
    half_life_s: float
    atomic_mass_u: float
    decay_modes: tuple[DecayMode, ...]
    source: str
    source_url: str
    fetched: str
    half_life_uncertainty_s: float | None = None

    @classmethod
    def from_record(cls, name: str, record: dict[str, Any]) -> Nuclide:
        """Build a validated :class:`Nuclide` from a raw JSON record."""
        norm = normalize_nuclide_name(name)
        for key in _REQUIRED_KEYS:
            if key not in record:
                raise DataFormatError(f"record for {norm} missing required key {key!r}")
        try:
            half_life_s = float(record["half_life_s"])
            atomic_mass_u = float(record["atomic_mass_u"])
        except (TypeError, ValueError) as exc:
            raise DataFormatError(f"record for {norm} has non-numeric mass/half-life") from exc
        if not (half_life_s > 0):
            raise DataFormatError(f"record for {norm} half_life_s must be > 0")
        raw_modes = record["decay_modes"]
        if not isinstance(raw_modes, list):
            raise DataFormatError(f"record for {norm} decay_modes must be a list")
        modes: list[DecayMode] = []
        for item in raw_modes:
            if not isinstance(item, dict) or "mode" not in item or "branch" not in item:
                raise DataFormatError(f"record for {norm} has malformed decay mode {item!r}")
            try:
                modes.append(DecayMode(mode=str(item["mode"]), branch=float(item["branch"])))
            except (TypeError, ValueError) as exc:
                raise DataFormatError(f"record for {norm} has non-numeric branch") from exc
        source = record["source"]
        source_url = record["source_url"]
        fetched = record["fetched"]
        if not all(isinstance(x, str) and x for x in (source, source_url, fetched)):
            raise DataFormatError(
                f"record for {norm} source/source_url/fetched must be non-empty strings"
            )
        unc = record.get("half_life_uncertainty_s")
        if unc is not None:
            try:
                unc = float(unc)
            except (TypeError, ValueError) as exc:
                raise DataFormatError(f"record for {norm} bad uncertainty") from exc
        return cls(
            name=norm,
            half_life_s=half_life_s,
            atomic_mass_u=atomic_mass_u,
            decay_modes=tuple(modes),
            source=source,
            source_url=source_url,
            fetched=fetched,
            half_life_uncertainty_s=unc,
        )

    @classmethod
    def _bundled_records(cls) -> dict[str, Any]:
        text = resources.files("pydecay.data").joinpath("nuclides.json").read_text(
            encoding="utf-8"
        )
        data = json.loads(text)
        if not isinstance(data, dict):
            raise DataFormatError("nuclides.json must be a JSON object")
        return data

    @classmethod
    def load(cls, name: str) -> Nuclide:
        """Load a nuclide from the bundled dataset by name (e.g. ``I-131``)."""
        norm = normalize_nuclide_name(name)
        records = cls._bundled_records()
        if norm not in records:
            raise NuclideNotFoundError(f"nuclide {norm!r} not found in bundled dataset")
        return cls.from_record(norm, records[norm])

    @classmethod
    def load_all(cls) -> dict[str, Nuclide]:
        """Load every nuclide from the bundled dataset."""
        return {norm: cls.from_record(norm, rec) for norm, rec in cls._bundled_records().items()}

    @property
    def lambda_(self) -> float:
        """Decay constant in 1/s."""
        return decay.decay_constant(self.half_life_s)

    @property
    def half_life(self) -> Any:
        """Half-life as a pint Quantity in seconds."""
        return self.half_life_s * ureg.second

    def activity(self, N: float | Any, t: float | str | Any = 0) -> float | Any:
        """Return A(t) = lambda * N * exp(-lambda * t) in Bq, mirroring ``N``'s kind."""
        n_atoms = to_float(N, "atom")
        t_s = to_seconds(t)
        a = self.lambda_ * n_atoms * decay.remaining_fraction(self.lambda_, t_s)
        return mirror_quantity(a, N, "becquerel")
