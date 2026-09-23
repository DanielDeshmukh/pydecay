# Changelog

All notable changes to pydecay are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Full ICRP-107 default catalog (1252 radionuclides + stable endpoints).
- `pydecay.spectra.emissions` / `beta_spectrum` (RAD/BET).
- IAEA 47 retained as differential test fixture only.
- Multi-nuclide `Inventory` with automatic ICRP-107 progeny closure:
  immutable `decay`, `cumulative_decays` (block matrix exponential),
  `decay_time_series` (linear/log grids), and accessors
  (`numbers` / `activities` / `masses` / `total_activity` / `half_lives`).
- `Nuclide.progeny` / `branching` / `is_stable` / `sf_branch` graph fields.
- Top-level export: `from pydecay import Inventory`.
- Cross-checks vs `radioactivedecay` 0.6.1 for inventory numbers,
  cumulative decays, and time-series curves.

### Changed
- `Nuclide.load` / `load_all` now read `icrp107.json` (version 0.2.0).

## [0.1.1] - 2026-09-23

### Fixed
- Package metadata author fields: hatchling now emits
  `Author: Daniel Deshmukh` and `Author-email: deshmukhdaniel2005@gmail.com`
  (name and email are separate `authors` entries). Guarded by
  `tests/test_packaging.py`.

## [0.1.0] - 2026-09-22

### Added
- Single-isotope analytical decay (`decayed_atoms`, `decayed_activity`,
  `remaining_fraction`) with pint-aware inputs.
- Linear and star-branched decay chains (`DecayChain`) with guarded Bateman
  closed form and `scipy.linalg.expm` fallback for degenerate lambdas.
- Bundled IAEA Live Chart nuclide dataset (47 isotopes) with per-record
  provenance (`source`, `source_url`, `fetched`).
- Unit conversions: Bq <-> Ci, atoms <-> grams, time parsing.
- Differential cross-check suite against `radioactivedecay` (ICRP-107).
- Golden-values regression suite (`tests/golden/`) with primary-source provenance.
- Solver-output cross-diff vs `radioactivedecay` (single isotope, linear chain, branching).
- Hypothesis invariant tests for decay laws and chains.
- CI coverage floor `--cov-fail-under=90` on the test job.
