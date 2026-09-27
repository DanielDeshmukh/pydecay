"""Extract, execute, and output-verify every recipe in docs/cookbook.md.

Each recipe is a ```python block tagged ``# recipe: <slug>`` followed by a
```text block declaring its expected stdout. This test executes every block
(no exceptions allowed) and asserts the captured stdout matches the
declared output line for line, so the cookbook can never drift from the
code it documents.
"""

from __future__ import annotations

import contextlib
import io
import re
import warnings
from pathlib import Path

import pytest

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")

COOKBOOK = Path(__file__).resolve().parents[1] / "docs" / "cookbook.md"
BLOCK_RE = re.compile(r"```(python|text)\n(.*?)```", re.S)
SLUG_RE = re.compile(r"^# recipe: ([a-z0-9-]+)$", re.M)

REQUIRED_RECIPES = [
    "remaining-activity",
    "chain-at-t",
    "decay-series",
    "dose-conversions",
    "hvl-sizing",
    "multilayer-wall",
    "csv-decay-table",
    "unit-conversions",
    "plot-decay-curve",
    "error-handling",
]


def _pairs() -> list[tuple[str, str, str]]:
    """Return (slug, code, expected_stdout) for each recipe, in file order."""
    text = COOKBOOK.read_text(encoding="utf-8")
    matches = list(BLOCK_RE.finditer(text))
    pairs: list[tuple[str, str, str]] = []
    for i, match in enumerate(matches):
        if match.group(1) != "python":
            continue
        assert i + 1 < len(matches), "python block has no following block"
        following = matches[i + 1]
        assert following.group(1) == "text", (
            "every recipe python block must be followed by a text output block"
        )
        slug_match = SLUG_RE.search(match.group(2))
        assert slug_match, "recipe block missing '# recipe: <slug>' marker"
        pairs.append((slug_match.group(1), match.group(2), following.group(2)))
    return pairs


PAIRS = _pairs()
SLUGS = [slug for slug, _, _ in PAIRS]


def test_recipe_set_is_complete():
    assert SLUGS == REQUIRED_RECIPES, (
        f"cookbook recipes drifted: found {SLUGS}, expected {REQUIRED_RECIPES}"
    )


@pytest.mark.parametrize("slug,code,expected", PAIRS, ids=SLUGS)
def test_recipe_executes_and_output_matches(
    slug: str, code: str, expected: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    buffer = io.StringIO()
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="FigureCanvasAgg is non-interactive")
        with contextlib.redirect_stdout(buffer):
            exec(compile(code, f"<recipe {slug}>", "exec"), {})
    got = [line.rstrip() for line in buffer.getvalue().splitlines()]
    want = [line.rstrip() for line in expected.splitlines()]
    while want and not want[-1]:
        want.pop()
    assert got == want, f"recipe {slug!r} output drifted:\n  got:  {got}\n  want: {want}"
