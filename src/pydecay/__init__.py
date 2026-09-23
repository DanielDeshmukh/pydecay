"""pydecay: radioactive decay mathematics.

Analytical single-isotope decay, Bateman/expm decay chains with branching,
IAEA-sourced nuclide data, and unit conversions (Bq/Ci, atoms/grams).
"""

from pydecay.api import decayed_activity, decayed_atoms, remaining_fraction
from pydecay.chain import DecayChain
from pydecay.exceptions import (
    ChainDefinitionError,
    DataFormatError,
    InvalidHalfLifeError,
    InvalidTimeError,
    NuclideNotFoundError,
    PyDecayError,
    UnitError,
)
from pydecay.nuclide import Nuclide

__version__ = "0.2.0"

__all__ = [
    "ChainDefinitionError",
    "DataFormatError",
    "DecayChain",
    "InvalidHalfLifeError",
    "InvalidTimeError",
    "Nuclide",
    "NuclideNotFoundError",
    "PyDecayError",
    "UnitError",
    "__version__",
    "decayed_activity",
    "decayed_atoms",
    "remaining_fraction",
]
