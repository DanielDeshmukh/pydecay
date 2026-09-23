"""Catalog build invariants (spec sections 6, 9, 10)."""

import hashlib
import json
import re
from pathlib import Path

import pytest

from pydecay.data._fetch_icrp import (
    LICENSE_SHA256,
    NDX_SHA256,
    build_catalog,
    build_decay_modes,
    fetch_bytes,
    infer_mode,
    sha256_file,
    write_json_atomic,
)
from pydecay.data._parse_icrp import NDX_EXPECTED_COUNT, parse_ndx_text
from pydecay.exceptions import DataFormatError
from pydecay.nuclide import normalize_nuclide_name

NDX_URL_SHA = "ac84a9cf1da890031c2ab81a33cba858ff637d701fca3bc33fb07c5a1d6cf2b9"
LICENSE_PIN = "48b128ed84d3e2ee7693491d29fb4ecdf3d00a1e99db20ceb97a9ab36a21aa51"
ART = Path(__file__).resolve().parents[1] / "src" / "pydecay" / "data" / "icrp107.json"
FULL_NDX = Path(r"C:\Users\DANIEL\AppData\Local\Temp\opencode\ICRP-07.NDX")


def _parsed(**over):
    base = {
        "name": "U-238",
        "half_life_raw": "4.468E+9",
        "half_life_units": "y",
        "half_life_s": 1.0,
        "modes_raw": "A SF",
        "progeny": ["Th-234"],
        "branching": [1.0],
        "sf_branch": 5.45e-7,
        "atomic_mass_u": 238.0,
    }
    base.update(over)
    return base


@pytest.mark.skipif(not FULL_NDX.exists(), reason="full NDX not downloaded yet")
def test_full_ndx_parses_1252():
    _records, meta = parse_ndx_text(FULL_NDX.read_text(encoding="iso-8859-1"))
    assert meta["record_count"] == NDX_EXPECTED_COUNT == 1252


@pytest.mark.skipif(not FULL_NDX.exists(), reason="full NDX not downloaded yet")
def test_build_catalog_counts_and_closure():
    records, _ = parse_ndx_text(FULL_NDX.read_text(encoding="iso-8859-1"))
    cat = build_catalog(records, fetched="2026-09-23")
    radioactive = [n for n, r in cat.items() if not r["is_stable"]]
    stables = [n for n, r in cat.items() if r["is_stable"]]
    assert len(radioactive) == 1252
    assert stables
    for name, rec in cat.items():
        if rec["is_stable"]:
            assert rec["half_life_s"] == float("inf")
            assert rec["decay_modes"] == []
            assert rec["progeny"] == []
            assert rec["branching"] == []
            assert rec["sf_branch"] is None
            assert rec["source"] == "ICRP-107-stable"
            assert rec["modes_raw"] == ""
            mass = re.search(r"-(\d+)", name)
            assert mass is not None
            assert rec["atomic_mass_u"] == float(mass.group(1))
            continue
        assert rec["half_life_s"] > 0
        assert rec["is_stable"] is False
        assert rec["source"] == "ICRP-107"
        assert isinstance(rec["decay_modes"], list)
        assert rec["decay_modes"]
        for mode in rec["decay_modes"]:
            assert set(mode) == {"mode", "branch"}
            assert isinstance(mode["branch"], float)
        missing = [p for p in rec["progeny"] if p not in cat]
        assert not missing, missing
        assert "ICRP-107" in rec["source"]


@pytest.mark.skipif(not FULL_NDX.exists(), reason="full NDX not downloaded yet")
def test_ndx_names_already_normal_form():
    records, _ = parse_ndx_text(FULL_NDX.read_text(encoding="iso-8859-1"))
    for rec in records:
        assert normalize_nuclide_name(rec["name"]) == rec["name"]


def test_pinned_sha_constants_match_plan():
    assert NDX_SHA256 == NDX_URL_SHA
    assert LICENSE_SHA256 == LICENSE_PIN


def test_build_catalog_rejects_wrong_count():
    with pytest.raises(DataFormatError):
        build_catalog([], fetched="2026-09-23")


def test_infer_mode_z_a_rules():
    assert infer_mode("U-238", "Th-234") == "A"
    assert infer_mode("Sr-90", "Y-90") == "B-"
    assert infer_mode("Tc-99m", "Tc-99") == "IT"
    assert infer_mode("Ac-224", "Ra-224") == "EC"
    assert infer_mode("Bi-212n", "Po-212m") == "B-"
    assert infer_mode("Ir-190n", "Ir-190") == "IT"
    with pytest.raises(ValueError):
        infer_mode("U-238", "U-237")
    with pytest.raises(ValueError):
        infer_mode("not-a-nuclide", "Th-234")


def test_build_decay_modes_alpha_with_sf():
    assert build_decay_modes(_parsed()) == [
        {"mode": "A", "branch": 1.0},
        {"mode": "SF", "branch": 5.45e-7},
    ]


def test_build_decay_modes_it_and_beta():
    modes = build_decay_modes(
        _parsed(
            name="Tc-99m",
            modes_raw="ITB-",
            progeny=["Tc-99", "Ru-99"],
            branching=[0.99996, 3.7e-5],
            sf_branch=None,
        )
    )
    assert modes == [
        {"mode": "IT", "branch": 0.99996},
        {"mode": "B-", "branch": 3.7e-5},
    ]


def test_build_decay_modes_refines_z_minus_one_via_modes_raw():
    ecb = build_decay_modes(
        _parsed(
            name="Ag-100m",
            modes_raw="ECB+",
            progeny=["Pd-100"],
            branching=[1.0],
            sf_branch=None,
        )
    )
    assert ecb == [{"mode": "EC+B+", "branch": 1.0}]
    ec = build_decay_modes(
        _parsed(name="Ar-37", modes_raw="EC", progeny=["Cl-37"], branching=[1.0], sf_branch=None)
    )
    assert ec == [{"mode": "EC", "branch": 1.0}]


def test_build_decay_modes_single_progeny_sum_one_fallback():
    # Unknown Z-A pattern (A-1) with one progeny and sum~1 -> modes_raw entry.
    modes = build_decay_modes(
        _parsed(name="U-238", modes_raw="n", progeny=["U-237"], branching=[1.0], sf_branch=None)
    )
    assert modes == [{"mode": "n", "branch": 1.0}]


def test_build_decay_modes_ambiguous_multi_progeny_raises():
    with pytest.raises(DataFormatError):
        build_decay_modes(
            _parsed(
                name="U-238",
                modes_raw="weird",
                progeny=["U-237", "Th-234"],
                branching=[0.5, 0.5],
                sf_branch=None,
            )
        )


def test_sha256_file(tmp_path):
    payload = b"abc"
    f = tmp_path / "f.bin"
    f.write_bytes(payload)
    assert sha256_file(f) == hashlib.sha256(payload).hexdigest()


def test_write_json_atomic_roundtrip_and_no_tmp_leftover(tmp_path):
    path = tmp_path / "out.json"
    write_json_atomic(path, {"b": 2, "a": 1})
    assert json.loads(path.read_text(encoding="utf-8")) == {"a": 1, "b": 2}
    write_json_atomic(path, {"a": 3})
    assert json.loads(path.read_text(encoding="utf-8")) == {"a": 3}
    assert list(tmp_path.iterdir()) == [path]


def test_fetch_bytes_verifies_sha256(tmp_path):
    payload = b"icrp-fixture"
    good = hashlib.sha256(payload).hexdigest()
    f = tmp_path / "blob.bin"
    f.write_bytes(payload)
    assert fetch_bytes(f.as_uri(), good) == payload
    with pytest.raises(DataFormatError, match="SHA-256"):
        fetch_bytes(f.as_uri(), "0" * 64)


@pytest.mark.skipif(not ART.exists(), reason="icrp107.json not built yet")
def test_artifact_is_icrp_default_shape():
    cat = json.loads(ART.read_text(encoding="utf-8"))
    assert len(cat) > 1252
    u = cat["U-238"]
    assert u["source"] == "ICRP-107"
    assert u["atomic_mass_u"] == pytest.approx(238.050788, rel=1e-9)
    assert u["is_stable"] is False
    assert u["progeny"] == ["Th-234"]
