"""Species/branching graph and decay generator matrix (spec section 4.2). Pure SI."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from pydecay.exceptions import ChainDefinitionError

_FRACTION_TOL = 1e-12


def _is_linear_pattern(n: int, fractions: tuple[tuple[float, ...], ...]) -> bool:
    for j in range(n):
        for i in range(n):
            expected = 1.0 if i == j + 1 else 0.0
            if abs(fractions[j][i] - expected) > _FRACTION_TOL:
                return False
    return True


@dataclass(frozen=True)
class DecayGraph:
    """A decay topology: decay constants plus branching fractions.

    ``fractions[j][i]`` is the fraction of species j's decays that go to
    species i. Rows summing to < 1 leave the remainder as decay to an
    untracked sink. ``lambdas[j] == 0`` is allowed only for terminal species
    (all-zero row) and denotes a stable nuclide.
    """

    lambdas: tuple[float, ...]
    names: tuple[str, ...]
    fractions: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        """Validate topology lengths, lambda values, and branching-fraction rows."""
        n = len(self.lambdas)
        if n == 0:
            raise ChainDefinitionError("graph must contain at least one species")
        if len(self.names) != n or len(self.fractions) != n:
            raise ChainDefinitionError("lambdas, names, and fractions must have equal length")
        for lam in self.lambdas:
            if not (lam >= 0) or lam == float("inf"):
                raise ChainDefinitionError(f"lambda must be finite and >= 0, got {lam}")
        for j, row in enumerate(self.fractions):
            if len(row) != n:
                raise ChainDefinitionError(f"fractions row {j} must have length {n}")
            row_sum = 0.0
            for i, f in enumerate(row):
                if not (f >= 0) or f == float("inf"):
                    raise ChainDefinitionError(f"fractions[{j}][{i}] must be finite and >= 0")
                row_sum += f
            if row_sum > 1.0 + _FRACTION_TOL:
                raise ChainDefinitionError(
                    f"branching fractions for species {j} sum to {row_sum} > 1"
                )
            if self.lambdas[j] == 0.0 and row_sum > _FRACTION_TOL:
                raise ChainDefinitionError(
                    f"species {j} has lambda = 0 but outgoing branches; "
                    "stable species must be terminal"
                )

    @classmethod
    def linear(
        cls, lambdas: Sequence[float], names: Sequence[str] | None = None
    ) -> DecayGraph:
        """Build an unbranched linear chain 1 → 2 → … → n."""
        lam = tuple(float(x) for x in lambdas)
        n = len(lam)
        if names is None:
            nm = tuple(f"species-{i + 1}" for i in range(n))
        else:
            nm = tuple(names)
        fr = tuple(
            tuple(1.0 if i == j + 1 else 0.0 for i in range(n)) for j in range(n)
        )
        return cls(lambdas=lam, names=nm, fractions=fr)

    @classmethod
    def branching(
        cls,
        lambdas: Sequence[float],
        fractions: Sequence[Sequence[float]],
        names: Sequence[str] | None = None,
    ) -> DecayGraph:
        """Build a graph from an explicit branching-fraction matrix."""
        lam = tuple(float(x) for x in lambdas)
        fr = tuple(tuple(float(x) for x in row) for row in fractions)
        if names is None:
            nm = tuple(f"species-{i + 1}" for i in range(len(lam)))
        else:
            nm = tuple(names)
        return cls(lambdas=lam, names=nm, fractions=fr)

    @property
    def is_branched(self) -> bool:
        """True when the topology is not a plain linear chain."""
        return not _is_linear_pattern(len(self.lambdas), self.fractions)

    def generator(self) -> np.ndarray:
        """Return G such that dN/dt = G @ N (destination rows, source columns)."""
        n = len(self.lambdas)
        G = np.zeros((n, n), dtype=np.float64)
        for j in range(n):
            G[j, j] = -self.lambdas[j]
            for i in range(n):
                if i != j and self.fractions[j][i] > 0.0:
                    G[i, j] += self.lambdas[j] * self.fractions[j][i]
        return G

    def min_separation(self) -> float:
        """Minimum pairwise |lambda_i - lambda_j| (inf for a single species)."""
        n = len(self.lambdas)
        if n < 2:
            return float("inf")
        best = float("inf")
        for i in range(n):
            for j in range(i + 1, n):
                best = min(best, abs(self.lambdas[i] - self.lambdas[j]))
        return best
