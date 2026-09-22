"""Chain solver kernels: guarded Bateman + matrix-exponential fallback.

Pure SI floats only (no pint). Dispatch policy (spec section 4.2):

* linear + parent-only IC + well-separated lambdas -> Bateman closed form
* anything else (branching, degeneracy, nonzero daughters) -> scipy.expm

The expm path is fix option 2 from the Bateman stability guidance; it is
numerically bulletproof for the degenerate-lambda regression. Cetnar's
reformulation is a deferred v2 optimization, not required for correctness.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
from scipy.linalg import expm  # type: ignore[import-untyped]

from pydecay.exceptions import ChainDefinitionError, InvalidTimeError, PyDecayError
from pydecay.graph import DecayGraph

DEGENERATE_EPS = 1e-8
"""Relative separation below which lambdas are treated as degenerate."""


def use_bateman(
    graph: DecayGraph, n0: Sequence[float], eps: float = DEGENERATE_EPS
) -> bool:
    """Return True when the fast Bateman path is safe for this graph and IC."""
    if graph.is_branched:
        return False
    if len(n0) != len(graph.lambdas):
        return False
    if any(float(x) != 0.0 for x in n0[1:]):
        return False
    max_lam = max(graph.lambdas)
    if max_lam <= 0:
        return False
    return graph.min_separation() >= eps * max_lam


def _require_finite(arr: np.ndarray, what: str) -> np.ndarray:
    if not np.all(np.isfinite(arr)):
        raise PyDecayError(f"{what} produced non-finite values")
    return arr


def bateman_closed_form(
    lambdas: Sequence[float], n0_parent: float, t_s: float
) -> np.ndarray:
    """Bateman (1910) closed-form solution for a parent-only initial condition.

    N_m(t) = N0 * prod_{i<m} l_i * sum_{k<=m} exp(-l_k t) / prod_{j<=m, j!=k}(l_j - l_k)
    """
    lam = [float(x) for x in lambdas]
    n = len(lam)
    out = np.empty(n, dtype=np.float64)
    for m in range(1, n + 1):
        prefactor = 1.0
        for i in range(m - 1):
            prefactor *= lam[i]
        series = 0.0
        for k in range(m):
            denom = 1.0
            for j in range(m):
                if j != k:
                    denom *= lam[j] - lam[k]
            if denom == 0.0:
                raise PyDecayError(
                    "degenerate lambdas reached Bateman path; dispatch should have used expm"
                )
            series += math.exp(-lam[k] * t_s) / denom
        out[m - 1] = float(n0_parent) * prefactor * series
    return _require_finite(out, "Bateman solution")


def solve(
    graph: DecayGraph,
    n0: Sequence[float],
    t_s: float,
    eps: float = DEGENERATE_EPS,
) -> np.ndarray:
    """Return N(t) for the graph and initial atom counts ``n0`` (canonical SI)."""
    n = len(graph.lambdas)
    if len(n0) != n:
        raise ChainDefinitionError(f"n0 has length {len(n0)}, expected {n}")
    init = np.asarray(n0, dtype=np.float64)
    if not np.all(np.isfinite(init)) or np.any(init < 0):
        raise PyDecayError(f"n0 must be finite and >= 0, got {n0!r}")
    if not math.isfinite(t_s):
        raise InvalidTimeError(f"time must be finite, got {t_s}")
    if t_s < 0:
        raise InvalidTimeError(f"time must be >= 0, got {t_s}")
    if t_s == 0.0:
        return init.copy()
    if use_bateman(graph, n0, eps):
        return bateman_closed_form(graph.lambdas, float(init[0]), t_s)
    result = expm(graph.generator() * t_s) @ init
    return _require_finite(result, "matrix-exponential solution")
