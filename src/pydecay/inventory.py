"""Multi-nuclide inventory with automatic progeny closure (spec section 5)."""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.linalg import expm  # type: ignore[import-untyped]

from pydecay._solver import DEGENERATE_EPS, solve
from pydecay.exceptions import (
    ChainDefinitionError,
    InvalidTimeError,
    PyDecayError,
    UnitError,
)
from pydecay.graph import DecayGraph
from pydecay.nuclide import Nuclide, normalize_nuclide_name
from pydecay.units import (
    CI_IN_BQ,
    atoms_to_grams,
    grams_to_atoms,
    mirror_quantity,
    to_float,
    to_seconds,
    ureg,
)

_MAX_CLOSURE_DEPTH = 256
"""Defense-in-depth cap on progeny BFS depth (catalog chains are far shorter)."""

_BRANCH_ROW_SUM_TOL = 0.035
"""Allowed overshoot when catalog branching rows sum slightly above 1 (ICRP noise)."""

_UNITS_ALIASES: dict[str, str] = {
    "bq": "Bq",
    "ci": "Ci",
    "atoms": "atoms",
    "atom": "atoms",
    "g": "g",
    "gram": "g",
    "grams": "g",
}

_PINT_TARGET: dict[str, str] = {
    "Bq": "Bq",
    "Ci": "Ci",
    "atoms": "atom",
    "g": "gram",
}


def _normalize_units(units: str) -> str:
    """Return the canonical unit label (``Bq``/``Ci``/``atoms``/``g``)."""
    if not isinstance(units, str):
        raise UnitError(f"units must be a string, got {type(units).__name__}")
    key = units.strip().lower()
    if key not in _UNITS_ALIASES:
        raise UnitError(f"unsupported units {units!r}; expected one of 'Bq', 'Ci', 'atoms', 'g'")
    return _UNITS_ALIASES[key]


def _entry_to_atoms(name: str, value: Any, units: str, nuc: Nuclide) -> float:
    """Convert one inventory entry (plain number or Quantity) to atom counts."""
    if isinstance(value, str):
        raise UnitError(f"amount for {name!r} must be a number or Quantity, got string {value!r}")
    if hasattr(value, "units"):
        amount = to_float(value, _PINT_TARGET[units])
    else:
        try:
            amount = float(value)
        except (TypeError, ValueError) as exc:
            raise UnitError(f"amount for {name!r} must be a number or Quantity") from exc
    if not math.isfinite(amount) or amount < 0:
        raise UnitError(f"amount for {name!r} must be finite and >= 0, got {amount}")
    if units == "atoms":
        n_atoms = amount
    elif units == "g":
        n_atoms = grams_to_atoms(amount, nuc.atomic_mass_u)
    else:
        bq = amount * CI_IN_BQ if units == "Ci" else amount
        lam = nuc.lambda_
        if lam == 0.0:
            raise UnitError(
                f"cannot interpret activity for stable nuclide {name!r}; use units='atoms'"
            )
        n_atoms = bq / lam
    if not math.isfinite(n_atoms) or n_atoms < 0:
        raise UnitError(f"amount for {name!r} converts to invalid atom count {n_atoms}")
    return n_atoms


def _closure(seeds: Sequence[str]) -> tuple[DecayGraph, tuple[Nuclide, ...]]:
    """BFS the progeny graph from ``seeds``; return one joint graph + records."""
    order: list[str] = []
    index: dict[str, int] = {}
    by_name: dict[str, Nuclide] = {}
    edges: dict[str, list[tuple[str, float]]] = {}

    def ensure(name: str) -> None:
        if name in by_name:
            return
        nuc = Nuclide.load(name)
        index[name] = len(order)
        order.append(name)
        by_name[name] = nuc
        edges[name] = []

    queue: deque[tuple[str, int]] = deque()
    for seed in seeds:
        ensure(seed)
        queue.append((seed, 0))

    expanded: set[str] = set()
    while queue:
        name, depth = queue.popleft()
        if name in expanded:
            continue
        expanded.add(name)
        if depth >= _MAX_CLOSURE_DEPTH:
            raise ChainDefinitionError(
                f"progeny closure exceeded max depth {_MAX_CLOSURE_DEPTH} at {name!r}"
            )
        nuc = by_name[name]
        for child_raw, branch in zip(nuc.progeny, nuc.branching, strict=True):
            child = normalize_nuclide_name(child_raw)
            if child not in by_name:
                ensure(child)
                queue.append((child, depth + 1))
            edges[name].append((child, float(branch)))

    _reject_cycles(order, edges)
    lambdas = tuple(by_name[nm].lambda_ for nm in order)
    rows: list[tuple[float, ...]] = []
    for nm in order:
        row = [0.0] * len(order)
        for child, branch in edges[nm]:
            row[index[child]] += branch
        row_sum = math.fsum(row)
        if row_sum > 1.0:
            if row_sum > 1.0 + _BRANCH_ROW_SUM_TOL:
                raise ChainDefinitionError(
                    f"branching fractions for {nm!r} sum to {row_sum} > 1 "
                    f"(tolerance {_BRANCH_ROW_SUM_TOL})"
                )
            # ICRP rows can sum slightly above 1 from published rounding noise;
            # scale to exactly 1 so DecayGraph's strict check and conservation hold.
            scale = 1.0 / row_sum
            row = [f * scale for f in row]
        rows.append(tuple(row))
    graph = DecayGraph(lambdas=lambdas, names=tuple(order), fractions=tuple(rows))
    return graph, tuple(by_name[nm] for nm in order)


def _reject_cycles(order: Sequence[str], edges: Mapping[str, list[tuple[str, float]]]) -> None:
    """Raise ChainDefinitionError if the progeny edge set contains a cycle."""
    color: dict[str, int] = {nm: 0 for nm in order}

    def visit(nm: str) -> None:
        color[nm] = 1
        for child, _branch in edges.get(nm, ()):
            state = color.get(child, 0)
            if state == 1:
                raise ChainDefinitionError(f"progeny cycle detected at {nm!r} -> {child!r}")
            if state == 0:
                visit(child)
        color[nm] = 2

    for nm in order:
        if color[nm] == 0:
            visit(nm)


@dataclass(frozen=True, init=False, repr=False)
class Inventory:
    """Immutable multi-nuclide inventory with automatic progeny closure.

    Seeds are user-provided nuclides and amounts; the decay graph eagerly
    includes every reachable progeny. Internal state is canonical atom
    counts. ``decay`` returns a new inventory and never mutates ``self``.
    """

    _graph: DecayGraph
    _n0: tuple[float, ...]
    _seeds: tuple[str, ...]
    _units: str
    _was_quantity: bool
    _nuclides: tuple[Nuclide, ...]
    _eps: float

    def __init__(
        self,
        contents: Mapping[str, Any],
        *,
        units: str = "Bq",
        eps: float = DEGENERATE_EPS,
    ) -> None:
        """Build an inventory from ``{nuclide_name: amount}`` in ``units``.

        Plain numbers are interpreted as ``units`` (default ``Bq``). pint
        Quantities must be dimensionally consistent with ``units``. The
        constructor kind (plain vs Quantity) is mirrored by accessors and
        preserved across ``decay``.
        """
        if not isinstance(contents, Mapping):
            raise ChainDefinitionError(
                f"contents must be a mapping of name -> amount, got {type(contents).__name__}"
            )
        units_norm = _normalize_units(units)
        seeds: list[str] = []
        raw: dict[str, Any] = {}
        was_quantity = False
        for key, val in contents.items():
            if not isinstance(key, str):
                raise ChainDefinitionError(
                    f"contents keys must be nuclide name strings, got {key!r}"
                )
            norm = normalize_nuclide_name(key)
            if norm in raw:
                raise ChainDefinitionError(f"duplicate inventory seed {norm!r}")
            seeds.append(norm)
            raw[norm] = val
            if hasattr(val, "units"):
                was_quantity = True
        if not seeds:
            raise ChainDefinitionError("Inventory requires at least one seed nuclide")

        graph, nuclides = _closure(seeds)
        by_name = {nuc.name: nuc for nuc in nuclides}
        n0 = [0.0] * len(graph.names)
        for i, name in enumerate(graph.names):
            if name in raw:
                n0[i] = _entry_to_atoms(name, raw[name], units_norm, by_name[name])

        object.__setattr__(self, "_graph", graph)
        object.__setattr__(self, "_n0", tuple(n0))
        object.__setattr__(self, "_seeds", tuple(seeds))
        object.__setattr__(self, "_units", units_norm)
        object.__setattr__(self, "_was_quantity", was_quantity)
        object.__setattr__(self, "_nuclides", nuclides)
        object.__setattr__(self, "_eps", float(eps))

    @classmethod
    def _from_state(
        cls,
        *,
        graph: DecayGraph,
        n0: tuple[float, ...],
        seeds: tuple[str, ...],
        units: str,
        was_quantity: bool,
        nuclides: tuple[Nuclide, ...],
        eps: float,
    ) -> Inventory:
        """Return a new Inventory sharing graph/nuclides with a new state vector."""
        obj = cls.__new__(cls)
        object.__setattr__(obj, "_graph", graph)
        object.__setattr__(obj, "_n0", n0)
        object.__setattr__(obj, "_seeds", seeds)
        object.__setattr__(obj, "_units", units)
        object.__setattr__(obj, "_was_quantity", was_quantity)
        object.__setattr__(obj, "_nuclides", nuclides)
        object.__setattr__(obj, "_eps", eps)
        return obj

    @property
    def names(self) -> tuple[str, ...]:
        """Species names in graph order (seeds first, then BFS-discovered progeny)."""
        return self._graph.names

    @property
    def n_species(self) -> int:
        """Number of species in the full closure (seeds + progeny)."""
        return len(self._graph.names)

    @property
    def seeds(self) -> tuple[str, ...]:
        """Normalized seed names from the constructor (preserved by ``decay``)."""
        return self._seeds

    @property
    def units(self) -> str:
        """Canonical unit label for plain-number constructor amounts."""
        return self._units

    def decay(self, t: float | str | Any) -> Inventory:
        """Return a new inventory with every species advanced by ``t`` (immutable)."""
        t_s = to_seconds(t)
        result = solve(self._graph, self._n0, t_s, eps=self._eps)
        # Numerical noise can leave tiny negatives on stable end-caps; state is non-negative.
        n_t = tuple(max(float(x), 0.0) for x in result)
        return Inventory._from_state(
            graph=self._graph,
            n0=n_t,
            seeds=self._seeds,
            units=self._units,
            was_quantity=self._was_quantity,
            nuclides=self._nuclides,
            eps=self._eps,
        )

    def cumulative_decays(self, t: float | str | Any) -> dict[str, Any]:
        """Atoms that decayed for each species during ``[0, t]``, mirroring kind.

        Uses the block matrix exponential ``exp([[G, I], [0, 0]] * t)`` whose
        upper-right block is ``U(t) = integral exp(G s) ds`` (``G`` may be
        singular when stable nuclides are present, so ``G^{-1}(expm(G t) - I)``
        is not used). Stable species report ``0.0``.
        """
        t_s = to_seconds(t)
        n = len(self._graph.names)
        n0 = np.asarray(self._n0, dtype=np.float64)
        if t_s == 0.0:
            cum = np.zeros(n, dtype=np.float64)
        else:
            g = self._graph.generator()
            block = np.zeros((2 * n, 2 * n), dtype=np.float64)
            block[:n, :n] = g
            block[:n, n:] = np.eye(n, dtype=np.float64)
            upper_right = expm(block * t_s)[:n, n:]
            integrated = upper_right @ n0
            lambdas = np.asarray(self._graph.lambdas, dtype=np.float64)
            fractions = np.asarray(self._graph.fractions, dtype=np.float64)
            production = fractions.T @ (lambdas * integrated)
            n_t = solve(self._graph, self._n0, t_s, eps=self._eps)
            cum = n0 - n_t + production
            # Numerical noise can yield tiny negatives; cumulative decays are >= 0.
            scale = max(float(np.max(np.abs(n0))), 1.0)
            cum = np.where(np.abs(cum) < 1e-12 * scale, 0.0, cum)
        out: dict[str, Any] = {}
        for name, val in zip(self._graph.names, cum, strict=True):
            if self._was_quantity:
                out[name] = mirror_quantity(float(val), 1 * ureg.atom, "atom")
            else:
                out[name] = float(val)
        return out

    def decay_time_series(
        self,
        t_end: float | str | Any,
        *,
        npoints: int = 501,
        time_scale: str = "linear",
        t_start: float | str | Any = 0.0,
    ) -> tuple[list[float], dict[str, list[float]]]:
        """Atom-number time series from ``t_start`` to ``t_end`` over the closure.

        Returns plain ``float`` seconds and plain ``float`` atom counts (does
        not mirror Quantity kind). ``time_scale`` is ``"linear"`` or ``"log"``.
        """
        if not isinstance(npoints, int) or isinstance(npoints, bool) or npoints < 2:
            raise PyDecayError(f"npoints must be an integer >= 2, got {npoints!r}")
        if time_scale not in ("linear", "log"):
            raise PyDecayError(f"time_scale must be 'linear' or 'log', got {time_scale!r}")
        t0 = to_seconds(t_start)
        t1 = to_seconds(t_end)
        if t0 < 0.0:
            raise InvalidTimeError(f"t_start must be >= 0, got {t0}")
        if t1 < 0.0:
            raise InvalidTimeError(f"t_end must be >= 0, got {t1}")
        if time_scale == "log":
            if t0 <= 0.0:
                raise InvalidTimeError(f"log time_scale requires t_start > 0, got {t0}")
            if t1 <= 0.0:
                raise InvalidTimeError(f"log time_scale requires t_end > 0, got {t1}")
            grid = np.logspace(np.log10(t0), np.log10(t1), num=npoints)
        else:
            if t0 > t1:
                raise InvalidTimeError(
                    f"linear decay_time_series requires t_start <= t_end, got {t0} > {t1}"
                )
            grid = np.linspace(t0, t1, num=npoints)
        names = self._graph.names
        series: dict[str, list[float]] = {name: [] for name in names}
        for t_s in grid:
            state = solve(self._graph, self._n0, float(t_s), eps=self._eps)
            for name, val in zip(names, state, strict=True):
                series[name].append(float(val))
        return [float(t) for t in grid], series

    def numbers(self) -> dict[str, Any]:
        """Atom counts of every species in the closure, mirroring constructor kind."""
        out: dict[str, Any] = {}
        for name, n in zip(self._graph.names, self._n0, strict=True):
            if self._was_quantity:
                out[name] = mirror_quantity(float(n), 1 * ureg.atom, "atom")
            else:
                out[name] = float(n)
        return out

    def activities(self) -> dict[str, Any]:
        """Activity (Bq) of every species, mirroring constructor kind."""
        out: dict[str, Any] = {}
        for i, name in enumerate(self._graph.names):
            a = self._graph.lambdas[i] * self._n0[i]
            if self._was_quantity:
                out[name] = mirror_quantity(a, 1 * ureg.becquerel, "becquerel")
            else:
                out[name] = float(a)
        return out

    def masses(self) -> dict[str, Any]:
        """Mass (grams) of every species, mirroring constructor kind."""
        out: dict[str, Any] = {}
        for i, name in enumerate(self._graph.names):
            m = atoms_to_grams(self._n0[i], self._nuclides[i].atomic_mass_u)
            if self._was_quantity:
                out[name] = mirror_quantity(m, 1 * ureg.gram, "gram")
            else:
                out[name] = float(m)
        return out

    def total_activity(self) -> float:
        """Sum of activities over the closure, in Bq (always a plain float)."""
        return float(sum(lam * n for lam, n in zip(self._graph.lambdas, self._n0, strict=True)))

    def half_lives(self) -> dict[str, float]:
        """Half-life (s) per species from the catalog; ``inf`` for stable nuclides."""
        return {nuc.name: float(nuc.half_life_s) for nuc in self._nuclides}

    def __repr__(self) -> str:
        """Show seeds and unit label only (not the full closure)."""
        return (
            f"Inventory(seeds={self._seeds!r}, units={self._units!r}, "
            f"n_species={self.n_species})"
        )
