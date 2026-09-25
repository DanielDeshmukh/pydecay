"""NIST XCOM fetcher parse + bundle tests (no network by default)."""

import gzip
import json
from pathlib import Path

import pytest

from pydecay.data._fetch_nist import parse_xcom_text, validate_payload

FIXTURE = Path(__file__).parent / "fixtures" / "dose" / "nist_mu_slice.json"


def test_parse_xcom_text_rows():
    text = "1.00000E-02  4.00000E+00\n1.50000E-02  2.50000E+00\n"
    rows = parse_xcom_text(text)
    assert rows[0][0] == pytest.approx(1e-2)
    assert rows[0][1] == pytest.approx(4.0)
    assert len(rows) == 2


def test_validate_payload_requires_all_materials():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # slice fixture has only lead; validate against full REQUIRED set should fail
    with pytest.raises(Exception):  # noqa: B017 - deliberately broad per task brief
        validate_payload(payload)


def test_bundled_gzip_roundtrip():
    raw = Path("src/pydecay/data/nist_mu.json.gz").read_bytes()
    data = json.loads(gzip.decompress(raw))
    assert set(data["materials"]) >= {
        "lead", "iron", "water", "concrete", "aluminum", "air", "polyethylene",
    }
    assert data["source"].startswith("NIST")
