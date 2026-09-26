"""Build ``dose_coefficients.json`` from the locked Task-4 curation table.

Run as ``python -m pydecay.data._curate_dose`` to (re)write the bundle.

Provenance (also recorded row-by-row in the JSON):

* Gamma (``gamma_R_m2_h_per_Ci``): Lauridsen, B. (1982) "Table of Exposure
  Rate Constants and Dose Equivalent Rate Constants", Risoe National
  Laboratory, Risoe-M No. 2322, Table 4 - nuclear photon lines only,
  X-rays and photons below 30 keV omitted (report section 1).
* ``gamma_R_cm2_mCi_h`` = 10 x the Risoe value (1 R.m2/h/Ci =
  10 R.cm2/mCi/h) - the plan's Task-5 point-source formula works in
  mCi/cm, so the field named ``gamma_R_cm2_mCi_h`` stores true
  R.cm2.mCi-1.h-1 units.
* Bucket-2 fallbacks (U-235, Pu-239, Ge-68): ICRP-107 Annex A photon
  emission probabilities (E >= 30 keV) via the same validated formula
  (K = 19.54, Risoe Table 1 mu_en/rho); mirrors the Risoe energy cut.
* ``h_star_over_ka``: ICRP Publication 74 (1996) Table A.21,
  H*(10)/Ka (Sv/Gy) for monoenergetic photons 10 keV - 10 MeV,
  as reproduced in IAEA (R.V. Griffith) "Quantities and Units for
  External Dose Assessment", Table III. ICRP-103/ICRP-116 do not
  tabulate H*(10)/Ka vs energy, hence ICRP-74 is the exact source.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_RISO_SOURCE = (
    "Lauridsen B. (1982) Risoe-M-2322 (Risoe National Laboratory) Table 4; "
    "nuclear photons only, X-rays and <30 keV omitted (sec. 1)"
)
_BUCKET2_SOURCE = (
    "ICRP-107 Annex A photon emission probabilities (E >= 30 keV) via the "
    "validated Risoe-M-2322 formula (K=19.54, Risoe Table 1 mu_en/rho); "
    "mirrors the Risoe sec. 1 energy cut"
)
_H_STAR_SOURCE = (
    "ICRP Publication 74 (1996) Table A.21, H*(10)/Ka (Sv/Gy), monoenergetic "
    "photons 10 keV-10 MeV; values as reproduced in IAEA (R.V. Griffith) "
    "'Quantities and Units for External Dose Assessment', Table III"
)

# (nuclide, gamma_R_m2_h_per_Ci, pdf page, printed page, evidence)
_RISO_ROWS: list[tuple[str, float, str, str, str]] = [
    ("Am-241", 0.0121, "422", "418", "text layer, n=2"),
    ("At-211", 0.0010, "399", "395", "text layer, n=1"),
    ("Ba-133", 0.2024, "195", "191", "text layer, n=9"),
    ("Bi-214", 0.7460, "400", "396", "text layer, n=51"),
    ("Co-57", 0.0548, "37", "33", "text layer, n=3"),
    ("Co-60", 1.2987, "39", "35", "image, n=2 lines"),
    ("Cs-137", 0.3224, "203", "199", "text layer, n=1 (137Cs+137Ba m row)"),
    ("Eu-152", 0.5983, "253-254", "249-250", "image, n=42"),
    ("F-18", 0.5895, "25", "21", "text layer, n=1"),
    ("Ga-68", 0.5455, "47", "43", "text layer, n=3"),
    ("I-125", 0.0039, "171", "167", "text layer, n=1 (35.492 keV)"),
    ("I-131", 0.2158, "186", "182", "text layer, n=9"),
    ("In-111", 0.2039, "150", "146", "text layer, n=2"),
    ("Ir-192", 0.4581, "351", "347", "text layer, n=17"),
    ("K-40", 0.0779, "29", "25", "text layer, n=1"),
    ("Kr-85", 0.0013, "82", "78", "text layer, n=1"),
    ("Lu-177", 0.0160, "317", "313", "text layer, n=5"),
    ("Mn-54", 0.4681, "36", "32", "text layer, n=1"),
    ("Na-22", 1.1882, "26", "22", "text layer, n=2"),
    ("Pb-210", 0.0016, "398", "394", "image, n=1 (OCR corrected 46.503)"),
    ("Pb-214", 0.1294, "400", "396", "text layer, n=13"),
    ("Ra-226", 0.8782, "403-404", "399-400",
     "image, n=64 (+da row; sum-checked vs Bi-214+Pb-214+bare)"),
    ("Rb-82", 0.6247, "75", "71", "text layer, n=4"),
    ("Se-75", 0.2056, "61", "57", "text layer, n=9"),
    ("Tc-99m", 0.0590, "127", "123", "image, n=1 (140.466 keV)"),
    ("Th-232", 0.0001, "411", "407", "text layer, n=1 (printed 4 dp)"),
    ("Tl-201", 0.0105, "373", "369", "text layer, n=5 (ground state)"),
    ("U-238", 0.0085, "419", "415", "image, n=1 (49.550 keV)"),
    ("Xe-133", 0.0136, "195", "191", "text layer, n=2"),
    ("Yb-175", 0.0209, "310", "306", "text layer, n=5"),
    ("Zn-65", 0.3105, "43", "39", "text layer, n=2"),
]

# Bucket-2 fallback (nuclide, gamma_R_m2_h_per_Ci, note)
_BUCKET2_ROWS: list[tuple[str, float, str]] = [
    ("Ge-68", 0.5466, "chain total 0.546590; Risoe 68 Ga row 0.5455 cross-check (+0.20%)"),
    ("Pu-239", 0.000037, "chain total >=30 keV; no Risoe row exists"),
    ("U-235", 0.0802, "chain total 0.080174; no Risoe 235 U row; 235 Pa row self-check -0.29%"),
]

# Bucket-1 omissions (nuclide, reason) - photon-free; dose API raises DoseDataError.
_OMITTED: dict[str, str] = {
    "C-14": "pure beta emitter, no photon rows in Risoe-M-2322 Table 4",
    "Fe-55": "no photon emission >=30 keV (EC daughter Mn-55 X-rays excluded by Risoe sec. 1)",
    "H-3": "pure beta emitter, no photon rows in Risoe-M-2322 Table 4",
    "Po-210": "no photon emission >=30 keV (803 keV gamma branch absent from Risoe table)",
    "Sr-90": "pure beta emitter (Y-90 daughter has no gamma; ground-state Y-90 omitted)",
    "Y-90": "ground state is photon-free; the only Risoe Y-90 row is the 3.190 h isomer",
}

# ICRP-74 Table A.21: H*(10)/Ka (Sv/Gy) for monoenergetic photons.
_H_STAR_E_MEV: list[float] = [
    0.010, 0.015, 0.020, 0.030, 0.040, 0.050, 0.060, 0.080, 0.100, 0.150,
    0.200, 0.300, 0.400, 0.500, 0.600, 0.800, 1.000, 1.500, 2.000, 3.000,
    4.000, 5.000, 6.000, 8.000, 10.000,
]
_H_STAR_FACTOR: list[float] = [
    0.008, 0.26, 0.61, 1.10, 1.47, 1.67, 1.74, 1.72, 1.65, 1.49,
    1.40, 1.31, 1.26, 1.23, 1.21, 1.19, 1.17, 1.15, 1.14, 1.13,
    1.12, 1.11, 1.11, 1.11, 1.10,
]


def _to_cm2(raw: float) -> float:
    """Convert R.m2/h/Ci to true R.cm2/mCi/h (x10) without float noise."""
    return round(raw * 10, 10)


def build_payload() -> dict[str, Any]:
    """Return the full dose_coefficients.json payload."""
    rows: dict[str, Any] = {}
    for name, raw, pdf, printed, evidence in _RISO_ROWS:
        rows[name] = {
            "gamma_R_cm2_mCi_h": _to_cm2(raw),
            "gamma_R_m2_h_per_Ci": raw,
            "source": _RISO_SOURCE,
            "table": "Risoe-M-2322 Table 4",
            "page": f"printed {printed} (PDF {pdf})",
            "evidence": evidence,
        }
    for name, raw, note in _BUCKET2_ROWS:
        rows[name] = {
            "gamma_R_cm2_mCi_h": _to_cm2(raw),
            "gamma_R_m2_h_per_Ci": raw,
            "source": _BUCKET2_SOURCE,
            "table": "ICRP-107 Annex A",
            "page": "-",
            "evidence": note,
        }
    return {
        "source": _RISO_SOURCE,
        "fetched": "2026-09-26",
        "description": (
            "Point-source exposure-rate constants for the pydecay core-40 "
            "nuclides. Coefficients are nuclear-photon emission values; "
            "X-rays and photons below 30 keV are omitted (Risoe-M-2322 sec. 1). "
            "gamma_R_cm2_mCi_h stores true R.cm2.mCi-1.h-1 (= 10 x the "
            "Risoe R.m2/h/Ci value); gamma_R_m2_h_per_Ci keeps the verbatim "
            "source value for provenance."
        ),
        "units": {
            "gamma_R_cm2_mCi_h": "R.cm2.mCi-1.h-1",
            "gamma_R_m2_h_per_Ci": "R.m2.h-1.Ci-1",
            "h_star_over_ka": "Sv.Gy-1",
        },
        "rows": dict(sorted(rows.items())),
        "omitted": dict(sorted(_OMITTED.items())),
        "h_star_over_ka": {
            "E_MeV": _H_STAR_E_MEV,
            "factor": _H_STAR_FACTOR,
            "source": _H_STAR_SOURCE,
        },
    }


def main() -> None:
    """Write dose_coefficients.json next to this module."""
    out = Path(__file__).resolve().parent / "dose_coefficients.json"
    out.write_text(json.dumps(build_payload(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
