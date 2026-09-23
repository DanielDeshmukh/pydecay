"""Pure parsers for ICRP-07.NDX (build-time; no network)."""

from __future__ import annotations

from typing import Any

from pydecay.exceptions import DataFormatError

NDX_EXPECTED_COUNT = 1252
BRANCH_SUM_ABS_TOL = 0.035

# Keep values in sync with pydecay.data._fetch_iaea.UNIT_TO_SECONDS
# (that map also carries ky/My/Gy; ICRP NDX never uses them).
UNIT_TO_SECONDS: dict[str, float] = {
    "ys": 1e-24,
    "zs": 1e-21,
    "as": 1e-18,
    "fs": 1e-15,
    "ps": 1e-12,
    "ns": 1e-9,
    "ls": 1e-6,
    "us": 1e-6,
    "ms": 1e-3,
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
    "d": 86400.0,
    "y": 31557600.0,
    "Y": 31557600.0,
}


def half_life_to_seconds_icrp(value: str, unit: str) -> float:
    """Convert a raw ICRP half-life value and unit to seconds.

    Args:
        value: Numeric half-life as written in the NDX field.
        unit: NDX half-life unit code (for example ``m``, ``h``, ``d``, ``y``).

    Returns:
        Half-life in seconds, strictly positive.

    Raises:
        DataFormatError: If the value is non-numeric, the unit is unknown,
            or the result is not greater than zero.
    """
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise DataFormatError(f"non-numeric half-life {value!r}") from exc
    if unit not in UNIT_TO_SECONDS:
        raise DataFormatError(f"unknown half-life unit {unit!r}")
    seconds = v * UNIT_TO_SECONDS[unit]
    if not (seconds > 0):
        raise DataFormatError(f"half-life must be > 0, got {seconds}")
    return seconds


def parse_ndx_line(line: str) -> dict[str, Any]:
    """Parse one 226-character ICRP-07.NDX data line into a record dict.

    Args:
        line: A single fixed-width NDX data line (no newline).

    Returns:
        Record dict with name, half-life fields, modes_raw, progeny and
        branching (catalog species only, ``SF`` split out into ``sf_branch``),
        atomic_mass_u, and icrp_extra energies/counts.

    Raises:
        DataFormatError: If the line length, header fields, progeny block,
            branch values, branch sum, or atomic mass are invalid.
    """
    if len(line) != 226:
        raise DataFormatError(f"NDX line length {len(line)} != 226: {line[:20]!r}")
    name = line[0:7].strip()
    hl_raw = line[7:15].strip()
    unit = line[15:17].strip()
    modes_raw = line[17:25].strip()
    if not name or not hl_raw or not unit:
        raise DataFormatError(f"bad NDX header fields: {line[:25]!r}")
    half_life_s = half_life_to_seconds_icrp(hl_raw, unit)
    return _parse_ndx_line_cursor(line, name, hl_raw, unit, modes_raw, half_life_s)


def _ndx_float_field(raw: str, field: str, name: str) -> float:
    try:
        return float(raw or "0")
    except ValueError as exc:
        raise DataFormatError(f"bad {field} {raw!r} for {name}") from exc


def _ndx_int_field(raw: str, field: str, name: str) -> int:
    try:
        return int(raw or "0")
    except ValueError as exc:
        raise DataFormatError(f"bad {field} {raw!r} for {name}") from exc


def _parse_ndx_line_cursor(
    line: str,
    name: str,
    hl_raw: str,
    unit: str,
    modes_raw: str,
    half_life_s: float,
) -> dict[str, Any]:
    off = 53
    progeny: list[str] = []
    branching: list[float] = []
    sf_branch: float | None = None
    all_branches: list[float] = []
    for k in range(4):
        p = line[off : off + 7].strip()
        off += 7
        off += 6  # pointer field
        b_str = line[off : off + 11].strip()
        off += 11
        if k < 3:
            off += 1  # 1x separator after the first three triples
        if not p:
            if b_str:
                try:
                    empty_branch = float(b_str)
                except ValueError as exc:
                    raise DataFormatError(f"bad branch {b_str!r} for {name}") from exc
                if empty_branch != 0.0:
                    raise DataFormatError(f"branch without progeny at slot {k} in {name}")
            continue
        try:
            b = float(b_str)
        except ValueError as exc:
            raise DataFormatError(f"bad branch {b_str!r} for {name}") from exc
        all_branches.append(b)
        if p == "SF":
            sf_branch = b if sf_branch is None else sf_branch + b
            continue
        progeny.append(p)
        branching.append(b)
    e_alpha = _ndx_float_field(line[152:159].strip(), "E_alpha", name)
    e_electron = _ndx_float_field(line[159:167].strip(), "E_electron", name)
    e_photon = _ndx_float_field(line[167:175].strip(), "E_photon", name)
    # counts: 3i4, i5, i4
    c0 = _ndx_int_field(line[175:179].strip(), "num_phot_lt_10k", name)
    c1 = _ndx_int_field(line[179:183].strip(), "num_phot_gt_10k", name)
    c2 = _ndx_int_field(line[183:187].strip(), "num_betas", name)
    c3 = _ndx_int_field(line[187:192].strip(), "num_mono_e", name)
    c4 = _ndx_int_field(line[192:196].strip(), "num_alpha", name)
    mass_s = line[196:207].strip()
    try:
        atomic_mass_u = float(mass_s)
    except ValueError as exc:
        raise DataFormatError(f"bad AMU {mass_s!r} for {name}") from exc
    if not (atomic_mass_u > 0):
        raise DataFormatError(f"non-positive AMU for {name}")
    total = sum(all_branches) if all_branches else 0.0
    if all_branches and abs(total - 1.0) > BRANCH_SUM_ABS_TOL:
        raise DataFormatError(f"branch sum {total} out of tol for {name}")
    return {
        "name": name,
        "half_life_raw": hl_raw,
        "half_life_units": unit,
        "half_life_s": half_life_s,
        "modes_raw": modes_raw,
        "progeny": progeny,
        "branching": branching,
        "sf_branch": sf_branch,
        "atomic_mass_u": atomic_mass_u,
        "icrp_extra": {
            "E_alpha": e_alpha,
            "E_electron": e_electron,
            "E_photon": e_photon,
            "num_phot_lt_10k": c0,
            "num_phot_gt_10k": c1,
            "num_betas": c2,
            "num_mono_e": c3,
            "num_alpha": c4,
        },
    }


def parse_ndx_text(text: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parse full ICRP-07.NDX text into records and header metadata.

    Args:
        text: Entire file contents (ISO-8859-1 decoded).

    Returns:
        Tuple of (records, meta) where meta has ``header`` and
        ``record_count``.

    Raises:
        DataFormatError: If the text is empty or any data line fails to parse.
    """
    lines = text.splitlines()
    if not lines:
        raise DataFormatError("empty NDX")
    header = lines[0]
    records = [parse_ndx_line(line) for line in lines[1:] if line.strip()]
    return records, {"header": header, "record_count": len(records)}
