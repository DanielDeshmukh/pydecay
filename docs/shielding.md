# Shielding

Narrow-beam photon attenuation: Beer-Lambert transmission, half- and
tenth-value layers, and multi-layer slabs, backed by bundled NIST XCOM
tables for seven materials (v0.6.0).

## Goal

Answer "how much does this slab weaken the beam?" - a first-pass
engineering estimate of narrow-beam transmission through planar shields.
Everything is pure-SI floats (metres, MeV); pin units at the edge if you
want Quantities.

## Beer-Lambert law

```text
I = I0 * exp(-mu * x)
HVL = ln2 / mu        TVL = ln10 / mu
```

`mu(E)` comes from NIST XCOM photon cross sections (total attenuation with
coherent scattering), log-log interpolated at 45 log-spaced energies spanning
0.01-20 MeV per material, bundled in `src/pydecay/data/nist_mu.json.gz`
(compositions per NIST X-Ray Mass Attenuation Coefficients, Table 2; see
`src/pydecay/data/_fetch_nist.py`).

## Materials

```python
from pydecay import material, available_materials
available_materials()
# ('air', 'aluminum', 'concrete', 'iron', 'lead', 'polyethylene', 'water')
lead = material("lead")
lead.density_g_cm3          # 11.35
lead.mu(1.25)               # 66.73 1/m
```

Linear attenuation coefficients `mu` (1/m) and derived layers, straight
from the bundled tables:

| Material | ρ (g/cm³) | μ @ 1.0 MeV (1/m) | μ @ 1.25 MeV (1/m) | HVL @ 1.25 MeV | TVL @ 1.25 MeV |
|---|---:|---:|---:|---:|---:|
| air | 0.001205 | 0.0077 | 0.0069 | 101.1 m | 336.0 m |
| aluminum | 2.699 | 16.583 | 14.832 | 4.67 cm | 15.52 cm |
| concrete | 2.30 | 14.933 | 13.355 | 5.19 cm | 17.24 cm |
| iron | 7.87 | 47.162 | 42.103 | 1.65 cm | 5.47 cm |
| lead | 11.35 | 80.773 | 66.731 | 1.04 cm | 3.45 cm |
| polyethylene | 0.94 | 6.826 | 6.105 | 11.35 cm | 37.72 cm |
| water | 1.00 | 7.069 | 6.323 | 10.96 cm | 36.42 cm |

(For Co-60's 1.25 MeV mean gamma energy: ~10 half-value layers of lead -
about 10.4 cm - cut the beam by 1000×.)

## HVL / TVL helpers

```python
from pydecay import hvl, tvl, hvl_slab, tvl_slab, mu_from_material

mu = mu_from_material("lead", 1.25)   # 66.73 1/m
hvl(mu)                               # 0.01039 m
hvl_slab("lead", 1.25)                # same, by name
tvl_slab("lead", 1.25)                # 0.03451 m
```

Unknown material names or energies outside the table span raise
`MaterialError`.

## Transmission

```python
from pydecay import transmit, transmit_slab, multilayer_transmit

transmit(1.0, mu, 0.01)                          # exp(-mu * x)
transmit_slab(1.0, "lead", 0.01, 1.25)           # 0.513 through 1 cm Pb

multilayer_transmit(
    1.0,
    [("water", 0.10), ("iron", 0.01), ("lead", 0.005)],
    1.25,
)                                                 # product of exps
```

- Layer order does not matter for pure attenuation.
- `buildup=` is reserved: passing it raises `NotImplementedError`
  ("buildup factors ship in v0.7").
- Negative/non-finite thicknesses and non-positive `mu` raise `ValueError`.

## Limitations

- **Narrow beam only**: no scatter, no skyshine, no streaming, no
  secondary-electron equilibrium questions.
- **No buildup factor** (reserved for v0.7) - broad-beam shields need one,
  so real transmitted doses are higher than these numbers.
- One energy at a time; polychromatic beams should be integrated
  energy-by-energy.
- An engineering aid, **not a regulatory or safety-analysis tool**.

## Data sources

- NIST XCOM photon cross-sections database (total attenuation with
  coherent scattering): <https://physics.nist.gov/PhysRefData/Xcom/html/xcom1.html>
- NIST X-Ray Mass Attenuation Coefficients, Table 2 (material compositions).
- License notice for the bundled tables: `src/pydecay/data/LICENSE.nist.txt`.
- Regeneration script: `src/pydecay/data/_fetch_nist.py`.
