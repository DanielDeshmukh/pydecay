"""Checksum-pinned fetch/build CLI for the ICRP-107 catalog.

Build-time tool (network/IO allowed; not a runtime module). Writes
``icrp107.json``, the golden NDX slice, ``LICENSE.ICRP-07``, and (with
``--spectra``) the gzipped RAD/BET artifacts under ``src/pydecay/data/`` /
``tests/fixtures/icrp/``.

NDX pins (plan Resolved 1a/1b): SHA-256 must match before any artifact is
written. ``fetched`` dates use ``datetime.date.today().isoformat()`` at
build time (resolution 14: not pinned).
"""

from __future__ import annotations

import argparse
import datetime
import gzip
import hashlib
import json
import os
import re
import sys
import tarfile
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

from pydecay.data._parse_icrp import BRANCH_SUM_ABS_TOL, NDX_EXPECTED_COUNT, parse_ndx_text
from pydecay.exceptions import DataFormatError
from pydecay.nuclide import normalize_nuclide_name

NDX_URL = (
    "https://raw.githubusercontent.com/radioactivedecay/datasets/main/"
    "icrp107_ame2020_nubase2020/ICRP-07.NDX"
)
NDX_SHA256 = "ac84a9cf1da890031c2ab81a33cba858ff637d701fca3bc33fb07c5a1d6cf2b9"
LICENSE_URL = "https://raw.githubusercontent.com/radioactivedecay/datasets/main/LICENSE.ICRP-07"
LICENSE_SHA256 = "48b128ed84d3e2ee7693491d29fb4ecdf3d00a1e99db20ceb97a9ab36a21aa51"
RADDATA_URL = "https://cran.r-project.org/src/contrib/RadData_1.0.2.tar.gz"
RADDATA_SHA256 = "837f3369e26b43242e514e2d8e9f715cf09ddb0230079f528b11202062ecf54e"

SOURCE = "ICRP-107"
SOURCE_STABLE = "ICRP-107-stable"
SOURCE_URL = "https://www.icrp.org/publication.asp?id=ICRP+Publication+107"
UA = "pydecay-icrp-build/0.2"

_DATA_DIR = Path(__file__).resolve().parent
_ROOT = _DATA_DIR.parents[2]
OUT_PATH = _DATA_DIR / "icrp107.json"
LICENSE_OUT_PATH = _DATA_DIR / "LICENSE.ICRP-07"
RAD_OUT_PATH = _DATA_DIR / "icrp107_rad.json.gz"
BET_OUT_PATH = _DATA_DIR / "icrp107_bet.json.gz"
GOLDEN_OUT_PATH = _ROOT / "tests" / "fixtures" / "icrp" / "ICRP-07.NDX.golden_slice.json"
GOLDEN_NAMES = ("U-238", "Tc-99m", "I-131", "Sr-90", "Co-60", "Pu-239")

_ELEMENTS: tuple[str, ...] = (
    "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al", "Si", "P", "S",
    "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga",
    "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd",
    "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm",
    "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "W", "Re", "Os",
    "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th", "Pa",
    "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr", "Rf", "Db", "Sg",
    "Bh", "Hs", "Mt", "Ds", "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
)
_Z_BY_SYMBOL = {sym: i + 1 for i, sym in enumerate(_ELEMENTS)}
_NAME_RE = re.compile(r"([A-Z][a-z]?)-(\d{1,3})([mn]?)")


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of ``path``."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _require_sha(data: bytes, expected: str, label: str) -> bytes:
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected.lower():
        raise DataFormatError(f"SHA-256 mismatch for {label}: expected {expected}, got {actual}")
    return data


def fetch_bytes(url: str, sha256: str) -> bytes:
    """GET ``url`` and verify the body against ``sha256``.

    Args:
        url: Source URL (http(s) or file).
        sha256: Expected SHA-256 hex digest.

    Returns:
        Raw response bytes after a successful hash match.

    Raises:
        DataFormatError: If the digest does not match.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    return _require_sha(data, sha256, url)


def write_json_atomic(path: Path, obj: Any) -> None:
    """Serialize ``obj`` as pretty JSON and replace ``path`` atomically."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(obj, indent=2, sort_keys=True, allow_nan=True) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def write_gzip_json(path: Path, obj: Any) -> None:
    """Serialize ``obj`` as gzip-compressed JSON and replace ``path`` atomically."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    payload = json.dumps(obj, separators=(",", ":"), allow_nan=True).encode("utf-8")
    tmp.write_bytes(gzip.compress(payload, compresslevel=9))
    os.replace(tmp, path)


def rad_from_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group RAD emission rows by nuclide name.

    Args:
        rows: Dict rows with keys ``RN``, ``code_AN``, ``E_MeV``, ``prob``,
            ``code_num``, ``is_photon``.

    Returns:
        Mapping of nuclide name to a list of emission dicts.
    """
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        name = str(row["RN"])
        is_photon_raw = row.get("is_photon", False)
        if isinstance(is_photon_raw, str):
            is_photon = is_photon_raw.strip().lower() in {"true", "1", "yes"}
        else:
            is_photon = bool(is_photon_raw)
        out[name].append(
            {
                "code_AN": str(row["code_AN"]),
                "E_MeV": float(row["E_MeV"]),
                "prob": float(row["prob"]),
                "code_num": int(float(row["code_num"])),
                "is_photon": is_photon,
            }
        )
    return dict(out)


def bet_from_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, list[float]]]:
    """Group BET spectrum rows by nuclide name.

    Args:
        rows: Dict rows with keys ``RN``, ``E_MeV``, ``A``.

    Returns:
        Mapping of nuclide name to ``{"E_MeV": [...], "A": [...]}``.
    """
    energies: dict[str, list[float]] = defaultdict(list)
    amps: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        name = str(row["RN"])
        energies[name].append(float(row["E_MeV"]))
        amps[name].append(float(row["A"]))
    return {name: {"E_MeV": energies[name], "A": amps[name]} for name in energies}


def _codes_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize rad_codes rows into the artifact ``codes`` list."""
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "code_num": int(float(row["code_num"])),
                "code_AN": str(row["code_AN"]),
                "description": str(row["description"]),
            }
        )
    return out


def _parse_nuclide_za(name: str) -> tuple[int, int]:
    """Return ``(Z, A)`` for names like ``U-238``, ``Tc-99m``, or ``Bi-212n``."""
    m = _NAME_RE.fullmatch(name)
    if m is None:
        raise ValueError(f"cannot parse nuclide name {name!r}")
    symbol = m.group(1)
    if symbol not in _Z_BY_SYMBOL:
        raise ValueError(f"unknown element symbol {symbol!r} in {name!r}")
    return _Z_BY_SYMBOL[symbol], int(m.group(2))


def infer_mode(parent_name: str, daughter_name: str) -> str:
    """Infer a decay mode from the parent/daughter Z-A relationship.

    Same Z and A is isomeric transition (``IT``); A decreases by 4 and Z by
    2 is alpha (``A``); Z increases by 1 is beta-minus (``B-``); Z decreases
    by 1 is electron capture (``EC``) at the Z-A level — ``build_decay_modes``
    refines that case to ``EC`` / ``B+`` / ``EC+B+`` using ``modes_raw``.

    Args:
        parent_name: Parent nuclide name in NDX form.
        daughter_name: Daughter nuclide name in NDX form.

    Returns:
        Mode code string.

    Raises:
        ValueError: If either name is unparseable or the Z-A delta is not a
            supported decay pattern.
    """
    z_p, a_p = _parse_nuclide_za(parent_name)
    z_d, a_d = _parse_nuclide_za(daughter_name)
    dz = z_d - z_p
    da = a_d - a_p
    if dz == 0 and da == 0:
        return "IT"
    if dz == -2 and da == -4:
        return "A"
    if dz == 1 and da == 0:
        return "B-"
    if dz == -1 and da == 0:
        return "EC"
    raise ValueError(f"ambiguous Z-A delta dz={dz} da={da} for {parent_name} -> {daughter_name}")


def _refine_electron_capture(modes_raw: str) -> str | None:
    """Split the Z-1 branch label using the parent's ``modes_raw`` tokens."""
    has_ec = "EC" in modes_raw
    has_bp = "B+" in modes_raw
    if has_ec and has_bp:
        return "EC+B+"
    if has_ec:
        return "EC"
    if has_bp:
        return "B+"
    return None


def build_decay_modes(parsed: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the ``decay_modes`` list for one parsed NDX record.

    Non-SF progeny get Z-A inferred modes (Z-1 refined via ``modes_raw``).
    If inference is ambiguous, a single ``modes_raw`` entry with branch
    ``1.0`` is used only when there is one progeny and the branch sum is
    within ``BRANCH_SUM_ABS_TOL`` of 1; otherwise ``DataFormatError``.
    SF is appended from ``sf_branch`` when present.

    Args:
        parsed: Record dict from ``parse_ndx_line``.

    Returns:
        List of ``{"mode": ..., "branch": ...}`` dicts.

    Raises:
        DataFormatError: If mode inference is ambiguous under multi-progeny.
    """
    name = str(parsed["name"])
    progeny = list(parsed["progeny"])
    branching = [float(b) for b in parsed["branching"]]
    modes_raw = str(parsed["modes_raw"])
    sf_branch = parsed.get("sf_branch")

    out: list[dict[str, Any]] = []
    ambiguous = False
    for daughter, branch in zip(progeny, branching, strict=True):
        try:
            mode = infer_mode(name, daughter)
        except ValueError:
            ambiguous = True
            break
        if mode == "EC":
            refined = _refine_electron_capture(modes_raw)
            if refined is None:
                ambiguous = True
                break
            mode = refined
        out.append({"mode": mode, "branch": branch})
    if ambiguous:
        if len(progeny) == 1 and abs(sum(branching) - 1.0) <= BRANCH_SUM_ABS_TOL:
            out = [{"mode": modes_raw, "branch": 1.0}]
        else:
            raise DataFormatError(
                f"ambiguous decay modes for {name}: modes_raw={modes_raw!r} progeny={progeny!r}"
            )
    if sf_branch is not None:
        out.append({"mode": "SF", "branch": float(sf_branch)})
    return out


def _stable_record(name: str, fetched: str) -> dict[str, Any]:
    m = re.search(r"-(\d+)", name)
    if m is None:
        raise DataFormatError(f"cannot get mass number from stable name {name!r}")
    return {
        "half_life_s": float("inf"),
        "atomic_mass_u": float(m.group(1)),
        "decay_modes": [],
        "source": SOURCE_STABLE,
        "source_url": SOURCE_URL,
        "fetched": fetched,
        "half_life_uncertainty_s": None,
        "half_life_raw": "",
        "half_life_units": "",
        "modes_raw": "",
        "progeny": [],
        "branching": [],
        "sf_branch": None,
        "is_stable": True,
    }


def _radioactive_record(parsed: dict[str, Any], fetched: str) -> dict[str, Any]:
    return {
        "half_life_s": float(parsed["half_life_s"]),
        "atomic_mass_u": float(parsed["atomic_mass_u"]),
        "decay_modes": build_decay_modes(parsed),
        "source": SOURCE,
        "source_url": SOURCE_URL,
        "fetched": fetched,
        "half_life_uncertainty_s": None,
        "half_life_raw": str(parsed["half_life_raw"]),
        "half_life_units": str(parsed["half_life_units"]),
        "modes_raw": str(parsed["modes_raw"]),
        "progeny": list(parsed["progeny"]),
        "branching": [float(b) for b in parsed["branching"]],
        "sf_branch": parsed.get("sf_branch"),
        "is_stable": False,
    }


def build_catalog(records: list[dict[str, Any]], fetched: str) -> dict[str, dict[str, Any]]:
    """Assemble the full catalog: 1252 radioactive rows plus stable endpoints.

    Validates the radioactive count against ``NDX_EXPECTED_COUNT``, injects a
    stable record for every progeny token outside the radioactive set, and
    asserts progeny closure over radioactive union stable.

    Args:
        records: Parsed NDX records from ``parse_ndx_text``.
        fetched: ISO date string stamped on every record.

    Returns:
        Mapping of nuclide name to catalog record.

    Raises:
        DataFormatError: On count mismatch, duplicate names, bad names, or
            progeny left outside the catalog.
    """
    if len(records) != NDX_EXPECTED_COUNT:
        raise DataFormatError(
            f"expected {NDX_EXPECTED_COUNT} radioactive records, got {len(records)}"
        )
    names = [str(r["name"]) for r in records]
    if len(set(names)) != len(names):
        raise DataFormatError("duplicate nuclide names in NDX records")
    for name in names:
        if normalize_nuclide_name(name) != name:
            raise DataFormatError(f"NDX name {name!r} is not in normal form")

    radioactive = set(names)
    stable_names: set[str] = set()
    for rec in records:
        for p in rec["progeny"]:
            if p != "SF" and p not in radioactive:
                stable_names.add(str(p))

    cat: dict[str, dict[str, Any]] = {}
    for rec in records:
        cat[str(rec["name"])] = _radioactive_record(rec, fetched)
    for name in sorted(stable_names):
        cat[name] = _stable_record(name, fetched)

    for name, rec in cat.items():
        if rec["is_stable"]:
            continue
        for p in rec["progeny"]:
            if p not in cat:
                raise DataFormatError(f"progeny {p!r} of {name!r} missing after stable injection")
    return cat


def build_golden_slice(records: list[dict[str, Any]], source_sha256: str) -> dict[str, Any]:
    """Extract the fixed golden nuclide rows (parse-dict shape) for fixtures."""
    by_name = {str(r["name"]): r for r in records}
    missing = [n for n in GOLDEN_NAMES if n not in by_name]
    if missing:
        raise DataFormatError(f"golden names missing from NDX: {missing}")
    return {
        "source": "ICRP-07.NDX",
        "source_sha256": source_sha256,
        "records": [by_name[n] for n in GOLDEN_NAMES],
    }


def _load_pinned(path: Path | None, url: str, sha256: str, label: str) -> bytes:
    if path is not None:
        data = Path(path).read_bytes()
        return _require_sha(data, sha256, f"{label} ({path})")
    return fetch_bytes(url, sha256)


def _load_raddata_tarball(path: Path | None) -> bytes:
    """Return verified RadData tarball bytes from ``path`` or the network."""
    if path is not None:
        data = Path(path).read_bytes()
        return _require_sha(data, RADDATA_SHA256, f"RadData ({path})")
    return fetch_bytes(RADDATA_URL, RADDATA_SHA256)


def build_spectra(raddata_path: Path | None = None) -> tuple[int, int]:
    """Build RAD/BET gzip artifacts from the RadData tarball.

    Requires the optional ``icrp`` extra (``pyreadr``). Returns
    ``(rad_nuclide_count, bet_nuclide_count)``.
    """
    try:
        import pyreadr
    except ImportError as exc:  # pragma: no cover - build-time only
        raise DataFormatError(
            "pyreadr is required for --spectra; install with pip install 'pydecay[icrp]'"
        ) from exc

    tarball = _load_raddata_tarball(raddata_path)
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tar_path = tmp_path / "RadData_1.0.2.tar.gz"
        tar_path.write_bytes(tarball)
        with tarfile.open(tar_path) as tf:
            tf.extractall(tmp_path, filter="data")

        rad_df = next(iter(pyreadr.read_r(str(tmp_path / "RadData/data/ICRP_07.RAD.rda")).values()))
        bet_df = next(iter(pyreadr.read_r(str(tmp_path / "RadData/data/ICRP_07.BET.rda")).values()))
        codes_df = next(iter(pyreadr.read_r(str(tmp_path / "RadData/data/rad_codes.rda")).values()))

    emissions = rad_from_rows(rad_df.to_dict(orient="records"))
    bet = bet_from_rows(bet_df.to_dict(orient="records"))
    codes = _codes_from_rows(codes_df.to_dict(orient="records"))

    write_gzip_json(RAD_OUT_PATH, {"codes": codes, "emissions": emissions})
    write_gzip_json(BET_OUT_PATH, bet)
    return len(emissions), len(bet)


def main(argv: list[str] | None = None) -> int:
    """Download/parse NDX, write catalog + golden slice + license. Exit code."""
    parser = argparse.ArgumentParser(description="Build icrp107.json from ICRP-07.NDX")
    parser.add_argument(
        "--ndx-path",
        type=Path,
        default=None,
        help="Local ICRP-07.NDX (SHA-256 still verified) instead of downloading",
    )
    parser.add_argument(
        "--license-url",
        default=LICENSE_URL,
        help="LICENSE.ICRP-07 URL when no --license-path is given",
    )
    parser.add_argument(
        "--license-path",
        type=Path,
        default=None,
        help="Local LICENSE.ICRP-07 copy (SHA-256 still verified)",
    )
    parser.add_argument(
        "--spectra",
        action="store_true",
        help="Also build icrp107_rad.json.gz and icrp107_bet.json.gz from RadData",
    )
    parser.add_argument(
        "--raddata-path",
        type=Path,
        default=None,
        help="Local RadData_1.0.2.tar.gz (SHA-256 still verified) for --spectra",
    )
    args = parser.parse_args(argv)
    try:
        if args.spectra:
            n_rad, n_bet = build_spectra(args.raddata_path)
            print(f"Wrote {RAD_OUT_PATH} ({n_rad} nuclides)")
            print(f"Wrote {BET_OUT_PATH} ({n_bet} nuclides)")
            return 0

        ndx = _load_pinned(args.ndx_path, NDX_URL, NDX_SHA256, "NDX")
        license_bytes = _load_pinned(args.license_path, args.license_url, LICENSE_SHA256, "license")
        records, meta = parse_ndx_text(ndx.decode("iso-8859-1"))
        if meta["record_count"] != NDX_EXPECTED_COUNT:
            raise DataFormatError(
                f"parsed {meta['record_count']} records, expected {NDX_EXPECTED_COUNT}"
            )
        fetched = datetime.date.today().isoformat()
        catalog = build_catalog(records, fetched)
        golden = build_golden_slice(records, NDX_SHA256)
        write_json_atomic(OUT_PATH, catalog)
        write_json_atomic(GOLDEN_OUT_PATH, golden)
        LICENSE_OUT_PATH.write_bytes(license_bytes)
    except (DataFormatError, OSError, ValueError) as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1
    n_rad = sum(1 for r in catalog.values() if not r["is_stable"])
    n_st = sum(1 for r in catalog.values() if r["is_stable"])
    print(f"Wrote {n_rad}+ radioactive + {n_st} stable = {len(catalog)} to {OUT_PATH}")
    print(f"Wrote golden slice ({len(golden['records'])} rows) to {GOLDEN_OUT_PATH}")
    print(f"Wrote {LICENSE_OUT_PATH} ({len(license_bytes)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
