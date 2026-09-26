# Changelog

All notable changes to pydecay are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.6.0] - 2026-09-24

### Added
- Point-source air-kerma and exposure dose rates (`dose_rate`, `exposure_rate`, `air_kerma_rate`)
  with curated per-nuclide coefficients and optional ambient H*(10) quantity.
- Narrow-beam shielding: `mu`, `hvl`, `tvl`, `transmit`, `transmit_slab`, `multilayer_transmit`
  backed by bundled NIST XCOM attenuation tables for seven materials.
- `Inventory.dose_rate()` composing per-nuclide rates.
- New exceptions: `DoseDataError`, `MaterialError`.

## [0.5.1] - 2026-09-24

### Changed
- Docs: clarify ICRP-107 catalog counting method — 1252 radionuclides +
  246 stable progeny endpoints = 1498 records (README, user guide,
  `docs/data-sources.md`, landing page). Stable endpoints are graph
  end-caps, not duplicate nuclides or decay-mode rows.
- Docs: fix citation label `ICRP-07 DATA` → `ICRP-107 DATA` in the
  landing-page docs masthead and footer (real filenames such as
  `LICENSE.ICRP-07` are unchanged).

## [0.5.0] - 2026-09-23

### Added
- Instantaneous rate helpers: `dn_dt(N, half_life)` (atoms/s) and
  `da_dt(A0, half_life, time)` (Bq/s) as top-level exports.
- `decay_ode_residual(N, half_life, *, dn_dt_value=None)` — ODE residual
  `dN/dt + λN`; analytic default is exactly 0, optional numerical
  derivative for verification.
- Pure kernels in `pydecay.decay`: `dn_dt`, `da_dt`, `ode_residual`.
- `Inventory.instantaneous_rates()` — joint `dN_i/dt = G @ N` for the
  full progeny closure, mirroring constructor kind.

## [0.4.0] - 2026-09-23

### Added
- Top-level re-exports of existing unit and decay helpers (same names as
  their home submodules): `to_seconds`, `bq_to_ci`, `ci_to_bq`,
  `atoms_to_grams`, `grams_to_atoms`, `decay_constant`, `mean_lifetime_s`.
  `__all__` grows from 16 to 23 names. No behavioural changes — pure
  additive surface expansion.

## [0.3.0] - 2026-09-23

### Added
- Multi-nuclide `Inventory` with automatic ICRP-107 progeny closure:
  immutable `decay`, `cumulative_decays` (block matrix exponential),
  `decay_time_series` (linear/log grids), and accessors
  (`numbers` / `activities` / `masses` / `total_activity` / `half_lives`).
- `Nuclide.progeny` / `branching` / `is_stable` / `sf_branch` graph fields.
- Top-level export: `from pydecay import Inventory`.
- Cross-checks vs `radioactivedecay` 0.6.1 for inventory numbers,
  cumulative decays, and time-series curves.
- Hypothesis property invariants for `Inventory` (composition, conservation,
  immutability, cumulative balance, series endpoints).

### Changed
- `Nuclide.lambda_` / `Nuclide.activity` on stable or infinite half-life now
  return `0.0` / `0 Bq` (needed for progeny end-caps). The free function
  `decay.decay_constant(inf)` still raises `InvalidHalfLifeError`.
- `decay_time_series` argument errors (`npoints`, `time_scale`) raise
  `PyDecayError` instead of bare `ValueError`, restoring the documented
  "all package errors derive from `PyDecayError`" contract.
- Catalog branching rows that sum slightly above 1 (ICRP rounding noise,
  within 0.035) are renormalized when building an `Inventory` closure so
  every non-stable seed can construct (previously ~17% raised
  `ChainDefinitionError`).

### Fixed
- Solver accepts and zeros tiny negative atom counts (~1e-16 numerical noise
  on stable end-caps) so chained `Inventory.decay` stays composable;
  `Inventory.decay` also clamps stored state to `>= 0`.

## [0.2.0] - 2026-09-23

### Added
- Full ICRP-107 default catalog (1252 radionuclides + stable endpoints).
- `pydecay.spectra.emissions` / `beta_spectrum` (RAD/BET).
- IAEA 47 retained as differential test fixture only.

### Changed
- `Nuclide.load` / `load_all` now read `icrp107.json`.

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
