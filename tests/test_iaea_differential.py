"""IAEA 47 fixture vs runtime ICRP half-lives (independent oracle)."""

import json
from pathlib import Path

from pydecay.nuclide import Nuclide

IAEA = Path(__file__).parent / "fixtures" / "iaea_nuclides_47.json"
# Measured class of drift (IAEA vs ICRP evaluations); start from documented
# accepted-deviation ceiling in docs/data-sources.md and tighten after first run.
REL_TOL_DATA = 1.5e-2


def test_overlap_half_lives_within_tolerance(capsys):
    iaea = json.loads(IAEA.read_text(encoding="utf-8"))
    worst = 0.0
    worst_name = None
    failures = []
    for name, rec in iaea.items():
        ours = Nuclide.load(name).half_life_s
        theirs = float(rec["half_life_s"])
        rel = abs(ours - theirs) / theirs
        if rel > worst:
            worst, worst_name = rel, name
        if rel > REL_TOL_DATA:
            failures.append((name, rel, theirs, ours))
    with capsys.disabled():
        print(f"worst {worst_name} {worst:.3e}")
    assert not failures, (
        f"half-life drift beyond {REL_TOL_DATA}: "
        f"{[(n, r) for n, r, _, _ in failures]}"
    )
