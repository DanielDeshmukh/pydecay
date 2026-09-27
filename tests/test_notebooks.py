"""Execute the tutorial notebooks end-to-end and verify their GOLDEN_CHECK lines.

Requires the ``tutorials`` extra (``nbclient``, ``ipykernel``); skips when the
harness is not installed. Each notebook must:

* carry concept markdown cells with cited sources (>= 5 markdown cells, >= 1
  URL),
* contain an ``answer``-tagged code cell for the exercise,
* execute cleanly under nbclient (no cell errors), and
* print a ``GOLDEN_CHECK {json}`` line whose values match the pinned entries
  in ``tests/golden/golden_values.json`` within each entry's ``rel_tol``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

nbformat = pytest.importorskip("nbformat")
pytest.importorskip("nbclient")
pytest.importorskip("ipykernel")
pytest.importorskip("matplotlib")

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = REPO_ROOT / "notebooks"
GOLDEN_PATH = REPO_ROOT / "tests" / "golden" / "golden_values.json"
GOLDEN_CHECK_PREFIX = "GOLDEN_CHECK "
CELL_TIMEOUT_S = 120

# notebook filename -> {golden entry id: golden field the notebook prints}
NOTEBOOK_GOLDENS: dict[str, dict[str, str]] = {
    "01_decay_basics.ipynb": {
        "i131_halflife_iaea": "half_life_s",
        "co60_halflife_iaea": "half_life_s",
        "co60_activity_10y": "expected_bq",
        "c14_fraction_5730y": "expected",
    },
    "02_inventory_chains.ipynb": {
        "sr90_y90_atoms_30y": "expected",
        "branch_p_d1_d2_10s": "expected",
    },
    "03_dose_rates.ipynb": {
        "co60_kerma_1mbq_1m": "expected",
        "co60_ambient_1mbq_1m": "expected",
        "dose_inverse_square_identity": "expected",
    },
    "04_shielding_design.ipynb": {
        "hvl_half_intensity_identity": "expected",
        "slab_double_thickness_identity": "expected",
    },
}


def _notebook_paths() -> list[Path]:
    return sorted(NOTEBOOK_DIR.glob("*.ipynb"))


NOTEBOOKS = _notebook_paths()


def _golden_entries() -> dict[str, dict[str, Any]]:
    return {e["id"]: e for e in json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))["entries"]}


def _cell_text(cell: Any) -> str:
    src = cell.get("source", "")
    return "".join(src) if isinstance(src, list) else src


def _stdout_text(nb: Any) -> str:
    chunks: list[str] = []
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        for out in cell.get("outputs", []):
            if out.get("output_type") == "stream" and out.get("name") == "stdout":
                text = out.get("text", "")
                chunks.append("".join(text) if isinstance(text, list) else text)
    return "".join(chunks)


def _close(got: Any, expected: Any, rel_tol: float, ctx: str) -> None:
    if isinstance(expected, dict):
        assert isinstance(got, dict), f"{ctx}: expected mapping, got {type(got)}"
        assert set(got) == set(expected), f"{ctx}: keys {sorted(got)} != {sorted(expected)}"
        for key, exp in expected.items():
            assert got[key] == pytest.approx(exp, rel=rel_tol), f"{ctx}:{key} got={got[key]!r}"
    else:
        assert got == pytest.approx(expected, rel=rel_tol), (
            f"{ctx}: got={got!r} expected={expected!r}"
        )


def test_notebook_set_is_complete():
    assert [p.name for p in NOTEBOOKS] == sorted(NOTEBOOK_GOLDENS), (
        f"notebook set drifted: found {[p.name for p in NOTEBOOKS]}, "
        f"expected {sorted(NOTEBOOK_GOLDENS)}"
    )


def test_golden_ids_for_notebooks_exist():
    entries = _golden_entries()
    for nb_name, mapping in NOTEBOOK_GOLDENS.items():
        for entry_id in mapping:
            assert entry_id in entries, f"{nb_name} references unknown golden {entry_id!r}"


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_structure(path: Path) -> None:
    nb = nbformat.read(path, as_version=4)
    md_cells = [c for c in nb.cells if c.cell_type == "markdown"]
    md_text = "\n".join(_cell_text(c) for c in md_cells)
    assert len(md_cells) >= 5, f"{path.name}: need >=5 markdown cells, got {len(md_cells)}"
    assert "http" in md_text, f"{path.name}: markdown cells must cite at least one URL"
    answer_cells = [
        c
        for c in nb.cells
        if c.cell_type == "code" and "answer" in c.get("metadata", {}).get("tags", [])
    ]
    assert answer_cells, f"{path.name}: missing answer-tagged exercise cell"
    code_text = "\n".join(_cell_text(c) for c in nb.cells if c.cell_type == "code")
    assert "pydecay" in code_text, f"{path.name}: must exercise the public pydecay API"
    assert GOLDEN_CHECK_PREFIX.strip() in code_text, f"{path.name}: missing GOLDEN_CHECK cell"


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_executes(path: Path) -> None:
    from nbclient import NotebookClient

    nb = nbformat.read(path, as_version=4)
    client = NotebookClient(
        nb,
        timeout=CELL_TIMEOUT_S,
        kernel_name="python3",
        resources={"metadata": {"path": str(path.parent)}},
    )
    client.execute()

    stdout = _stdout_text(nb)
    payloads = [
        json.loads(line[len(GOLDEN_CHECK_PREFIX) :])
        for line in stdout.splitlines()
        if line.startswith(GOLDEN_CHECK_PREFIX)
    ]
    assert payloads, f"{path.name}: no GOLDEN_CHECK line printed during execution"

    entries = _golden_entries()
    field_map = NOTEBOOK_GOLDENS[path.name]
    seen: set[str] = set()
    for payload in payloads:
        assert isinstance(payload, dict), f"{path.name}: GOLDEN_CHECK payload must be an object"
        for entry_id, value in payload.items():
            assert entry_id in field_map, f"{path.name}: unexpected golden {entry_id!r}"
            entry = entries[entry_id]
            _close(
                value,
                entry[field_map[entry_id]],
                entry["rel_tol"],
                f"{path.name}:{entry_id}",
            )
            seen.add(entry_id)
    assert seen == set(field_map), (
        f"{path.name}: GOLDEN_CHECK missing {sorted(set(field_map) - seen)}"
    )
