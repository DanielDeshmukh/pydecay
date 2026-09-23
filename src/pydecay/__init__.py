"""pydecay: radioactive decay mathematics.

Analytical single-isotope decay, Bateman/expm decay chains with branching,
ICRP-107 nuclide data, multi-nuclide inventories with progeny ingrowth,
spectra access, and unit conversions (Bq/Ci, atoms/grams).
"""

from pydecay.api import decayed_activity, decayed_atoms, remaining_fraction
from pydecay.chain import DecayChain
from pydecay.decay import decay_constant, mean_lifetime_s
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
from pydecay.units import atoms_to_grams, bq_to_ci, ci_to_bq, grams_to_atoms, to_seconds

__version__ = "0.4.0"

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
    "atoms_to_grams",
    "beta_spectrum",
    "bq_to_ci",
    "ci_to_bq",
    "decay_constant",
    "decayed_activity",
    "decayed_atoms",
    "emissions",
    "grams_to_atoms",
    "mean_lifetime_s",
    "remaining_fraction",
    "to_seconds",
]
