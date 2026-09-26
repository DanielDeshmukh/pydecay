"""pydecay: radioactive decay mathematics.

Analytical single-isotope decay, Bateman/expm decay chains with branching,
ICRP-107 nuclide data, multi-nuclide inventories with progeny ingrowth,
spectra access, unit conversions (Bq/Ci, atoms/grams), instantaneous
rate / ODE residual helpers, point-source dose rates, and narrow-beam
shielding (HVL/TVL, Beer-Lambert transmission).
"""

from pydecay.api import (
    da_dt,
    decay_ode_residual,
    decayed_activity,
    decayed_atoms,
    dn_dt,
    dose_rate,
    remaining_fraction,
)
from pydecay.chain import DecayChain
from pydecay.decay import decay_constant, mean_lifetime_s
from pydecay.dose import air_kerma_rate, exposure_rate
from pydecay.exceptions import (
    ChainDefinitionError,
    DataFormatError,
    DoseDataError,
    InvalidHalfLifeError,
    InvalidTimeError,
    MaterialError,
    NuclideNotFoundError,
    PyDecayError,
    UnitError,
)
from pydecay.inventory import Inventory
from pydecay.materials import available_materials, material
from pydecay.nuclide import Nuclide
from pydecay.shielding import (
    hvl,
    hvl_slab,
    mu_from_material,
    multilayer_transmit,
    transmit,
    transmit_slab,
    tvl,
    tvl_slab,
)
from pydecay.spectra import beta_spectrum, emissions
from pydecay.units import atoms_to_grams, bq_to_ci, ci_to_bq, grams_to_atoms, to_seconds

__version__ = "0.6.0"

__all__ = [
    "ChainDefinitionError",
    "DataFormatError",
    "DecayChain",
    "DoseDataError",
    "InvalidHalfLifeError",
    "InvalidTimeError",
    "Inventory",
    "MaterialError",
    "Nuclide",
    "NuclideNotFoundError",
    "PyDecayError",
    "UnitError",
    "__version__",
    "air_kerma_rate",
    "atoms_to_grams",
    "available_materials",
    "beta_spectrum",
    "bq_to_ci",
    "ci_to_bq",
    "da_dt",
    "decay_constant",
    "decay_ode_residual",
    "decayed_activity",
    "decayed_atoms",
    "dn_dt",
    "dose_rate",
    "emissions",
    "exposure_rate",
    "grams_to_atoms",
    "hvl",
    "hvl_slab",
    "material",
    "mean_lifetime_s",
    "mu_from_material",
    "multilayer_transmit",
    "remaining_fraction",
    "to_seconds",
    "transmit",
    "transmit_slab",
    "tvl",
    "tvl_slab",
]
