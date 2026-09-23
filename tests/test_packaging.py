"""Package metadata guard: Author / Author-email must stay split.

Hatchling folds a single ``{ name, email }`` author entry into
``Author-email: Name <email>`` and leaves ``Author`` empty. ``pip show``
then displays the name only under Author-email. Keep name and email in
separate author entries so metadata renders as:

    Author: Daniel Deshmukh
    Author-email: deshmukhdaniel2005@gmail.com
"""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"

EXPECTED_AUTHOR_NAME = "Daniel Deshmukh"
EXPECTED_AUTHOR_EMAIL = "deshmukhdaniel2005@gmail.com"


def _project() -> dict:
    with PYPROJECT.open("rb") as fh:
        data = tomllib.load(fh)
    return data["project"]


def _build_wheel(tmpdir: str) -> Path:
    """Build a wheel into ``tmpdir`` and return the wheel path."""
    import glob
    import subprocess

    root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "-o", tmpdir],
        cwd=root,
        check=True,
        capture_output=True,
    )
    wheels = glob.glob(str(Path(tmpdir) / "*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, got {wheels}"
    return Path(wheels[0])


def test_authors_name_and_email_are_separate_entries():
    authors = _project()["authors"]
    names = [a.get("name") for a in authors if "name" in a]
    emails = [a.get("email") for a in authors if "email" in a]

    assert EXPECTED_AUTHOR_NAME in names, (
        f"Author name {EXPECTED_AUTHOR_NAME!r} missing from pyproject authors; got {names}"
    )
    assert EXPECTED_AUTHOR_EMAIL in emails, (
        f"Author email {EXPECTED_AUTHOR_EMAIL!r} missing from pyproject authors; got {emails}"
    )


def test_no_author_entry_combines_name_and_email():
    """A combined entry is what hatchling folds into Author-email only."""
    for entry in _project()["authors"]:
        assert not ("name" in entry and "email" in entry), (
            "authors entry must not set both name and email in one object "
            f"(hatchling will emit Author-email only): {entry}"
        )


def test_author_email_has_no_display_name_wrapper():
    for entry in _project()["authors"]:
        email = entry.get("email")
        if email is None:
            continue
        assert "<" not in email and ">" not in email, (
            f"email field must be a bare address, not Name <email>: {email!r}"
        )


def test_wheel_excludes_fetch_scripts_and_keeps_icrp_assets(tmp_path):
    """Wheel ships ICRP catalog/license and omits network fetch helpers."""
    import zipfile

    wheel = _build_wheel(str(tmp_path))
    with zipfile.ZipFile(wheel) as zf:
        names = zf.namelist()
    assert any(n.endswith("pydecay/data/icrp107.json") for n in names)
    assert any(n.endswith("pydecay/data/LICENSE.ICRP-07") for n in names)
    assert any(n.endswith("pydecay/data/icrp107_rad.json.gz") for n in names)
    assert any(n.endswith("pydecay/data/icrp107_bet.json.gz") for n in names)
    assert not any("_fetch_icrp.py" in n for n in names)
    assert not any("_fetch_iaea.py" in n for n in names)


def test_wheel_size_budget(tmp_path):
    """Hard fail if the wheel exceeds the 15 MB budget."""
    wheel = _build_wheel(str(tmp_path))
    size = wheel.stat().st_size
    assert size <= 15_000_000, f"wheel size {size} exceeds 15 MB budget"
