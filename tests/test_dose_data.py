"""dose_coefficients.json schema and loader tests."""

import json
from pathlib import Path

from pydecay import _dose_data

SLICE = Path(__file__).parent / "fixtures" / "dose" / "dose_coefficients_slice.json"


def test_slice_schema_fields():
    payload = json.loads(SLICE.read_text(encoding="utf-8"))
    for name, row in payload["rows"].items():
        assert "gamma_R_cm2_mCi_h" in row, name
        assert row.get("source"), name


def test_bundle_contains_core_nuclides():
    payload = _dose_data.load_dose_coefficients()
    for name in ("Co-60", "Cs-137", "I-131", "Tc-99m"):
        assert name in payload["rows"]


def test_h_star_table_present_and_monotone():
    payload = _dose_data.load_dose_coefficients()
    ks = payload["h_star_over_ka"]
    assert len(ks["E_MeV"]) == len(ks["factor"])
    assert ks["factor"][0] > 0
