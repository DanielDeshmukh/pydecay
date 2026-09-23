"""Inventory cumulative-decays / numbers / time-series cross-diff vs radioactivedecay 0.6.1.

Half-life *data* drift is covered by tests/test_crosscheck.py (REL_TOL=1e-3).
This module compares *Inventory* results with matched scenarios. radioactivedecay
omits stable nuclides from ``cumulative_decays``; pydecay reports ``0.0`` for them.
Time series compares atom numbers (rr ``decay_units='num'``).
"""

from __future__ import annotations

import pytest

rr = pytest.importorskip("radioactivedecay", reason="radioactivedecay not installed")
from radioactivedecay import Inventory as RRInventory  # noqa: E402

from pydecay.inventory import Inventory  # noqa: E402

REL_TOL = 1e-3


def _rel(ours: float, theirs: float) -> float:
    denom = abs(theirs) if abs(theirs) > 1e-30 else 1.0
    return abs(ours - theirs) / denom


def _series_close(ours: float, theirs: float) -> bool:
    """Relative match, or both near zero (rr emits tiny t=0 noise on stable daughters)."""
    if abs(ours) <= 1e-5 and abs(theirs) <= 1e-5:
        return True
    return _rel(ours, theirs) <= REL_TOL


def _assert_cum_match(
    scenario: str,
    contents: dict[str, float],
    t_s: float,
    units: str = "Bq",
) -> None:
    ours = Inventory(contents, units=units).cumulative_decays(t_s)
    theirs = dict(RRInventory(contents, units=units).cumulative_decays(t_s, units="s"))
    for key, their_val in theirs.items():
        name = str(key)
        assert name in ours, f"{scenario}: missing {name} in pydecay cumulative_decays"
        rel = _rel(float(ours[name]), float(their_val))
        assert rel <= REL_TOL, (
            f"{scenario} cumulative_decays[{name}]: ours={ours[name]!r} "
            f"theirs={their_val!r} rel={rel:.3e} t_s={t_s!r} "
            f"pydecay={__import__('pydecay').__version__} "
            f"radioactivedecay={rr.__version__}"
        )
    rr_keys = {str(k) for k in theirs}
    for key, val in ours.items():
        if key not in rr_keys:
            # radioactivedecay omits stable species; pydecay must report 0.0.
            assert float(val) == 0.0, (
                f"{scenario}: unexpected non-zero cumulative for omitted {key}: {val!r}"
            )


def test_cumulative_single_co60():
    """Scenario 1: single Co-60, 1e6 Bq, 10 Julian years."""
    _assert_cum_match("Co-60 single", {"Co-60": 1.0e6}, 10.0 * 31557600.0)


def test_cumulative_linear_sr90_chain():
    """Scenario 2: Sr-90 -> Y-90 -> Zr-90(stable), 30 Julian years."""
    _assert_cum_match("Sr-90 chain", {"Sr-90": 1.0e6}, 30.0 * 31557600.0)


def test_cumulative_branched_i131():
    """Scenario 3: branched I-131 -> Xe-131m/Xe-131, 8 days in seconds."""
    _assert_cum_match("I-131 branched", {"I-131": 1.0e6}, 8.0 * 86400.0)


def test_cumulative_multi_seed():
    """Scenario 4: multi-seed I-131 + Tc-99m, 1 day."""
    _assert_cum_match(
        "multi-seed",
        {"I-131": 1.0e6, "Tc-99m": 1.0e6},
        86400.0,
    )


def test_numbers_match_after_decay():
    """Ingested numbers after decay match radioactivedecay Inventory.numbers()."""
    contents = {"Co-60": 1.0e6}
    t_s = 10.0 * 31557600.0
    ours = Inventory(contents, units="Bq").decay(t_s).numbers()
    theirs = dict(RRInventory(contents, units="Bq").decay(t_s, units="s").numbers())
    for key, their_val in theirs.items():
        name = str(key)
        rel = _rel(float(ours[name]), float(their_val))
        assert rel <= REL_TOL, (
            f"Co-60 numbers[{name}]: ours={ours[name]!r} theirs={their_val!r} "
            f"rel={rel:.3e}"
        )


def _assert_series_match(
    scenario: str,
    contents: dict[str, float],
    t_end_s: float,
    *,
    npoints: int = 21,
    time_scale: str = "linear",
    t_start: float = 0.0,
) -> None:
    """Point-wise atom-number curve equality vs radioactivedecay decay_time_series.

    rr hardcodes log-axis tmin=0.1 and has no t_start; callers must pass
    t_start=0.1 when time_scale='log' so the grids align.
    """
    ours_t, ours_s = Inventory(contents, units="Bq").decay_time_series(
        t_end_s,
        npoints=npoints,
        time_scale=time_scale,
        t_start=t_start,
    )
    theirs_t, theirs_s = RRInventory(contents, units="Bq").decay_time_series(
        t_end_s,
        time_units="s",
        time_scale=time_scale,
        decay_units="num",
        npoints=npoints,
    )
    assert len(ours_t) == len(theirs_t) == npoints
    for i, (a, b) in enumerate(zip(ours_t, theirs_t, strict=True)):
        rel_t = _rel(float(a), float(b))
        assert rel_t <= REL_TOL, (
            f"{scenario} time[{i}]: ours={a!r} theirs={b!r} rel={rel_t:.3e}"
        )
    for key, their_vals in theirs_s.items():
        name = str(key)
        assert name in ours_s, f"{scenario}: missing {name} in pydecay series"
        our_vals = ours_s[name]
        assert len(our_vals) == len(their_vals)
        for i, (o, v) in enumerate(zip(our_vals, their_vals, strict=True)):
            if not _series_close(float(o), float(v)):
                rel = _rel(float(o), float(v))
                raise AssertionError(
                    f"{scenario} series[{name}][{i}]: ours={o!r} theirs={v!r} "
                    f"rel={rel:.3e} t={ours_t[i]!r} "
                    f"pydecay={__import__('pydecay').__version__} "
                    f"radioactivedecay={rr.__version__}"
                )


def test_series_linear_single_co60():
    """Time-series curve: single Co-60, 1e6 Bq, 10 Julian years, linear."""
    _assert_series_match("Co-60 series", {"Co-60": 1.0e6}, 10.0 * 31557600.0)


def test_series_linear_sr90_chain():
    """Time-series curve: Sr-90 -> Y-90 -> Zr-90, 30 Julian years, linear."""
    _assert_series_match("Sr-90 series", {"Sr-90": 1.0e6}, 30.0 * 31557600.0)


def test_series_linear_branched_i131():
    """Time-series curve: branched I-131, 8 days, linear."""
    _assert_series_match("I-131 series", {"I-131": 1.0e6}, 8.0 * 86400.0)


def test_series_linear_multi_seed():
    """Time-series curve: multi-seed I-131 + Tc-99m, 1 day, linear."""
    _assert_series_match(
        "multi-seed series",
        {"I-131": 1.0e6, "Tc-99m": 1.0e6},
        86400.0,
    )


def test_series_log_single_co60():
    """Time-series curve on log axis; t_start=0.1 matches rr hardcoded tmin."""
    _assert_series_match(
        "Co-60 log series",
        {"Co-60": 1.0e6},
        10.0 * 31557600.0,
        time_scale="log",
        t_start=0.1,
    )
