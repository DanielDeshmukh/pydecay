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
