"""Nuclide data model and bundled-dataset access (spec sections 3/7)."""

from __future__ import annotations

import json
import math
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

_NAME_RE = re.compile(r"^([A-Za-z]{1,2})-?(\d{1,3})([mMnN]?)$")


def normalize_nuclide_name(name: str) -> str:
    """Normalize a nuclide name to canonical form like ``I-131``, ``Tc-99m``, or ``Bi-212n``."""
    m = _NAME_RE.fullmatch(name.strip())
    if m is None:
        raise DataFormatError(f"cannot parse nuclide name {name!r}")
    element = m.group(1)[0].upper() + m.group(1)[1:].lower()
    mass = m.group(2)
    meta = m.group(3).lower()
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
    progeny: tuple[str, ...] = ()
    branching: tuple[float, ...] = ()
    is_stable: bool = False
    sf_branch: float | None = None

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
        progeny, branching, is_stable = cls._parse_progeny_branching(norm, record)
        sf_branch = record.get("sf_branch")
        if sf_branch is not None:
            try:
                sf_branch = float(sf_branch)
            except (TypeError, ValueError) as exc:
                raise DataFormatError(f"record for {norm} bad sf_branch") from exc
            if not math.isfinite(sf_branch) or sf_branch < 0:
                raise DataFormatError(f"record for {norm} sf_branch must be finite and >= 0")
        return cls(
            name=norm,
            half_life_s=half_life_s,
            atomic_mass_u=atomic_mass_u,
            decay_modes=tuple(modes),
            source=source,
            source_url=source_url,
            fetched=fetched,
            half_life_uncertainty_s=unc,
            progeny=progeny,
            branching=branching,
            is_stable=is_stable,
            sf_branch=sf_branch,
        )

    @staticmethod
    def _parse_progeny_branching(
        norm: str, record: dict[str, Any]
    ) -> tuple[tuple[str, ...], tuple[float, ...], bool]:
        """Parse optional progeny/branching/is_stable (defaults empty/false)."""
        raw_progeny = record.get("progeny", [])
        if not isinstance(raw_progeny, list) or not all(
            isinstance(p, str) and p for p in raw_progeny
        ):
            raise DataFormatError(f"record for {norm} progeny must be a list of names")
        raw_branching = record.get("branching", [])
        if not isinstance(raw_branching, list):
            raise DataFormatError(f"record for {norm} branching must be a list")
        branches: list[float] = []
        for item in raw_branching:
            try:
                frac = float(item)
            except (TypeError, ValueError) as exc:
                raise DataFormatError(f"record for {norm} has non-numeric branch") from exc
            if not math.isfinite(frac) or frac < 0:
                raise DataFormatError(
                    f"record for {norm} branching fractions must be finite and >= 0"
                )
            branches.append(frac)
        if len(raw_progeny) != len(branches):
            raise DataFormatError(
                f"record for {norm} progeny/branching length mismatch: "
                f"{len(raw_progeny)} != {len(branches)}"
            )
        is_stable = record.get("is_stable", False)
        if not isinstance(is_stable, bool):
            raise DataFormatError(f"record for {norm} is_stable must be a bool")
        if is_stable and branches:
            raise DataFormatError(f"record for {norm} is stable but has branching fractions")
        return tuple(raw_progeny), tuple(branches), is_stable

    @classmethod
    def _bundled_records(cls) -> dict[str, Any]:
        text = resources.files("pydecay.data").joinpath("icrp107.json").read_text(encoding="utf-8")
        data = json.loads(text)
        if not isinstance(data, dict):
            raise DataFormatError("icrp107.json must be a JSON object")
        return data

    @classmethod
    def load(cls, name: str) -> Nuclide:
        """Load a nuclide from the bundled dataset by name (e.g. ``I-131``)."""
        norm = normalize_nuclide_name(name)
        records = cls._bundled_records()
        if norm not in records:
            raise NuclideNotFoundError(f"nuclide {norm!r} not found in ICRP-107 catalog")
        return cls.from_record(norm, records[norm])

    @classmethod
    def load_all(cls) -> dict[str, Nuclide]:
        """Load every nuclide from the bundled dataset."""
        return {norm: cls.from_record(norm, rec) for norm, rec in cls._bundled_records().items()}

    @property
    def lambda_(self) -> float:
        """Decay constant in 1/s; ``0.0`` for stable nuclides (infinite half-life)."""
        if self.is_stable or not math.isfinite(self.half_life_s):
            return 0.0
        return decay.decay_constant(self.half_life_s)

    @property
    def half_life(self) -> Any:
        """Half-life as a pint Quantity in seconds."""
        return self.half_life_s * ureg.second

    def activity(self, N: float | Any, t: float | str | Any = 0) -> float | Any:
        """Return A(t) = lambda * N * exp(-lambda * t) in Bq, mirroring ``N``'s kind."""
        n_atoms = to_float(N, "atom")
        t_s = to_seconds(t)
        lam = self.lambda_
        if lam == 0.0:
            return mirror_quantity(0.0, N, "becquerel")
        a = lam * n_atoms * decay.remaining_fraction(lam, t_s)
        return mirror_quantity(a, N, "becquerel")
