"""Tests for the public pydecay.spectra API."""

import pytest

from pydecay.exceptions import DataFormatError, NuclideNotFoundError
from pydecay.spectra import beta_spectrum, emissions


def test_emissions_known_nuclide():
    rows = emissions("Ac-223")
    assert rows
    assert "E_MeV" in rows[0]
    assert rows[0]["E_MeV"] >= 0


def test_emissions_unknown_nuclide():
    with pytest.raises(NuclideNotFoundError):
        emissions("Xx-999")


def test_beta_spectrum_lengths_and_nonneg():
    energies, amps = beta_spectrum("Ac-226")
    assert len(energies) == len(amps)
    assert energies
    assert all(e >= 0 for e in energies)


def test_beta_spectrum_unknown_nuclide():
    with pytest.raises(NuclideNotFoundError):
        beta_spectrum("Xx-999")


def test_beta_spectrum_missing_for_stable():
    # O-16 is in the catalog as stable and has no BET rows.
    with pytest.raises(DataFormatError):
        beta_spectrum("O-16")


def test_emissions_missing_for_stable():
    with pytest.raises(DataFormatError):
        emissions("O-16")
