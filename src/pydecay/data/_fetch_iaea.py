"""Fetch curated nuclide data from the IAEA Live Chart API.

Build-time tool: not part of the installed package (excluded from the wheel).
Writes ``nuclides.json`` next to this file. Half-lives are never hand-typed;
every value comes from the API response, stamped with today's date.

Endpoint reality (probed 2026-09-22): ``https://nds.iaea.org/relnsd/v1/data``
returns CSV (the legacy JSON endpoint is dead) and requires the
``User-Agent: Livechart/1.0`` header (otherwise HTTP 403). Metastable
isomers (``Tc-99m``, ``Pa-234m``) are absent from ``fields=ground_states``;
they are read from ``fields=levels`` of the base nuclide and paired with the
base ground-state mass excess plus the level excitation energy.

Year convention: 1 y = 1 Y = 31557600 s (Julian year, 365.25 d).
Field names are verified against tests/fixtures/iaea_groundstates_sample.csv.
"""

from __future__ import annotations

import csv
import datetime
import io
import json
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

from pydecay.exceptions import DataFormatError

API_GS = "https://nds.iaea.org/relnsd/v1/data?fields=ground_states&nuclides={code}"
API_LEVELS = "https://nds.iaea.org/relnsd/v1/data?fields=levels&nuclides={code}"
UA = "Livechart/1.0"
SOURCE = "IAEA Live Chart of Nuclides (nds.iaea.org)"
SOURCE_URL = "https://nds.iaea.org/relnsd/vcharthtml/VChartHTML.html"
OUT_PATH = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "iaea_nuclides_47.json"

KEV_PER_U = 931494.10242

UNIT_TO_SECONDS: dict[str, float] = {
    "ys": 1e-24,
    "zs": 1e-21,
    "as": 1e-18,
    "fs": 1e-15,
    "ps": 1e-12,
    "ns": 1e-9,
    "us": 1e-6,
    "ms": 1e-3,
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
    "d": 86400.0,
    "y": 31557600.0,
    "Y": 31557600.0,
    "ky": 3.15576e10,
    "My": 3.15576e13,
    "Gy": 3.15576e16,
}

MANDATORY_ISOTOPES: tuple[str, ...] = (
    "Co-60",
    "Cs-137",
    "I-131",
    "C-14",
    "U-238",
    "Tc-99m",
)

ISOTOPES: tuple[str, ...] = (
    "F-18", "Ga-68", "Tc-99m", "Tc-99", "I-131", "I-125", "I-123",
    "Lu-177", "Y-90", "In-111", "Tl-201", "C-11", "Ra-223", "P-32",
    "Co-60", "Cs-137", "Cs-134", "Ir-192", "Sr-90", "Kr-85", "Ar-39",
    "Am-241", "Po-210", "Pb-210", "Rn-222", "Ra-226", "Ra-224",
    "Th-232", "U-238", "U-235", "Pu-239",
    "C-14", "H-3", "K-40", "Ca-45", "S-35",
    "Na-24", "Fe-59", "Co-57", "Zn-65", "Mn-54", "Cr-51", "Se-75",
    "Th-234", "Pa-234m", "U-234", "Th-230",
)


def half_life_to_seconds(value: str, unit: str) -> float:
    """Convert an IAEA half-life value/unit pair to seconds."""
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise DataFormatError(f"non-numeric half-life value {value!r}") from exc
    if unit not in UNIT_TO_SECONDS:
        raise DataFormatError(f"unknown half-life unit {unit!r}")
    seconds = v * UNIT_TO_SECONDS[unit]
    if not (seconds > 0):
        raise DataFormatError(f"half-life must be > 0, got {seconds}")
    return seconds


def parse_groundstate(record: dict[str, Any]) -> dict[str, Any]:
    """Convert one API CSV row (ground state or isomer level) into a bundled record."""
    today = datetime.date.today().isoformat()
    hl_v = record.get("half_life")
    hl_u = record.get("unit_hl")
    if not hl_v or not hl_u:
        raise DataFormatError(f"record missing half-life fields: {record!r}")
    half_life_s = half_life_to_seconds(str(hl_v), str(hl_u))
    try:
        mass_number = int(record["z"]) + int(record["n"])
    except (KeyError, TypeError, ValueError) as exc:
        raise DataFormatError(f"record missing usable z/n: {record!r}") from exc
    try:
        mass_excess_kev = float(record["massexcess"])
    except (KeyError, TypeError, ValueError) as exc:
        raise DataFormatError(f"record missing usable massexcess: {record!r}") from exc
    atomic_mass_u = mass_number + mass_excess_kev / KEV_PER_U
    if not (atomic_mass_u > 0):
        raise DataFormatError(f"non-positive atomic mass for {record!r}")
    decay_modes: list[dict[str, Any]] = []
    for i in (1, 2, 3):
        mode = record.get(f"decay_{i}")
        pct = record.get(f"decay_{i}_%")
        if not mode or not pct:
            continue
        try:
            branch = float(pct) / 100.0
        except (TypeError, ValueError) as exc:
            raise DataFormatError(f"non-numeric decay branch {pct!r}") from exc
        decay_modes.append({"mode": str(mode), "branch": branch})
    return {
        "half_life_s": half_life_s,
        "atomic_mass_u": atomic_mass_u,
        "decay_modes": decay_modes,
        "source": SOURCE,
        "source_url": SOURCE_URL,
        "fetched": today,
        "half_life_uncertainty_s": None,
    }


def _api_get(url: str) -> str:
    """GET ``url`` with the required User-Agent; sleep 0.2 s for rate-limit courtesy."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data: bytes = resp.read()
    time.sleep(0.2)
    return data.decode("utf-8")


def _read_csv(url: str) -> list[dict[str, Any]]:
    text = _api_get(url).strip()
    if not text:
        return []
    return list(csv.DictReader(io.StringIO(text)))


def _nuclide_code(norm: str) -> str:
    """``I-131`` -> ``131i`` (mass digits + lowercased symbol)."""
    element, mass = norm.split("-")
    return f"{mass}{element.lower()}"


def _fetch_isomer(norm: str) -> dict[str, Any]:
    """Fetch a metastable isomer via ground_states + levels of the base nuclide."""
    base = norm[:-1]
    code = _nuclide_code(base)
    gs_rows = _read_csv(API_GS.format(code=code))
    if not gs_rows:
        raise DataFormatError(f"no groundstate data returned for {norm}")
    try:
        gs_massexcess = float(gs_rows[0]["massexcess"])
    except (KeyError, TypeError, ValueError) as exc:
        raise DataFormatError(f"record missing usable massexcess for {base}") from exc
    candidates: list[tuple[float, dict[str, Any], float]] = []
    for row in _read_csv(API_LEVELS.format(code=code)):
        try:
            energy = float(row.get("energy") or "")
            hls = float(row.get("half_life_sec") or "")
        except (TypeError, ValueError):
            continue
        if energy > 0 and hls > 0:
            candidates.append((hls, row, energy))
    if not candidates:
        raise DataFormatError(f"no long-lived level found for {norm}")
    candidates.sort(key=lambda item: item[0], reverse=True)
    _, row, energy = candidates[0]
    synth = dict(row)
    synth["massexcess"] = gs_massexcess + energy
    return parse_groundstate(synth)


def fetch_one(name: str) -> dict[str, Any]:
    """Fetch and parse a single nuclide record from the live API."""
    from pydecay.nuclide import normalize_nuclide_name

    norm = normalize_nuclide_name(name)
    if norm.endswith("m"):
        return _fetch_isomer(norm)
    rows = _read_csv(API_GS.format(code=_nuclide_code(norm)))
    if not rows:
        raise DataFormatError(f"no groundstate data returned for {norm}")
    return parse_groundstate(rows[0])


def main() -> int:
    """Fetch all curated isotopes and write nuclides.json. Returns exit code."""
    out: dict[str, Any] = {}
    failures: list[str] = []
    for name in ISOTOPES:
        try:
            out[name] = fetch_one(name)
        except Exception as exc:  # report and continue per-isotope
            failures.append(f"{name}: {exc}")
    missing_mandatory = [m for m in MANDATORY_ISOTOPES if m not in out]
    if missing_mandatory:
        print("FATAL: mandatory isotopes failed:", ", ".join(missing_mandatory), file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1
    for f in failures:
        print(f"WARN skipped: {f}", file=sys.stderr)
    OUT_PATH.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {len(out)} nuclides to {OUT_PATH} ({len(failures)} skipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
