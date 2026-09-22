"""DecayChain: the pint-edge domain object over the pure solver kernels."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from pydecay._solver import DEGENERATE_EPS, solve
from pydecay.exceptions import ChainDefinitionError
from pydecay.graph import DecayGraph
from pydecay.nuclide import Nuclide, normalize_nuclide_name
from pydecay.units import mirror_quantity, to_float, to_seconds, ureg


def _resolve_lambda(name: str, lambdas: Mapping[str, float] | None) -> float:
    """Resolve a species' decay constant from an explicit map or bundled data."""
    if lambdas is not None and name in lambdas:
        lam = float(lambdas[name])
        if not math.isfinite(lam) or lam < 0:
            raise ChainDefinitionError(f"invalid lambda for {name!r}: {lam}")
        return lam
    try:
        return Nuclide.load(name).lambda_
    except Exception as exc:
        raise ChainDefinitionError(
            f"no half-life available for {name!r}; pass lambdas={{'{name}': ...}}"
        ) from exc


class DecayChain:
    """A linear or star-branched decay chain evaluated through pydecay's solver.

    Construction validates topology; evaluation is lazy per ``t``. Solver
    dispatch (Bateman vs matrix exponential) is an internal detail.
    """

    def __init__(
        self,
        lambdas: Sequence[float],
        names: Sequence[str] | None = None,
        *,
        eps: float = DEGENERATE_EPS,
    ) -> None:
        """Build a linear chain from decay constants (1/s), parent first."""
        self._graph = DecayGraph.linear(lambdas, names=names)
        self._eps = float(eps)

    @classmethod
    def from_isotopes(cls, names: Sequence[str], *, eps: float = DEGENERATE_EPS) -> DecayChain:
        """Build a linear chain from bundled nuclide names, ordered parent→daughter."""
        if not names:
            raise ChainDefinitionError("from_isotopes requires at least one isotope")
        norms = [normalize_nuclide_name(n) for n in names]
        lams = [Nuclide.load(n).lambda_ for n in norms]
        return cls(lams, norms, eps=eps)

    @classmethod
    def branching(
        cls,
        parent: str,
        branches: Mapping[str, float],
        *,
        lambdas: Mapping[str, float] | None = None,
        eps: float = DEGENERATE_EPS,
    ) -> DecayChain:
        """Build a star chain: one parent feeding terminal daughters by fraction."""
        if not branches:
            raise ChainDefinitionError("branching requires at least one branch")
        p = parent
        daughters = list(branches)
        if p in daughters:
            raise ChainDefinitionError("parent cannot also be a daughter")
        total = sum(float(f) for f in branches.values())
        if not math.isfinite(total) or total > 1.0 + 1e-12 or total < 0:
            raise ChainDefinitionError(
                f"branching fractions must sum to [0, 1], got {total}"
            )
        names = (p, *daughters)
        lam_p = _resolve_lambda(p, lambdas)
        lam_d = [_resolve_lambda(d, lambdas) for d in daughters]
        n = len(names)
        fractions = [[0.0] * n for _ in range(n)]
        for i, frac in enumerate(branches.values(), start=1):
            fractions[0][i] = float(frac)
        graph = DecayGraph.branching(
            (lam_p, *lam_d), [tuple(row) for row in fractions], names=names
        )
        obj = cls.__new__(cls)
        obj._graph = graph
        obj._eps = float(eps)
        return obj

    @property
    def names(self) -> tuple[str, ...]:
        """Species names in graph order."""
        return self._graph.names

    @property
    def lambdas(self) -> tuple[float, ...]:
        """Decay constants in 1/s, graph order."""
        return self._graph.lambdas

    def _init_vector(
        self,
        n0: Sequence[Any] | Mapping[str, Any] | None,
    ) -> tuple[list[float], bool]:
        """Return (canonical n0 list, input_was_quantity)."""
        n = len(self._graph.names)
        if n0 is None:
            vec = [0.0] * n
            vec[0] = 1.0
            return vec, False
        was_quantity = False
        if isinstance(n0, Mapping):
            vec = [0.0] * n
            for key, val in n0.items():
                if key not in self._graph.names:
                    raise ChainDefinitionError(f"unknown species {key!r}")
                idx = self._graph.names.index(key)
                if hasattr(val, "units"):
                    was_quantity = True
                    vec[idx] = to_float(val, "atom")
                else:
                    vec[idx] = float(val)
            return vec, was_quantity
        vals = list(n0)
        if len(vals) != n:
            raise ChainDefinitionError(f"n0 has length {len(vals)}, expected {n}")
        vec = []
        for val in vals:
            if hasattr(val, "units"):
                was_quantity = True
                vec.append(to_float(val, "atom"))
            else:
                vec.append(float(val))
        return vec, was_quantity

    def at(
        self,
        t: float | str | Any = 0,
        *,
        n0: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> dict[str, float] | dict[str, Any]:
        """Atom counts of every species at time ``t``; mirrors ``n0`` kind."""
        t_s = to_seconds(t)
        vec, was_q = self._init_vector(n0)
        result = solve(self._graph, vec, t_s, eps=self._eps)
        if was_q:
            return {
                name: mirror_quantity(float(val), 1 * ureg.atom, "atom")
                for name, val in zip(self.names, result, strict=True)
            }
        return {name: float(val) for name, val in zip(self.names, result, strict=True)}

    def activity(
        self,
        t: float | str | Any = 0,
        *,
        n0: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> dict[str, float] | dict[str, Any]:
        """Activity of every species at time ``t`` in Bq; mirrors ``n0`` kind."""
        atoms: dict[str, Any] = self.at(t, n0=n0)
        out: dict[str, Any] = {}
        for i, name in enumerate(self.names):
            val = atoms[name]
            if hasattr(val, "units"):
                out[name] = mirror_quantity(
                    self.lambdas[i] * float(val.magnitude), val, "becquerel"
                )
            else:
                out[name] = self.lambdas[i] * float(val)
        return out
