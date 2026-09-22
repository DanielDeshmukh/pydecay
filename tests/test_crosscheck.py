"""Differential cross-check against radioactivedecay (ICRP-107).

Reports relative drift for every overlapping nuclide; fails only beyond
REL_TOL. Skipped entirely when radioactivedecay is not installed.
"""

import pytest

rr = pytest.importorskip("radioactivedecay", reason="radioactivedecay not installed")

from pydecay.nuclide import Nuclide  # noqa: E402

REL_TOL = 1e-3

# Controller ruling (Task 11): IAEA Live Chart vs ICRP-107 published evaluation
# differences (both value sets in .superpowers/sdd/.../task-11-report.md; to be
# documented in docs/data-sources.md at Task 12). REL_TOL stays locked — any
# nuclide outside this set must still land within REL_TOL.
ACCEPTED_DEVIATIONS = frozenset(
    {
        "Ar-39",
        "C-11",
        "Cs-137",
        "I-123",
        "K-40",
        "Kr-85",
        "Pa-234m",
        "Ra-224",
        "S-35",
        "Sr-90",
        "Tc-99m",
        "Th-230",
        "Th-232",
        "Tl-201",
    }
)


def _rr_half_life_s(name: str) -> float:
    """Adapter: radioactivedecay half-life in seconds (attribute from Task 11 Step 1 probe).

    Probe (radioactivedecay 0.6.1): ``Nuclide.half_life`` is a *method*
    ``half_life(units='s') -> float``; there is no ``half_life_seconds``
    attribute and no pint Quantity.
    """
    nuc = rr.Nuclide(name)
    if hasattr(nuc, "half_life_seconds") and nuc.half_life_seconds is not None:
        val = nuc.half_life_seconds
        if hasattr(val, "to"):  # pint Quantity
            return float(val.to("second").magnitude)
        return float(val)
    method = getattr(nuc, "half_life", None)
    if callable(method):
        return float(method(units="s"))
    raise AssertionError(f"cannot locate half-life on radioactivedecay.Nuclide({name})")


def _rr_known_names() -> set[str]:
    """Best-effort name inventory of the radioactivedecay dataset.

    Probe (radioactivedecay 0.6.1): ``DecayData()`` requires positional
    args; the preloaded default is ``rr.DEFAULTDATA`` whose ``nuclides``
    is a numpy ndarray of name strings (not a dict).
    """
    dd = getattr(rr, "DEFAULTDATA", None)
    if dd is not None:
        try:
            inner = getattr(dd, "nuclides", None)
            if inner is not None:
                return {str(x) for x in inner}
        except Exception:  # fall through to mandatory-six probe
            pass
    data = getattr(rr, "DecayData", None)
    if data is not None:
        try:
            dd = data()
            inner = getattr(dd, "nuclides", None) or getattr(dd, "_nuclides", None)
            if isinstance(inner, dict):
                return set(inner)
        except Exception:  # fall through to mandatory-six probe
            pass
    return {"Co-60", "Cs-137", "I-131", "C-14", "U-238", "Tc-99m"}


def test_overlap_nonempty():
    overlap = set(Nuclide.load_all()) & set(_rr_known_names())
    assert len(overlap) >= 6


def test_half_life_drift_within_tolerance(capsys):
    ours = Nuclide.load_all()
    names = sorted(set(ours) & set(_rr_known_names()))
    assert names, "no overlapping nuclides to compare"
    failures = []
    with capsys.disabled():
        print(f"\nhalf-life drift vs radioactivedecay (ICRP-107), REL_TOL={REL_TOL}:")
        for name in names:
            a = ours[name].half_life_s
            b = _rr_half_life_s(name)
            rel = abs(a - b) / b
            if rel <= REL_TOL:
                flag = "OK  "
            elif name in ACCEPTED_DEVIATIONS:
                flag = "ACCP"
            else:
                flag = "FAIL"
            print(f"  {flag} {name:10s} pydecay={a:.6e}s  rr={b:.6e}s  rel={rel:.3e}")
            if rel > REL_TOL and name not in ACCEPTED_DEVIATIONS:
                failures.append((name, rel))
    assert not failures, f"half-life drift beyond {REL_TOL}: {failures}"
