"""Tests for the IAEA fetch parser (run against a captured live CSV fixture)."""

import csv
import datetime
from pathlib import Path

import pytest

from pydecay.data._fetch_iaea import half_life_to_seconds, parse_groundstate
from pydecay.exceptions import DataFormatError

FIXTURE = Path(__file__).parent / "fixtures" / "iaea_groundstates_sample.csv"


@pytest.fixture(scope="module")
def sample_record():
    with FIXTURE.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert rows, "fixture must contain at least one CSV data row"
    return rows[0]


def test_fixture_contains_expected_isotope(sample_record):
    assert int(sample_record["z"]) + int(sample_record["n"]) == 131


def test_half_life_units():
    assert half_life_to_seconds("8.02", "d") == pytest.approx(8.02 * 86400.0)
    assert half_life_to_seconds("6.01", "h") == pytest.approx(6.01 * 3600.0)
    assert half_life_to_seconds("5.27", "y") == pytest.approx(5.27 * 31557600.0)
    assert half_life_to_seconds("5.27", "Y") == pytest.approx(5.27 * 31557600.0)
    assert half_life_to_seconds("15", "ms") == pytest.approx(0.015)
    with pytest.raises(DataFormatError):
        half_life_to_seconds("5", "fortnights")
    with pytest.raises(DataFormatError):
        half_life_to_seconds("not-a-number", "d")


def test_parse_groundstate_produces_schema_record(sample_record):
    rec = parse_groundstate(sample_record)
    for key in (
        "half_life_s",
        "atomic_mass_u",
        "decay_modes",
        "source",
        "source_url",
        "fetched",
    ):
        assert key in rec, f"missing {key}"
    assert rec["half_life_s"] > 0
    assert rec["atomic_mass_u"] > 0
    assert rec["source"].startswith("IAEA")
    assert "nds.iaea.org" in rec["source_url"]
    datetime.date.fromisoformat(rec["fetched"])
    assert isinstance(rec["decay_modes"], list)


def test_parse_groundstate_rejects_missing_half_life():
    with pytest.raises(DataFormatError):
        parse_groundstate({"half_life": "", "unit_hl": "y", "z": "53", "n": "78"})
    with pytest.raises(DataFormatError):
        parse_groundstate({"z": "131", "n": "0"})
