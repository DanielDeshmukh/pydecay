"""ICRP-07.NDX fixed-width parser tests (spec sections 3, 6)."""

import json
from pathlib import Path

import pytest

from pydecay.data._parse_icrp import (
    BRANCH_SUM_ABS_TOL,
    NDX_EXPECTED_COUNT,
    half_life_to_seconds_icrp,
    parse_ndx_line,
    parse_ndx_text,
)
from pydecay.exceptions import DataFormatError

FIXTURE = Path(__file__).parent / "fixtures" / "icrp" / "ICRP-07.NDX.head"
GOLDEN = Path(__file__).parent / "fixtures" / "icrp" / "ICRP-07.NDX.golden_slice.json"


def test_spec_constants_locked_to_plan():
    assert NDX_EXPECTED_COUNT == 1252
    assert BRANCH_SUM_ABS_TOL == 0.035


def test_head_fixture_parses_all_records():
    text = FIXTURE.read_text(encoding="iso-8859-1")
    records, meta = parse_ndx_text(text)
    assert meta["header"]
    assert len(records) == 5
    assert meta["record_count"] == 5


def test_head_records_invariants():
    text = FIXTURE.read_text(encoding="iso-8859-1")
    records, _ = parse_ndx_text(text)
    # Branch-sum enforcement (all NDX floats incl. SF, before split) lives in the
    # parser; do not re-check the sum here against 1.0 after the SF split.
    for rec in records:
        assert rec["name"]
        assert rec["half_life_s"] > 0
        assert len(rec["progeny"]) == len(rec["branching"])
        assert "SF" not in rec["progeny"]
        assert rec["atomic_mass_u"] > 0


def test_ac223_first_line_from_real_file():
    # First data line in production NDX (probed 2026-09-23); parse head line 1
    # rather than a hand-built line.
    head_lines = FIXTURE.read_text(encoding="iso-8859-1").splitlines()
    rec = parse_ndx_line(head_lines[1])
    assert rec["name"] == "Ac-223"
    assert rec["half_life_raw"] == "2.10"
    assert rec["half_life_units"] == "m"
    assert rec["half_life_s"] == pytest.approx(2.10 * 60.0)
    assert rec["modes_raw"] == "A"
    assert rec["progeny"] == ["Fr-219"]
    assert rec["branching"] == [pytest.approx(0.99)]
    assert rec["sf_branch"] is None
    assert rec["atomic_mass_u"] == pytest.approx(223.019136)
    assert "SF" not in rec["progeny"]


def test_half_life_units():
    assert half_life_to_seconds_icrp("8.02070", "d") == pytest.approx(8.02070 * 86400.0)
    assert half_life_to_seconds_icrp("4.468E+9", "y") == pytest.approx(4.468e9 * 31557600.0)
    assert half_life_to_seconds_icrp("6.015", "h") == pytest.approx(6.015 * 3600.0)
    with pytest.raises(DataFormatError):
        half_life_to_seconds_icrp("1.0", "fortnight")
    with pytest.raises(DataFormatError):
        half_life_to_seconds_icrp("nope", "y")


def test_parse_ndx_line_rejects_bad_length():
    with pytest.raises(DataFormatError):
        parse_ndx_line("Ac-223 not a real NDX line")


def test_branch_sum_out_of_tolerance_raises():
    # Head line 1 carries branch 9.9000E-01; lowering it puts the all-floats
    # sum (pre SF-split) outside BRANCH_SUM_ABS_TOL.
    head_lines = FIXTURE.read_text(encoding="iso-8859-1").splitlines()
    line = head_lines[1].replace("9.9000E-01", "5.0000E-01")
    assert line != head_lines[1]
    assert len(line) == 226
    with pytest.raises(DataFormatError):
        parse_ndx_line(line)


def test_u238_sf_split_from_golden_slice():
    if not GOLDEN.exists():
        pytest.skip("golden slice added with full NDX build in Task 2")
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    u238 = next(r for r in data["records"] if r["name"] == "U-238")
    assert u238["progeny"] == ["Th-234"]
    assert u238["branching"] == [pytest.approx(1.0)]
    assert u238["sf_branch"] == pytest.approx(5.45e-7)
    assert u238["atomic_mass_u"] == pytest.approx(238.050788, rel=1e-9)
    assert u238["half_life_s"] == pytest.approx(4.468e9 * 31557600.0, rel=1e-12)
