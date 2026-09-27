"""Generate landingpage/src/data/decayNuclides.ts from pydecay's ICRP-107 catalog.

Run from anywhere:

    python landingpage/scripts/generate_decay_nuclides.py

The output is consumed by the DECAY playground tab. Stable endpoints
(is_stable=True, half_life_s=inf) are excluded because they have no decay
curve. Every function in this module is covered by
tests/test_landing_generator.py.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[2]

try:
    from pydecay import Nuclide
except ImportError:  # running without the package installed
    sys.path.insert(0, str(ROOT / "src"))
    from pydecay import Nuclide

DAY_S = 86400.0
YEAR_D = 365.2422

# IUPAC element names for every symbol that can appear in an ICRP-107 id.
SYMBOL_NAMES: dict[str, str] = {
    "H": "Hydrogen", "He": "Helium", "Li": "Lithium", "Be": "Beryllium",
    "B": "Boron", "C": "Carbon", "N": "Nitrogen", "O": "Oxygen",
    "F": "Fluorine", "Ne": "Neon", "Na": "Sodium", "Mg": "Magnesium",
    "Al": "Aluminium", "Si": "Silicon", "P": "Phosphorus", "S": "Sulfur",
    "Cl": "Chlorine", "Ar": "Argon", "K": "Potassium", "Ca": "Calcium",
    "Sc": "Scandium", "Ti": "Titanium", "V": "Vanadium", "Cr": "Chromium",
    "Mn": "Manganese", "Fe": "Iron", "Co": "Cobalt", "Ni": "Nickel",
    "Cu": "Copper", "Zn": "Zinc", "Ga": "Gallium", "Ge": "Germanium",
    "As": "Arsenic", "Se": "Selenium", "Br": "Bromine", "Kr": "Krypton",
    "Rb": "Rubidium", "Sr": "Strontium", "Y": "Yttrium", "Zr": "Zirconium",
    "Nb": "Niobium", "Mo": "Molybdenum", "Tc": "Technetium", "Ru": "Ruthenium",
    "Rh": "Rhodium", "Pd": "Palladium", "Ag": "Silver", "Cd": "Cadmium",
    "In": "Indium", "Sn": "Tin", "Sb": "Antimony", "Te": "Tellurium",
    "I": "Iodine", "Xe": "Xenon", "Cs": "Cesium", "Ba": "Barium",
    "La": "Lanthanum", "Ce": "Cerium", "Pr": "Praseodymium", "Nd": "Neodymium",
    "Pm": "Promethium", "Sm": "Samarium", "Eu": "Europium", "Gd": "Gadolinium",
    "Tb": "Terbium", "Dy": "Dysprosium", "Ho": "Holmium", "Er": "Erbium",
    "Tm": "Thulium", "Yb": "Ytterbium", "Lu": "Lutetium", "Hf": "Hafnium",
    "Ta": "Tantalum", "W": "Tungsten", "Re": "Rhenium", "Os": "Osmium",
    "Ir": "Iridium", "Pt": "Platinum", "Au": "Gold", "Hg": "Mercury",
    "Tl": "Thallium", "Pb": "Lead", "Bi": "Bismuth", "Po": "Polonium",
    "At": "Astatine", "Rn": "Radon", "Fr": "Francium", "Ra": "Radium",
    "Ac": "Actinium", "Th": "Thorium", "Pa": "Protactinium", "U": "Uranium",
    "Np": "Neptunium", "Pu": "Plutonium", "Am": "Americium", "Cm": "Curium",
    "Bk": "Berkelium", "Cf": "Californium", "Es": "Einsteinium", "Fm": "Fermium",
    "Md": "Mendelevium", "No": "Nobelium", "Lr": "Lawrencium",
    "Rf": "Rutherfordium", "Db": "Dubnium", "Sg": "Seaborgium",
    "Bh": "Bohrium", "Hs": "Hassium", "Mt": "Meitnerium", "Ds": "Darmstadtium",
    "Rg": "Roentgenium", "Cn": "Copernicium", "Nh": "Nihonium",
    "Fl": "Flerovium", "Mc": "Moscovium", "Lv": "Livermorium",
    "Ts": "Tennessine", "Og": "Oganesson",
}

_ID_RE = re.compile(r"^([A-Z][a-z]?)-\d+[a-z]?$")
_EXP_RE = re.compile(r"e([+-])(\d+)")


def fmt_float(value: float) -> str:
    """Format a float the way JS/prettier expects: e18 and e-5, never e+18 or e-05."""

    def repl(match: re.Match[str]) -> str:
        sign = match.group(1)
        digits = match.group(2).lstrip("0") or "0"
        return f"e{sign}{digits}" if sign == "-" else f"e{digits}"

    return _EXP_RE.sub(repl, repr(value))


class Row(NamedTuple):
    """One generated record for the landing-page select."""

    id: str
    element: str
    days: float
    time_unit: str
    days_per_unit: float
    display: str


def time_unit(days: float) -> tuple[str, float, str]:
    """Classify a half-life in days into (unit, days_per_unit, display)."""
    if days < 1:
        hours = days * 24
        return "hours", 1 / 24, f"{hours:.4g} hours"
    if days < YEAR_D / 2:
        return "days", 1.0, f"{days:.6g} days"
    years = days / YEAR_D
    display = f"{years:.4g}".replace("e+0", "e")
    return "years", YEAR_D, f"{display} years"


def element_name(symbol: str) -> str:
    """Map a chemical symbol to its element name; unknown symbols pass through."""
    return SYMBOL_NAMES.get(symbol, symbol)


def build_rows() -> list[Row]:
    """Load the ICRP-107 catalog and return sorted rows for all radionuclides."""
    rows: list[Row] = []
    for nuclide in Nuclide.load_all().values():
        if nuclide.is_stable:
            continue
        days = nuclide.half_life_s / DAY_S
        if not (days > 0):
            raise ValueError(f"{nuclide.name}: non-positive half-life {nuclide.half_life_s}")
        match = _ID_RE.match(nuclide.name)
        if match is None:
            raise ValueError(f"{nuclide.name}: id does not match [A-Z][a-z]?-N")
        unit, per_unit, display = time_unit(days)
        rows.append(
            Row(nuclide.name, element_name(match.group(1)), days, unit, per_unit, display)
        )
    rows.sort(key=lambda row: row.id)
    return rows


def render(rows: list[Row]) -> str:
    """Render rows as the TypeScript source for decayNuclides.ts."""
    lines = [
        "// GENERATED by landingpage/scripts/generate_decay_nuclides.py - do not edit.",
        'import type { DemoNuclide } from "./nuclides";',
        "",
        "export const decayNuclides: DemoNuclide[] = [",
    ]
    for row in rows:
        lines += [
            "  {",
            f'    id: "{row.id}",',
            f'    element: "{row.element}",',
            f"    halfLifeDays: {fmt_float(row.days)},",
            f'    displayHalfLife: "{row.display}",',
            f'    timeUnit: "{row.time_unit}",',
            f"    daysPerUnit: {fmt_float(row.days_per_unit)},",
            "  },",
        ]
    lines.append("];")
    return "\n".join(lines) + "\n"


def output_path() -> Path:
    """Absolute path of the generated TypeScript file."""
    return ROOT / "landingpage" / "src" / "data" / "decayNuclides.ts"


def main() -> None:
    """Write decayNuclides.ts and print a summary."""
    rows = build_rows()
    target = output_path()
    target.write_text(render(rows), encoding="utf-8", newline="\n")
    print(f"wrote {len(rows)} radionuclides -> {target}")


if __name__ == "__main__":
    main()
