"""Solver-output cross-diff vs radioactivedecay 0.6.1 (design spec sections 4-5).

Half-life *data* drift is covered by tests/test_crosscheck.py.
This module compares *decay results* with matched decay constants.
"""

from __future__ import annotations

import math

import pytest

rr = pytest.importorskip("radioactivedecay", reason="radioactivedecay not installed")
from radioactivedecay import Inventory  # noqa: E402

from pydecay import DecayChain, decayed_activity  # noqa: E402

REL_TOL_SOLVER = 1e-6
REL_TOL_ANALYTIC = 1e-9


# copied from tests/test_crosscheck.py to avoid package layout change
def _rr_half_life_s(name: str) -> float:
    """Half-life in seconds from radioactivedecay (copied from test_crosscheck)."""
    nuc = rr.Nuclide(name)
    method = getattr(nuc, "half_life", None)
    if callable(method):
        return float(method(units="s"))
    raise AssertionError(f"cannot locate half-life on radioactivedecay.Nuclide({name})")


def test_single_isotope_activity_matches_inventory():
    """Scenario 1: Co-60, 1e6 Bq, 10 Julian years in seconds -- matched T_half.

    Both sides use ``units='s'`` so radioactivedecay's year_conv cannot
    inject a ~1e-5 relative error that would falsely fail REL_TOL_SOLVER.
    """
    hl_rr = _rr_half_life_s("Co-60")
    t_s = 10.0 * 31557600.0
    ours = decayed_activity(1.0e6, hl_rr, t_s)
    inv = Inventory({"Co-60": 1.0e6}, units="Bq")
    theirs = float(dict(inv.decay(t_s, units="s").activities())["Co-60"])
    rel = abs(ours - theirs) / theirs
    assert rel <= REL_TOL_SOLVER, (
        f"single Co-60 activity mismatch: ours={ours!r} theirs={theirs!r} "
        f"rel={rel:.3e} hl_rr={hl_rr!r} t_s={t_s!r} "
        f"pydecay={__import__('pydecay').__version__} "
        f"radioactivedecay={rr.__version__}"
    )


def test_linear_chain_atoms_match_inventory():
    """Scenario 2: Sr-90 -> Y-90 -> Zr-90(stable), parent-only, 30 Julian years in s."""
    t_s = 30.0 * 31557600.0
    hl_sr = _rr_half_life_s("Sr-90")
    hl_y = _rr_half_life_s("Y-90")
    chain = DecayChain([math.log(2) / hl_sr, math.log(2) / hl_y, 0.0],
                       names=["Sr-90", "Y-90", "Zr-90"])
    ours = chain.at(t_s, n0={"Sr-90": 1.0, "Y-90": 0.0, "Zr-90": 0.0})
    inv0 = Inventory({"Sr-90": 1.0e6}, units="Bq")
    theirs_parent0 = float(dict(inv0.numbers())["Sr-90"])
    theirs_nums = dict(inv0.decay(t_s, units="s").numbers())
    for name in ("Sr-90", "Y-90", "Zr-90"):
        a = ours[name]  # n0 parent atoms = 1.0
        b = float(theirs_nums.get(name, 0.0)) / theirs_parent0
        denom = b if b > 1e-30 else 1e-30
        rel = abs(a - b) / denom
        assert rel <= REL_TOL_SOLVER, (
            f"chain {name}: ours_frac={a!r} theirs_frac={b!r} rel={rel:.3e} "
            f"t_s={t_s!r} rr={rr.__version__}"
        )


def test_branching_star_matches_closed_form():
    """Scenario 3: synthetic P->D1/D2 star vs Bateman-star closed form.

    radioactivedecay 0.6.1 cannot inject custom lambdas into Inventory;
    external formula is the oracle (design section 5 call-site confirmation).
    """
    lp, ld1, ld2 = 0.1, 0.05, 0.02
    t = 10.0
    chain = DecayChain.branching(
        "P", {"D1": 0.6, "D2": 0.4}, lambdas={"P": lp, "D1": ld1, "D2": ld2}
    )
    got = chain.at(t)

    def daughter_atoms(f: float, lam_p: float, lam_d: float) -> float:
        return f * lam_p / (lam_d - lam_p) * (math.exp(-lam_p * t) - math.exp(-lam_d * t))

    exp_p = math.exp(-lp * t)
    exp_d1 = daughter_atoms(0.6, lp, ld1)
    exp_d2 = daughter_atoms(0.4, lp, ld2)
    for name, exp in (("P", exp_p), ("D1", exp_d1), ("D2", exp_d2)):
        rel = abs(got[name] - exp) / exp
        assert rel <= REL_TOL_ANALYTIC, (
            f"branch {name}: got={got[name]!r} expected={exp!r} rel={rel:.3e}"
        )
