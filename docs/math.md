# Mathematics

Formulas and citations for every path pydecay can take. Ground truth is the
design spec (`docs/superpowers/specs/2026-09-22-pydecay-design.md`), whose
sources cite Krane, Bateman (1910), Cetnar (2006), BIPM, and NIST SP 811.

## Single isotope

ODE and closed form (Krane, *Introductory Nuclear Physics*, Ch. 6; memoryless
Poisson assumption):

```text
dN/dt = -lambda * N   ->   N(t) = N0 * exp(-lambda * t)
```

Implemented as the closed form only — never numerically integrated for a
single isotope (`src/pydecay/decay.py`).

Decay constant and mean lifetime:

```text
lambda = ln(2) / T_half
tau    = 1 / lambda = T_half / ln(2)
```

Identities asserted in tests (`tests/test_decay.py`):

```text
N(T_half) = N0 / 2
N(tau)    = N0 / e
```

Activity (BIPM SI Brochure: 1 Bq = 1 decay/s; NIST SP 811: 1 Ci = 3.7e10 Bq):

```text
A(t) = lambda * N(t) = A0 * exp(-lambda * t)
```

## Linear chains (Bateman)

System for species 1 → 2 → … → n:

```text
dN1/dt = -lambda1 * N1
dNi/dt = lambda_{i-1} * N_{i-1} - lambda_i * N_i    (i = 2..n)
```

Bateman (1910) closed form for a parent-only initial condition
(H. Bateman, Proc. Cambridge Phil. Soc. 15, 423–427):

```text
N_n(t) = N1_0 * (prod_{i=1}^{n-1} lambda_i)
         * sum_{k=1}^{n} [ exp(-lambda_k * t)
                           / prod_{j!=k} (lambda_j - lambda_k) ]
```

**Stability caveat:** when `lambda_i ≈ lambda_j` the denominator
`(lambda_j - lambda_k) → 0` and the naive formula blows up even though the
physical answer is finite. pydecay never ships an unguarded Bateman formula.

### Dispatch table (spec fix option 2; Cetnar 2006 noted as deferred)

| Condition | Path |
|---|---|
| Linear, unbranched, parent-only IC, well-separated lambdas | Bateman closed form |
| Branching present | `scipy.linalg.expm(G * t) @ n0` |
| Degenerate pair (`min|λi-λj| < eps * max(λ)`, default eps = 1e-8) | `expm` |
| Nonzero daughter initial conditions | `expm` |
| `t = 0` | copy of `n0` (no solver call) |

Cetnar's reformulation (fix option 1) is a deferred v2 optimization: it
changes performance characteristics, not results, once the `expm` guard is
in place.

## Generator matrix convention

```text
dN/dt = G @ N
G[i,i] = -lambda_i
G[i,j] += lambda_j * f_ji     # destination row i, source column j
```

where `f_ji` is the fraction of species `j`'s decays that go to species `i`
(linear chains are the special case `f = 1` on the subdiagonal).

Note: the reference doc's index order (`A[i-1][i] = lambda_{i-1}`) is
transposed relative to this convention. pydecay follows the
ingrowth-verified form above (`src/pydecay/graph.py`).

## Atom ↔ gram

```text
N = (mass_g / M) * N_A
N_A = 6.02214076e23 /mol     (exact, 2019 SI redefinition, BIPM)
```

`M` is the nuclide's atomic mass in g/mol (numerically equal to the atomic
mass in u). Implemented in `units.atoms_to_grams` / `units.grams_to_atoms`.
