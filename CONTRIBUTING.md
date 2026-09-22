# Contributing to pydecay

## Workflow (strict TDD)

1. Write a failing test that names the behavior you want.
2. Run it; confirm it fails for the right reason.
3. Implement the minimum to pass.
4. Run the full gate: `pytest`, `ruff check src tests`, `mypy src`.
5. Commit with conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).

No production code lands without a failing test first (exceptions: config
boilerplate and documentation).

## Data rules

- Never hand-type half-life values. Regenerate
  `src/pydecay/data/nuclides.json` with
  `python -m pydecay.data._fetch_iaea` (network required).
- Every record must carry `source`, `source_url`, and `fetched`.
- If bundled values disagree with a secondary source, IAEA wins; document any
  accepted evaluation drift in `docs/data-sources.md` with both values.

## Math rules

- Ground truth is the technical reference
  (`docs/superpowers/specs/2026-09-22-pydecay-design.md`), whose formulas
  cite Bateman (1910), Cetnar (2006), Krane, BIPM, and NIST SP 811.
- Degenerate-lambda and branching behavior must route through `expm`; never
  ship an unguarded Bateman formula.

## Docs

`mkdocs serve` locally; `mkdocs build --strict` must pass. Diagrams are
mermaid blocks in `docs/architecture.md`.
