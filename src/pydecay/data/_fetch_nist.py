"""Checksum-pinned NIST XCOM mass-attenuation fetch/build CLI.

Build-time tool (network allowed; excluded from the wheel and coverage).
Writes ``nist_mu.json.gz`` next to this file with total mass attenuation
coefficients (mu/rho, cm^2/g, with coherent scattering) for the seven v0.6
shielding materials at 45 log-spaced energies spanning 0.01-20 MeV.

Endpoint reality (probed 2026-09-25): the text-based XCOM form at
``https://physics.nist.gov/PhysRefData/Xcom/html/xcom1-t.html`` is scriptable
via urllib POST: ``/cgi-bin/Xcom/xcom2-t`` selects Elem/Comp/Mix, then
``/cgi-bin/Xcom/xcom3_{1,2,3}-t`` returns an HTML page whose ``<pre>`` block
holds the data table. Textarea fields MUST use CRLF line endings (LF-only is
rejected with "Energies must be between 1 keV and 100 GeV"). Omitting the
``Output`` checkbox limits output to the requested energies (XCOM applies its
own 4-significant-figure rounding, matching NIST's published tables - cross-
checked against ``XrayMassCoef/ElemTab/z82.html``: Pb at 10 keV = 1.306E+02).
Cloudflare injects a per-request challenge script into responses; it is
stripped before hashing so the pinned raw file stays byte-stable.

Materials and provenance:
- ``lead``/``iron``/``aluminum``: XCOM elements Pb/Fe/Al.
- ``water``: XCOM compound H2O; ``polyethylene``: XCOM compound CH2 (XCOM
  forbids parentheses, so polyethylene is entered as its repeat unit; the
  resulting weight fractions H 0.143716 / C 0.856284 are NIST Table 2's
  Polyethylene row).
- ``air``/``concrete``: XCOM mixtures built from weight fractions transcribed
  from NIST X-Ray Mass Attenuation Coefficients Table 2
  (https://physics.nist.gov/PhysRefData/XrayMassCoef/tab2.html, fetched
  2026-09-25): "Air, Dry (near sea level)" C 0.000124 / N 0.755268 /
  O 0.231781 / Ar 0.012827 and "Concrete, Ordinary" H 0.022100 / C 0.002484 /
  O 0.574930 / Na 0.015208 / Mg 0.001266 / Al 0.019953 / Si 0.304627 /
  K 0.010045 / Ca 0.042951 / Fe 0.006435.

Densities (g/cm^3) are metadata only (mu/rho is density-independent):
lead 11.35, aluminum 2.699 and iron 7.87 from NIST Table 1
(https://physics.nist.gov/PhysRefData/XrayMassCoef/tab1.html: 1.135E+01,
2.699E+00, 7.874E+00 - iron rounded to the spec value); water 1.00, concrete
2.30 and air 1.205e-3 (20 C, 1 atm) from NIST Table 2 (1.000E+00,
2.300E+00, 1.205E-03); polyethylene 0.94 per the v0.6 dose/shielding spec
(NIST Table 2 lists the nominal 9.300E-01).

``RAW_SHA256`` pins ``data/raw_nist/xcom.txt`` (the concatenated, CF-stripped
responses). If NIST legitimately changes the responses, re-fetch and update
the pin in the same commit, as with ``_fetch_icrp.py``'s NDX pin.
"""

from __future__ import annotations

import argparse
import datetime
import gzip
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from pydecay.exceptions import DataFormatError

SOURCE = "NIST XCOM"
SOURCE_URL = "https://physics.nist.gov/PhysRefData/Xcom/html/xcom1.html"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
XCOM_ELEM_URL = "https://physics.nist.gov/cgi-bin/Xcom/xcom3_1-t"
XCOM_COMP_URL = "https://physics.nist.gov/cgi-bin/Xcom/xcom3_2-t"
XCOM_MIX_URL = "https://physics.nist.gov/cgi-bin/Xcom/xcom3_3-t"

DATA_DIR = Path(__file__).resolve().parent
_ROOT = DATA_DIR.parents[2]
OUT_PATH = DATA_DIR / "nist_mu.json.gz"
DEFAULT_RAW_PATH = _ROOT / "data" / "raw_nist" / "xcom.txt"

RAW_SHA256 = "3fd1d13f0ed93d9f2dc1e542127b0e492e693f882f6a8cab28a7e2fadabf4a63"

REQUIRED_MATERIALS: tuple[str, ...] = (
    "lead",
    "iron",
    "water",
    "concrete",
    "aluminum",
    "air",
    "polyethylene",
)

DENSITY_G_CM3: dict[str, float] = {
    "lead": 11.35,
    "iron": 7.87,
    "water": 1.00,
    "concrete": 2.30,
    "aluminum": 2.699,
    "air": 1.205e-3,
    "polyethylene": 0.94,
}

_AIR_FORMULAE = "\r\n".join(("C 0.000124", "N 0.755268", "O 0.231781", "Ar 0.012827"))
_CONCRETE_FORMULAE = "\r\n".join(
    (
        "H 0.022100",
        "C 0.002484",
        "O 0.574930",
        "Na 0.015208",
        "Mg 0.001266",
        "Al 0.019953",
        "Si 0.304627",
        "K 0.010045",
        "Ca 0.042951",
        "Fe 0.006435",
    )
)

MATERIAL_QUERIES: dict[str, tuple[str, dict[str, str]]] = {
    "lead": (XCOM_ELEM_URL, {"ZSym": "Pb", "ZNum": "", "OutOpt": "PIC"}),
    "iron": (XCOM_ELEM_URL, {"ZSym": "Fe", "ZNum": "", "OutOpt": "PIC"}),
    "water": (XCOM_COMP_URL, {"Formula": "H2O", "Name": ""}),
    "concrete": (XCOM_MIX_URL, {"Formulae": _CONCRETE_FORMULAE, "Name": ""}),
    "aluminum": (XCOM_ELEM_URL, {"ZSym": "Al", "ZNum": "", "OutOpt": "PIC"}),
    "air": (XCOM_MIX_URL, {"Formulae": _AIR_FORMULAE, "Name": ""}),
    "polyethylene": (XCOM_COMP_URL, {"Formula": "CH2", "Name": ""}),
}

E_MIN_MEV = 0.01
E_MAX_MEV = 20.0
N_ENERGIES = 45
MIN_POINTS = 40

_RAW_HEADER = (
    b"### pydecay raw_nist xcom.txt - NIST XCOM text-form responses "
    b"(see src/pydecay/data/_fetch_nist.py)\n"
)
_SECTION_RE = re.compile(r"^### material: ([a-z]+)[ \t]*$", re.MULTILINE)
_SCI_TOKEN_RE = re.compile(r"[+-]?\d+\.\d+E[+-]\d+")
_CF_CLICKJACK_RE = re.compile(rb"<script>\(function\(\)\{function c\(\).*?</script>", re.DOTALL)
_CF_BEACON_RE = re.compile(
    rb'<script type="module" src="https://static\.cloudflareinsights\.com/.*?</script>\n?',
    re.DOTALL,
)


def log_energy_grid() -> list[str]:
    """Return ``N_ENERGIES`` log-spaced energies covering 0.01-20 MeV.

    Returns:
        Energy strings in 4-significant-figure scientific notation (the
        precision XCOM accepts), strictly increasing, endpoints exact.
    """
    ratio = E_MAX_MEV / E_MIN_MEV
    return [f"{E_MIN_MEV * ratio ** (i / (N_ENERGIES - 1)):.3e}" for i in range(N_ENERGIES)]


def parse_xcom_text(text: str) -> list[tuple[float, float]]:
    """Parse ``(E_MeV, mu_over_rho)`` rows from an XCOM text-form response.

    A data row is a line carrying at least two E-notation numbers: header,
    constituent ("Z=8 : 0.888102") and markup lines carry none and are
    skipped. Two-number lines are taken as ``(E, mu/rho)`` directly; longer
    lines are the XCOM table ``E, coherent, incoherent, photoelectric,
    pair-nuclear, pair-electron, total-with-coherent, total-without-coherent``
    and use column 1 (total attenuation with coherent scattering).

    Args:
        text: One XCOM response body (or any text with the same row layout).

    Returns:
        ``(E_MeV, mu_over_rho)`` pairs in file order.
    """
    rows: list[tuple[float, float]] = []
    for line in text.splitlines():
        nums = _SCI_TOKEN_RE.findall(line)
        if len(nums) == 2:
            rows.append((float(nums[0]), float(nums[1])))
        elif len(nums) >= 8:
            rows.append((float(nums[0]), float(nums[6])))
    return rows


def validate_payload(payload: dict[str, Any]) -> None:
    """Validate a bundle payload against the v0.6 schema.

    Requires every ``REQUIRED_MATERIALS`` entry with a positive finite
    density, at least ``MIN_POINTS`` positive finite ``(E, mu/rho)`` rows in
    strictly increasing energy order, and an energy span covering
    ``[0.01, 20]`` MeV.

    Args:
        payload: Candidate bundle dict (see module docstring).

    Raises:
        DataFormatError: If any schema or physical-range requirement fails.
    """
    materials = payload.get("materials")
    if not isinstance(materials, dict):
        raise DataFormatError("payload.materials must be an object")
    missing = [name for name in REQUIRED_MATERIALS if name not in materials]
    if missing:
        raise DataFormatError(f"missing required materials: {', '.join(missing)}")
    for name in REQUIRED_MATERIALS:
        entry = materials[name]
        if not isinstance(entry, dict):
            raise DataFormatError(f"material {name!r} must be an object")
        density = entry.get("density_g_cm3")
        if not isinstance(density, (int, float)) or not math.isfinite(density) or density <= 0:
            raise DataFormatError(f"{name}: density_g_cm3 must be finite and > 0, got {density!r}")
        energies = entry.get("E_MeV")
        mus = entry.get("mu_over_rho")
        if not isinstance(energies, list) or not isinstance(mus, list):
            raise DataFormatError(f"{name}: E_MeV and mu_over_rho must be lists")
        if len(energies) != len(mus):
            raise DataFormatError(f"{name}: E_MeV and mu_over_rho lengths differ")
        if len(energies) < MIN_POINTS:
            raise DataFormatError(f"{name}: {len(energies)} points, need at least {MIN_POINTS}")
        previous: float | None = None
        for index, (energy_raw, mu_raw) in enumerate(zip(energies, mus, strict=True)):
            try:
                energy = float(energy_raw)
                mu = float(mu_raw)
            except (TypeError, ValueError) as exc:
                raise DataFormatError(
                    f"{name}: non-numeric row {index}: {energy_raw!r}, {mu_raw!r}"
                ) from exc
            if not math.isfinite(energy) or energy <= 0:
                raise DataFormatError(f"{name}: non-positive/non-finite E at row {index}: {energy}")
            if not math.isfinite(mu) or mu <= 0:
                raise DataFormatError(
                    f"{name}: non-positive/non-finite mu/rho at row {index}: {mu}"
                )
            if previous is not None and energy <= previous:
                raise DataFormatError(f"{name}: energies not strictly increasing at row {index}")
            previous = energy
        assert previous is not None  # len >= MIN_POINTS guarantees rows
        if float(energies[0]) > E_MIN_MEV or float(energies[-1]) < E_MAX_MEV:
            raise DataFormatError(
                f"{name}: energy span [{energies[0]}, {energies[-1]}] does not cover "
                f"[{E_MIN_MEV}, {E_MAX_MEV}] MeV"
            )


def _strip_cf_noise(data: bytes) -> bytes:
    """Remove Cloudflare's per-request challenge/beacon scripts from a response."""
    data = _CF_CLICKJACK_RE.sub(b"", data)
    return _CF_BEACON_RE.sub(b"", data)


def _post(url: str, fields: dict[str, str]) -> bytes:
    """POST ``fields`` to a XCOM CGI with retries; return the raw response bytes.

    Args:
        url: Full XCOM CGI endpoint.
        fields: Form fields (textarea values must already use CRLF).

    Returns:
        Raw response body bytes.

    Raises:
        DataFormatError: If every attempt fails.
    """
    body = urllib.parse.urlencode(fields).encode("ascii")
    last_error: OSError | None = None
    for _ in range(5):
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "User-Agent": UA,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                raw: bytes = response.read()
                return raw
        except OSError as exc:
            last_error = exc
            time.sleep(3)
    raise DataFormatError(f"XCOM request to {url} failed after retries: {last_error}")


def fetch_raw() -> bytes:
    """Fetch all required materials from the XCOM text form.

    Returns:
        The concatenated, CF-stripped responses with ``### material: name``
        section markers - exactly the bytes written to ``data/raw_nist/xcom.txt``.

    Raises:
        DataFormatError: If any material returns fewer than ``MIN_POINTS``
            rows (CGI error pages parse to zero rows).
    """
    grid = "\r\n".join(log_energy_grid())
    chunks = [_RAW_HEADER]
    for name in REQUIRED_MATERIALS:
        url, base_fields = MATERIAL_QUERIES[name]
        fields = dict(base_fields)
        fields["Energies"] = grid
        body = _strip_cf_noise(_post(url, fields))
        rows = parse_xcom_text(body.decode("utf-8", "replace"))
        if len(rows) < MIN_POINTS:
            raise DataFormatError(f"{name}: XCOM returned {len(rows)} rows, expected {MIN_POINTS}+")
        chunks.append(f"### material: {name}\n".encode("ascii"))
        chunks.append(body)
        time.sleep(0.5)
    return b"".join(chunks)


def _split_sections(text: str) -> dict[str, str]:
    """Map material name to response body for each ``### material:`` marker."""
    matches = list(_SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[match.end() : end]
    return sections


def _require_sha(data: bytes, expected: str, label: str) -> bytes:
    """Return ``data`` if its SHA-256 matches ``expected``, else raise.

    Raises:
        DataFormatError: On digest mismatch, showing the actual digest.
    """
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected.lower():
        raise DataFormatError(
            f"SHA-256 mismatch for {label}: RAW_SHA256={expected or '<unset>'!r}, got {actual} "
            "(if this re-fetch is intentional, update RAW_SHA256 in _fetch_nist.py)"
        )
    return data


def _write_gzip_json(path: Path, payload: dict[str, Any]) -> None:
    """Serialize ``payload`` as gzip JSON and replace ``path`` atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    tmp.write_bytes(gzip.compress(encoded, compresslevel=9))
    os.replace(tmp, path)


def build(raw_path: Path, out_path: Path) -> dict[str, Any]:
    """Parse pinned raw XCOM responses, validate, and write ``nist_mu.json.gz``.

    Args:
        raw_path: Concatenated raw responses file (SHA-256 must match
            ``RAW_SHA256``).
        out_path: Destination gzip JSON path.

    Returns:
        The validated payload that was written.

    Raises:
        DataFormatError: On SHA mismatch, missing sections, or failed
            validation.
    """
    raw = _require_sha(Path(raw_path).read_bytes(), RAW_SHA256, str(raw_path))
    sections = _split_sections(raw.decode("utf-8", "replace"))
    materials: dict[str, Any] = {}
    for name in REQUIRED_MATERIALS:
        body = sections.get(name)
        if body is None:
            raise DataFormatError(f"raw file {raw_path} has no '### material: {name}' section")
        rows = parse_xcom_text(body)
        materials[name] = {
            "density_g_cm3": DENSITY_G_CM3[name],
            "E_MeV": [energy for energy, _ in rows],
            "mu_over_rho": [mu for _, mu in rows],
        }
    payload: dict[str, Any] = {
        "source": SOURCE,
        "source_url": SOURCE_URL,
        "fetched": datetime.date.today().isoformat(),
        "units": {"E_MeV": "MeV", "mu_over_rho": "cm^2/g"},
        "materials": materials,
    }
    validate_payload(payload)
    _write_gzip_json(out_path, payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    """Fetch (if needed) and build nist_mu.json.gz. Returns exit code."""
    parser = argparse.ArgumentParser(description="Build nist_mu.json.gz from NIST XCOM responses")
    parser.add_argument(
        "--raw",
        type=Path,
        default=DEFAULT_RAW_PATH,
        help="Raw XCOM responses file (fetched from the network if absent)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT_PATH,
        help="Output gzip JSON path (default: src/pydecay/data/nist_mu.json.gz)",
    )
    args = parser.parse_args(argv)
    try:
        if not args.raw.exists():
            args.raw.parent.mkdir(parents=True, exist_ok=True)
            raw = fetch_raw()
            args.raw.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            print(f"Fetched XCOM responses -> {args.raw} (sha256 {digest})")
        payload = build(args.raw, args.out)
    except (DataFormatError, OSError, ValueError) as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {len(payload['materials'])} materials to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
