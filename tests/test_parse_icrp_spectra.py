"""Unit tests for ICRP RAD/BET converters (CSV fixtures, no network)."""

import csv
from pathlib import Path

from pydecay.data._fetch_icrp import bet_from_rows, rad_from_rows

FIXTURES = Path(__file__).parent / "fixtures" / "icrp"


def test_rad_sample_shape():
    rows = list(csv.DictReader((FIXTURES / "rad_sample.csv").open(encoding="utf-8")))
    rad = rad_from_rows(rows)
    assert "Ac-223" in rad
    assert rad["Ac-223"][0]["E_MeV"] >= 0
    assert "prob" in rad["Ac-223"][0]


def test_bet_sample_shape():
    rows = list(csv.DictReader((FIXTURES / "bet_sample.csv").open(encoding="utf-8")))
    bet = bet_from_rows(rows)
    assert bet
    first = next(iter(bet.values()))
    assert len(first["E_MeV"]) == len(first["A"])
