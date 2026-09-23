# Changelog

All notable changes to pydecay are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
