"""Exception hierarchy for pydecay.

All package-raised errors derive from :class:`PyDecayError` so callers can
catch a single base class.
"""


class PyDecayError(Exception):
    """Base class for all pydecay errors."""


class NuclideNotFoundError(PyDecayError):
    """Raised when a nuclide name is not present in the bundled dataset."""


class InvalidHalfLifeError(PyDecayError):
    """Raised when a half-life or decay constant is non-positive or non-finite."""


class InvalidTimeError(PyDecayError):
    """Raised when a time value is negative or non-finite."""


class ChainDefinitionError(PyDecayError):
    """Raised when a decay chain is malformed (empty, bad lengths, bad branching)."""


class UnitError(PyDecayError):
    """Raised when a value cannot be parsed or has the wrong dimension."""


class DataFormatError(PyDecayError):
    """Raised when a bundled data record is missing keys or has bad values."""
