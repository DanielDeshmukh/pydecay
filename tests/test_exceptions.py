"""Tests for the pydecay exception hierarchy."""

import pytest

from pydecay.exceptions import (
    ChainDefinitionError,
    DataFormatError,
    InvalidHalfLifeError,
    InvalidTimeError,
    NuclideNotFoundError,
    PyDecayError,
    UnitError,
)


@pytest.mark.parametrize(
    "exc_cls",
    [
        NuclideNotFoundError,
        InvalidHalfLifeError,
        InvalidTimeError,
        ChainDefinitionError,
        UnitError,
        DataFormatError,
    ],
)
def test_all_errors_subclass_pydecay_error(exc_cls):
    assert issubclass(exc_cls, PyDecayError)
    assert issubclass(exc_cls, Exception)


def test_errors_carry_message():
    with pytest.raises(InvalidTimeError, match="must be"):
        raise InvalidTimeError("time must be >= 0")
