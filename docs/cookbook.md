# Cookbook

Ten copy-paste recipes for everyday pydecay tasks. Every `python` block is
executed by `tests/test_docs_recipes.py` on each test run and compared
against the `text` block below it, so the outputs you read are outputs the
code actually produces.

## 1. Half-life to remaining activity

**Problem:** Start with 1000 Bq of I-131 and find what remains after
three half-lives.

```python
# recipe: remaining-activity
from pydecay import Nuclide, decayed_activity

i131 = Nuclide.load("I-131")
a0 = 1000.0                      # Bq
t = 3 * i131.half_life_s         # three half-lives, in seconds

print(f"T_half = {i131.half_life_s / 86400:.4f} days")
print(f"A(3 half-lives) = {decayed_activity(a0, i131.half_life, t):.4f} Bq")
```

Expected output:

```text
T_half = 8.0207 days
A(3 half-lives) = 125.0000 Bq
```

**Source:** `A(t) = A0 * exp(-ln2/T_half * t)`; half-life from ICRP
Publication 107 <https://www.icrp.org/publication.asp?id=ICRP+Publication+107>.

## 2. Chain composition at time *t*

**Problem:** A sample starts with 1e6 atoms of Sr-90. What does it look
like after 10 years?

```python
# recipe: chain-at-t
from pydecay import DecayChain

chain = DecayChain.from_isotopes(["Sr-90", "Y-90"])
t = 10 * 31557600                # 10 Julian years, in seconds

for name, atoms in chain.at(t, n0={"Sr-90": 1e6}).items():
    print(f"{name}: {atoms:.6e} atoms")
```

Expected output:

```text
Sr-90: 7.860305e+05 atoms
Y-90: 1.996938e+02 atoms
```

**Source:** Bateman (1910), *Proc. Cambridge Philos. Soc.* **15**, 423-427;
half-lives from ICRP Publication 107
<https://www.icrp.org/publication.asp?id=ICRP+Publication+107>.

## 3. Build a decay time series

**Problem:** Tabulate a Mo-99/Tc-99m generator inventory from 0 to 24 hours.

```python
# recipe: decay-series
from pydecay import Inventory

inv = Inventory({"Mo-99": 1e6}, units="Bq")
t, series = inv.decay_time_series("24 hours", npoints=5)

print("t (s) | Mo-99 (Bq) | Tc-99m (Bq)")
for i, t_s in enumerate(t):
    print(f"{t_s:7.0f} | {series['Mo-99'][i]:10.4e} | {series['Tc-99m'][i]:11.4e}")
```

Expected output:

```text
t (s) | Mo-99 (Bq) | Tc-99m (Bq)
      0 | 3.4247e+11 |  0.0000e+00
  21600 | 3.2154e+11 |  1.3210e+10
  43200 | 3.0189e+11 |  1.9018e+10
  64800 | 2.8343e+11 |  2.1170e+10
  86400 | 2.6611e+11 |  2.1536e+10
```

**Source:** Mo-99 and Tc-99m half-lives from ICRP Publication 107
<https://www.icrp.org/publication.asp?id=ICRP+Publication+107>; see also
[Quickstart](quickstart.md).

## 4. Exposure to kerma to ambient dose

**Problem:** Walk the full point-source chain: exposure rate, air kerma
rate, then ambient dose equivalent, for 1 MBq of Co-60 at 1 m.

```python
# recipe: dose-conversions
from pydecay import air_kerma_rate, dose_rate, exposure_rate

gamma = 12.987        # R.cm2.mCi-1.h-1 for Co-60 (Risoe-M-2322, Table 4)
a0 = 1e6              # Bq
r_cm = 100.0          # 1 m

x = exposure_rate(gamma, a0, r_cm)
k = air_kerma_rate(gamma, a0, r_cm)
amb = dose_rate(a0, "Co-60", 1.0, quantity="ambient")

print(f"exposure rate   = {x:.6e} R/h")
print(f"air kerma rate  = {k:.6e} Gy/h")
print(f"ambient dose eq = {amb:.6e} Sv/h")
print(f"H*(10)/Ka       = {amb / k:.4f}")
```

Expected output:

```text
exposure rate   = 3.510000e-05 R/h
air kerma rate  = 3.074760e-07 Gy/h
ambient dose eq = 3.566722e-07 Sv/h
H*(10)/Ka       = 1.1600
```

**Source:** gamma constant from Lauridsen (1982), Risoe-M-2322 Table 4;
1 R in air = 8.76e-3 Gy (NIST); H*(10)/Ka = 1.16 Sv/Gy at 1.25 MeV from
ICRP Publication 74, Table A.21
<https://www.icrp.org/publication.asp?id=ICRP+Publication+74>. Full
conventions: [Dose rates](dose.md).

## 5. Single-slab HVL sizing

**Problem:** How much concrete stops a 1.25 MeV beam to 0.1 %?

```python
# recipe: hvl-sizing
import math

from pydecay import hvl_slab, transmit_slab

energy = 1.25            # MeV, mean Co-60 gamma energy
hvl = hvl_slab("concrete", energy)
target = 1e-3            # transmission to reach

n_hvl = math.log2(1 / target)
thickness = n_hvl * hvl
actual = transmit_slab(1.0, "concrete", thickness, energy)

print(f"HVL (concrete, 1.25 MeV) = {hvl:.4f} m")
print(f"half-layers for 1e-3     = {n_hvl:.4f}")
print(f"thickness                = {thickness:.4f} m")
print(f"check transmission       = {actual:.6e}")
```

Expected output:

```text
HVL (concrete, 1.25 MeV) = 0.0519 m
half-layers for 1e-3     = 9.9658
thickness                = 0.5172 m
check transmission       = 1.000000e-03
```

**Source:** Beer-Lambert `I = I0*exp(-mu*x)`, `HVL = ln2/mu`; `mu` from
NIST XCOM <https://physics.nist.gov/PhysRefData/Xcom/html/xcom1.html>.
Caveats and material table: [Shielding](shielding.md).

## 6. Multilayer wall

**Problem:** Stack 1 cm lead, 20 cm concrete, and 5 cm polyethylene; what
gets through at 1.25 MeV?

```python
# recipe: multilayer-wall
from pydecay import multilayer_transmit

wall = [("lead", 0.01), ("concrete", 0.20), ("polyethylene", 0.05)]
transmission = multilayer_transmit(1.0, wall, 1.25)

print("layer             thickness (m)")
for material, x in wall:
    print(f"{material:<17} {x:.3f}")
print(f"{'total':<17} {sum(x for _, x in wall):.3f}")
print(f"transmission @ 1.25 MeV = {transmission:.6e}")
```

Expected output:

```text
layer             thickness (m)
lead              0.010
concrete          0.200
polyethylene      0.050
total             0.260
transmission @ 1.25 MeV = 2.615751e-02
```

**Source:** product of per-layer `exp(-mu_i * x_i)` with NIST XCOM
coefficients <https://physics.nist.gov/PhysRefData/Xcom/html/xcom1.html>;
narrow-beam only (buildup arrives in v0.7).

## 7. Batch CSV decay table

**Problem:** Produce a CSV of activities for three nuclides at 0, 1, 5,
and 10 days (written to `decay_table.csv` in the working directory).

```python
# recipe: csv-decay-table
import csv

from pydecay import Nuclide, decayed_activity

nuclides = ["I-131", "Co-60", "Cs-137"]
times_days = [0, 1, 5, 10]

with open("decay_table.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["nuclide"] + [f"day_{d}" for d in times_days])
    for name in nuclides:
        nuc = Nuclide.load(name)
        row = [name]
        for d in times_days:
            a = decayed_activity(1e6, nuc.half_life, d * 86400)
            row.append(f"{a:.6e}")
        writer.writerow(row)

with open("decay_table.csv") as f:
    print(f.read(), end="")
```

Expected output:

```text
nuclide,day_0,day_1,day_5,day_10
I-131,1.000000e+06,9.172091e+05,6.491452e+05,4.213894e+05
Co-60,1.000000e+06,9.996401e+05,9.982016e+05,9.964063e+05
Cs-137,1.000000e+06,9.999371e+05,9.996855e+05,9.993711e+05
```

**Source:** same analytic decay as recipe 1 with ICRP Publication 107
half-lives <https://www.icrp.org/publication.asp?id=ICRP+Publication+107>.

## 8. Unit conversions

**Problem:** Convert years to seconds, curies to becquerels, and atoms to
grams.

```python
# recipe: unit-conversions
from pydecay import atoms_to_grams, bq_to_ci, ci_to_bq, to_seconds

print(f"10 Julian years = {to_seconds(10 * 31557600):.0f} s")
print(f"1 Ci            = {ci_to_bq(1.0):.3e} Bq")
print(f"3.7e10 Bq       = {bq_to_ci(3.7e10):.1f} Ci")
u238_g = atoms_to_grams(6.02214076e23, 238.0508)
print(f"6.02214076e23 atoms of mass 238.0508 u = {u238_g:.4f} g")
```

Expected output:

```text
10 Julian years = 315576000 s
1 Ci            = 3.700e+10 Bq
3.7e10 Bq       = 1.0 Ci
6.02214076e23 atoms of mass 238.0508 u = 238.0508 g
```

**Source:** `1 Ci = 3.7e10 Bq` (exact) and `N_A = 6.02214076e23 /mol`
(exact), NIST Special Publication 811 <https://www.nist.gov/pml/special-publication-811>.

## 9. Plot a decay curve

**Problem:** Plot the I-131 activity fraction over 30 days and print a
few points.

```python
# recipe: plot-decay-curve
import matplotlib.pyplot as plt
import numpy as np

from pydecay import Nuclide, remaining_fraction

i131 = Nuclide.load("I-131")
days = np.linspace(0, 30, 301)
fraction = [remaining_fraction(i131.half_life_s, d * 86400) for d in days]

for d in (0, 8, 16, 24):
    print(f"day {d:2d}: A(t)/A0 = {fraction[d * 10]:.4f}")

plt.plot(days, fraction, label="I-131")
plt.xlabel("days")
plt.ylabel("A(t) / A0")
plt.title("I-131 decay")
plt.legend()
plt.grid(alpha=0.3)
plt.show()
```

Expected output:

```text
day  0: A(t)/A0 = 1.0000
day  8: A(t)/A0 = 0.5009
day 16: A(t)/A0 = 0.2509
day 24: A(t)/A0 = 0.1257
```

**Source:** exponential decay with the ICRP Publication 107 half-life
<https://www.icrp.org/publication.asp?id=ICRP+Publication+107>.

## 10. Catch pydecay errors

**Problem:** Handle the three mistakes users hit most: a misspelled
nuclide, an unknown material, and a negative time.

```python
# recipe: error-handling
from pydecay import (
    Nuclide,
    NuclideNotFoundError,
    PyDecayError,
    to_seconds,
    transmit_slab,
)

try:
    Nuclide.load("Xx-999")
except NuclideNotFoundError as exc:
    print(f"lookup failed: {exc}")

try:
    transmit_slab(1.0, "unobtainium", 0.1, 1.25)
except PyDecayError as exc:
    print(f"shielding failed: {type(exc).__name__}")

try:
    to_seconds(-5)
except PyDecayError as exc:
    print(f"time rejected: {type(exc).__name__}")
```

Expected output:

```text
lookup failed: nuclide 'Xx-999' not found in ICRP-107 catalog
shielding failed: MaterialError
time rejected: InvalidTimeError
```

**Source:** every package error inherits from `PyDecayError`; see the
[User guide](user-guide.md) for the full exception table.
