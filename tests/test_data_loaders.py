"""Tests for cached catalog and lazy RAD/BET loaders in pydecay.data."""

import builtins
import gzip

import pytest

from pydecay.data import load_bet, load_bet_for, load_catalog, load_rad, load_rad_for
from pydecay.exceptions import NuclideNotFoundError


def test_catalog_nonempty():
    assert len(load_catalog()) >= 1252


def test_rad_and_bet_lookup():
    rad = load_rad_for("Ac-223")
    assert rad and "E_MeV" in rad[0]
    with pytest.raises(NuclideNotFoundError):
        load_rad_for("Xx-999")


def test_bet_lookup_and_missing():
    bet = load_bet_for("Ac-226")
    assert len(bet["E_MeV"]) == len(bet["A"])
    with pytest.raises(NuclideNotFoundError):
        load_bet_for("Xx-999")


def test_loaders_are_cached():
    assert load_catalog() is load_catalog()
    assert load_rad() is load_rad()
    assert load_bet() is load_bet()


def test_import_does_not_open_bet(monkeypatch):
    opened: list[str] = []
    real_open = builtins.open
    real_gzip_open = gzip.open

    def spy(path, *args, **kwargs):
        opened.append(str(path))
        return real_open(path, *args, **kwargs)

    def spy_gzip(path, *args, **kwargs):
        opened.append(str(path))
        return real_gzip_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", spy)
    monkeypatch.setattr(gzip, "open", spy_gzip)
    load_catalog.cache_clear()
    load_rad.cache_clear()
    load_bet.cache_clear()
    load_catalog()
    assert not any("bet" in p.lower() for p in opened)
    assert not any("icrp107_rad" in p.lower() for p in opened)
