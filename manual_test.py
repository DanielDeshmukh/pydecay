"""Manual smoke test of the pydecay public API. Run: python manual_test.py"""

from __future__ import annotations

import sys

import pint

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

import pydecay
from pydecay import DecayChain, Nuclide, decayed_activity, decayed_atoms, remaining_fraction
from pydecay.exceptions import InvalidHalfLifeError, NuclideNotFoundError, PyDecayError
from pydecay.units import bq_to_ci, ci_to_bq, to_seconds

ureg = pint.UnitRegistry()
PASS = 0
FAIL = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {label}")
    else:
        FAIL += 1
        print(f"  FAIL  {label}  {detail}")


print(f"pydecay {pydecay.__version__}  exports={len(pydecay.__all__)}")

print("\n[1] single-isotope analytical decay")
half_life_s = 8.0
N0 = 1_000_000.0
check("N(t=T1/2)=N0/2", abs(decayed_atoms(N0, half_life_s, 8.0) - N0 / 2) < 1e-6)
check("N(0)=N0", abs(decayed_atoms(N0, half_life_s, 0.0) - N0) < 1e-9)
check("remaining(2T1/2)=0.25", abs(remaining_fraction(half_life_s, 16.0) - 0.25) < 1e-12)
check("A(t=T1/2)=A0/2", abs(decayed_activity(500.0, half_life_s, 8.0) - 250.0) < 1e-9)

print("\n[2] unit-mirrored inputs (pint)")
t_q = 8.0 * ureg.second
check("half-life as Quantity", abs(decayed_atoms(N0, half_life_s * ureg.second, t_q) - N0 / 2) < 1e-6)
check("half-life as '8 s' string", abs(decayed_atoms(N0, "8 s", "8 s") - N0 / 2) < 1e-6)
check("to_seconds(year)", abs(to_seconds(1.0 * ureg.year) - 31557600.0) < 1.0)

print("\n[3] nuclide data (IAEA-sourced)")
co60 = Nuclide.load("Co-60")
print(f"  n(Co-60) half_life_s={co60.half_life_s:.6g}")
check(
    "Co-60 half-life ~ 1.6634e8 s",
    abs(co60.half_life_s - 1.6634e8) / 1.6634e8 < 1e-3,
    str(co60.half_life_s),
)
check("Co-60 half_life property is Quantity", abs(float(co60.half_life.to("second").m) - co60.half_life_s) < 1e-6)
all_nuclides = Nuclide.load_all()
for name in ("Co-60", "Cs-137", "I-131", "C-14", "U-238", "Tc-99m"):
    check(f"{name} bundled", name in all_nuclides)
check("dataset size >= 47", len(all_nuclides) >= 47, f"got {len(all_nuclides)}")

print("\n[4] linear chain Sr-90 -> Y-90")
try:
    chain = DecayChain.from_isotopes(["Sr-90", "Y-90"])
    check("from_isotopes builds linear chain", chain.names == ("Sr-90", "Y-90"), str(chain.names))
    out = chain.at(30.0 * ureg.year)
    check("at() returns dict of Quantities", isinstance(out, dict) and len(out) == 2, str(out))
    check("parent decreased", float(out["Sr-90"]) < float(chain.at(0.0)["Sr-90"]), str(out))
    act = chain.activity(0.0)
    check("activity() returns dict", isinstance(act, dict) and len(act) == 2, str(act))
except Exception as e:  # noqa: BLE001
    check("linear chain runs", False, repr(e))

print("\n[5] branching chain (Co-60 style not bundled as chain; use synthetic branching)")
try:
    b = DecayChain.branching(
        parent="P",
        branches={"D1": 0.6, "D2": 0.4},
        lambdas={"P": 0.1, "D1": 0.01, "D2": 0.02},
    )
    bout = b.at(10.0 * ureg.second)
    check("branching at() returns 3 nodes", isinstance(bout, dict) and len(bout) == 3, str(bout))
    check("branching values non-negative", all(float(v) >= 0 for v in bout.values()), str(bout))
    check("parent decayed", float(bout["P"]) < 1.0, str(bout))
except TypeError as e:
    check("branching()", False, f"signature issue: {e}")
except Exception as e:  # noqa: BLE001
    check("branching runs", False, repr(e))

print("\n[6] unit conversions")
check("bq_to_ci(3.7e10)=1", abs(bq_to_ci(3.7e10) - 1.0) < 1e-12)
check("ci_to_bq(1)=3.7e10", abs(ci_to_bq(1.0) - 3.7e10) < 1.0)
check("roundtrip", abs(bq_to_ci(ci_to_bq(2.5)) - 2.5) < 1e-12)

print("\n[7] exception paths")
try:
    decayed_atoms(100.0, -1.0, 1.0)
    check("negative half-life raises InvalidHalfLifeError", False, "no exception")
except InvalidHalfLifeError:
    check("negative half-life raises InvalidHalfLifeError", True)
except PyDecayError as e:
    check("negative half-life raises InvalidHalfLifeError", False, type(e).__name__)

try:
    Nuclide.load("Xx-999")
    check("unknown nuclide raises NuclideNotFoundError", False, "no exception")
except NuclideNotFoundError:
    check("unknown nuclide raises NuclideNotFoundError", True)
except PyDecayError as e:
    check("unknown nuclide raises NuclideNotFoundError", False, type(e).__name__)

print(f"\n{PASS} passed, {FAIL} failed")
raise SystemExit(1 if FAIL else 0)
