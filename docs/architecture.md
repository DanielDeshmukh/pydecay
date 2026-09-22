# Architecture

Three views of the package: module layering, solver dispatch, and a request
data-flow trace.

## Module layering

```mermaid
graph TD
    INIT["__init__.py (re-exports)"] --> API[api.py]
    INIT --> CH[chain.py]
    INIT --> NU[nuclide.py]
    INIT --> EX[exceptions.py]
    API --> U[units.py]
    API --> D[decay.py]
    CH --> S["_solver.py"]
    CH --> G[graph.py]
    CH --> NU
    CH --> U
    NU --> U
    NU --> D
    NU --> DATA["data/nuclides.json"]
    S --> G
    S --> SCIPY["scipy.linalg.expm"]
    D --> EX
    S --> EX
    G --> EX
    U --> PINT[pint]
    classDef pure fill:#e8f5e9,stroke:#2e7d32
    classDef edge fill:#e3f2fd,stroke:#1565c0
    class D,G,S pure
    class API,CH,NU,U,INIT edge
```

Boundary rules: pure-SI modules (`decay.py`, `graph.py`, `_solver.py`) never
import pint; edge modules (`units.py`, `nuclide.py`, `chain.py`, `api.py`,
`__init__.py`) may use pint on their public surface and always pass canonical
floats downward.

## Solver dispatch

```mermaid
flowchart TD
    A["DecayChain.at(t) / solve(graph, n0, t)"] --> B{"branched OR nonzero daughter IC?"}
    B -->|yes| E["scipy.linalg.expm(G*t) @ n0"]
    B -->|no| C{"min|lambda_i - lambda_j| >= eps * max(lambda)?"}
    C -->|no| E
    C -->|yes| F["Bateman closed form"]
    E --> Z{"all finite?"}
    F --> Z
    Z -->|no| X["raise PyDecayError (never return NaN)"]
    Z -->|yes| Y["N(t) vector"]
    B -->|t = 0| Y0["return copy of n0"]
```

(Every path also validates `t >= 0` finite and atoms `>= 0` finite first;
`t = 0` short-circuits before dispatch.)

## Data flow

```mermaid
sequenceDiagram
    participant U as User
    participant API as api.py / chain.py
    participant UN as units.py
    participant CORE as decay.py / _solver.py
    U->>API: decayed_atoms(N0=1e6, half_life="8 days", time="24 hours")
    API->>UN: to_half_life_seconds / to_seconds (parse once)
    API->>CORE: remaining_atoms(n0_f, lambda_, t_s)
    CORE-->>API: float (canonical SI)
    API->>UN: mirror_quantity(result, N0, "atom")
    UN-->>U: Quantity if N0 was Quantity, else float
```
