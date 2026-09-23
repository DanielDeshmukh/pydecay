"""pydecay: radioactive decay mathematics.

Analytical single-isotope decay, Bateman/expm decay chains with branching,
ICRP-107 nuclide data, multi-nuclide inventories with progeny ingrowth,
spectra access, and unit conversions (Bq/Ci, atoms/grams).
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
from pydecay.inventory import Inventory
from pydecay.nuclide import Nuclide
from pydecay.spectra import beta_spectrum, emissions

__version__ = "0.2.0"

__all__ = [
    "ChainDefinitionError",
    "DataFormatError",
    "DecayChain",
    "InvalidHalfLifeError",
    "InvalidTimeError",
    "Inventory",
    "Nuclide",
    "NuclideNotFoundError",
    "PyDecayError",
    "UnitError",
    "__version__",
    "beta_spectrum",
    "decayed_activity",
    "decayed_atoms",
    "emissions",
    "remaining_fraction",
]
