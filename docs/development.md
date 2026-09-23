# Development

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -e ".[dev,test,docs]"
```

Requires Python >= 3.10.

## Strict TDD workflow

Same five steps as in `CONTRIBUTING.md` at the repository root:

1. Write a failing test that names the behavior you want.
2. Run it; confirm it fails for the right reason.
3. Implement the minimum to pass.
4. Run the full gate (commands below).
5. Commit with conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).

No production code lands without a failing test first (exceptions: config
boilerplate and documentation).

## Quality gates

Run from the repository root (PowerShell examples; drop `.venv\` prefix if
the venv is active):

| Gate | Command | Expect |
|---|---|---|
| Tests | `.venv\Scripts\python.exe -m pytest` | all pass |
| Coverage | `.venv\Scripts\python.exe -m pytest --cov=pydecay --cov-report=term-missing` | `TOTAL` >= 90 (`fail_under = 90` in `pyproject.toml`) |
| Lint | `.venv\Scripts\python.exe -m ruff check src tests examples` | All checks passed |
| Types | `.venv\Scripts\python.exe -m mypy src` | Success |
| Docs | `.venv\Scripts\python.exe -m mkdocs build --strict` | no warnings; `site/` produced |

Local docs preview:

```bash
mkdocs serve
```

## Data regeneration (network required)

Never hand-type half-life values. Regenerate the ICRP-107 catalog with:

```bash
python -m pydecay.data._fetch_icrp --ndx-path path/to/ICRP-07.NDX
```

- SHA-256 pins verified before any artifact is written (see
  `src/pydecay/data/_fetch_icrp.py`).
- Spectra: `python -m pydecay.data._fetch_icrp --spectra` (requires
  `pip install -e ".[icrp]"` for `pyreadr`).
- Every record must carry `source`, `source_url`, and `fetched`.
- IAEA Live Chart is the **differential test oracle only**
  (`tests/fixtures/iaea_nuclides_47.json`).
- Document any accepted evaluation drift in
  [`Data sources`](data-sources.md) with both values.

The fetch scripts are build-time tools and are excluded from the wheel
(`[tool.hatch.build.targets.wheel] exclude` in `pyproject.toml`).

## CI layout

`.github/workflows/ci.yml` runs three jobs on pushes / PRs to `main`:

| Job | What |
|---|---|
| `lint` | Python 3.12: `ruff check src tests`, `mypy` |
| `test` | Matrix **3.10 / 3.11 / 3.12 / 3.13**: `pytest --cov=pydecay` |
| `docs` | Python 3.12: `mkdocs build --strict` |

## Project layout

```text
src/pydecay/          # package (api, chain, decay, graph, _solver, units, nuclide, spectra, exceptions)
src/pydecay/data/     # icrp107.json + RAD/BET gzip + _fetch_*.py (build-time, not in wheel)
tests/                # pytest suite (known values, units, data, chains, cross-check, golden)
examples/             # runnable scripts
docs/                 # MkDocs pages (this site)
mkdocs.yml            # site config
```
