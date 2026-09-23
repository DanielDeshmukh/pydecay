"""Frozen golden values: primary-source half-lives + analytic decay tuples."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pydecay import DecayChain, Nuclide, decayed_activity, remaining_fraction

GOLDEN_PATH = Path(__file__).parent / "golden_values.json"
REQUIRED_ENTRY_KEYS = {"id", "kind", "rel_tol", "source", "note"}
PROVENANCE_OK_PREFIXES = ("IAEA", "NNDC", "analytic", "radioactivedecay")


def _load_golden() -> dict:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def test_golden_file_exists_and_has_schema():
    data = _load_golden()
    assert data["schema_version"] == 1
    assert data["verified_on"]
    assert isinstance(data["entries"], list) and data["entries"]


def test_every_entry_has_required_keys_and_provenance():
    for entry in _load_golden()["entries"]:
        missing = REQUIRED_ENTRY_KEYS - set(entry)
        assert not missing, f"{entry.get('id', '?')} missing {missing}"
        src = entry["source"]
        assert any(src.startswith(p) for p in PROVENANCE_OK_PREFIXES), (
            f"{entry['id']} source must cite IAEA/NNDC/analytic/radioactivedecay, got {src!r}"
        )
        if src.startswith("radioactivedecay"):
            assert "version" in entry["note"].lower() or "0." in entry["note"]


def _ids(kind: str) -> list[str]:
    return [e["id"] for e in _load_golden()["entries"] if e["kind"] == kind]


def _entry(entry_id: str) -> dict:
    for e in _load_golden()["entries"]:
        if e["id"] == entry_id:
            return e
    raise AssertionError(f"missing golden entry {entry_id}")


@pytest.mark.parametrize("entry_id", _ids("nuclide_half_life"))
def test_nuclide_half_life_matches_bundle(entry_id):
    e = _entry(entry_id)
    hl = Nuclide.load(e["nuclide"]).half_life_s
    assert hl == pytest.approx(e["half_life_s"], rel=e["rel_tol"])


@pytest.mark.parametrize("entry_id", _ids("single_activity"))
def test_single_activity(entry_id):
    e = _entry(entry_id)
    got = decayed_activity(e["a0_bq"], Nuclide.load(e["nuclide"]).half_life, e["t_s"])
    assert got == pytest.approx(e["expected_bq"], rel=e["rel_tol"])


@pytest.mark.parametrize("entry_id", _ids("remaining_fraction"))
def test_remaining_fraction(entry_id):
    e = _entry(entry_id)
    if "nuclide" in e:
        hl = Nuclide.load(e["nuclide"]).half_life_s
    else:
        hl = e["half_life_s"]
    got = remaining_fraction(hl, e["t_s"])
    assert got == pytest.approx(e["expected"], rel=e["rel_tol"])


@pytest.mark.parametrize("entry_id", _ids("chain_atoms"))
def test_chain_atoms(entry_id):
    e = _entry(entry_id)
    spec = e["chain"]
    if spec.get("type") == "linear" and "isotopes" in spec:
        chain = DecayChain.from_isotopes(spec["isotopes"])
    elif spec.get("type") == "branching":
        chain = DecayChain.branching(
            spec["parent"],
            spec["branches"],
            lambdas=spec["lambdas"],
        )
    else:
        raise AssertionError(f"unknown chain spec {spec!r}")
    got = chain.at(e["t_s"], n0=e["n0"])
    for name, exp in e["expected"].items():
        assert got[name] == pytest.approx(exp, rel=e["rel_tol"]), (
            f"{entry_id}:{name} got={got[name]!r} expected={exp!r}"
        )
